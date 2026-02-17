import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import Status
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate


def compute_rolled_up_points(task: Task) -> int | None:
    """Sum of effective_points of all children. None if no children or none are sized."""
    if not task.children:
        return None
    total = 0
    any_sized = False
    for child in task.children:
        ep = compute_effective_points(child)
        if ep is not None:
            total += ep
            any_sized = True
    return total if any_sized else None


def compute_effective_points(task: Task) -> int | None:
    """Rolled-up points if available, else own points."""
    rup = compute_rolled_up_points(task)
    if rup is not None:
        return rup
    return task.points


def compute_unsized_children(task: Task) -> int:
    """Count of direct children where points is None."""
    return sum(1 for child in task.children if child.points is None)


def compute_readiness(task: Task) -> str:
    """Compute readiness state per architecture doc rules."""
    if task.needs_refinement:
        return "needs_refinement"
    if task.points is None and not task.children:
        return "needs_sizing"
    ep = compute_effective_points(task)
    if task.children and compute_unsized_children(task) > 0:
        return "needs_breakdown"
    if ep is not None and ep > 6:
        return "needs_breakdown"
    if task.children:
        return "blocked_by_children"
    return "ready"


def is_locked(task: Task) -> bool:
    """Check if task has an active (non-expired) lock."""
    if task.lock is None:
        return False
    return task.lock.expires_at > datetime.now(timezone.utc)


def enrich_task(task: Task) -> dict:
    """Build a dict with stored + computed fields for a task."""
    return {
        "id": task.id,
        "project_id": task.project_id,
        "parent_task_id": task.parent_task_id,
        "name": task.name,
        "description": task.description,
        "context": task.context,
        "task_type": task.task_type,
        "status": task.status,
        "points": task.points,
        "position": task.position,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "effective_points": compute_effective_points(task),
        "rolled_up_points": compute_rolled_up_points(task),
        "unsized_children": compute_unsized_children(task),
        "readiness": compute_readiness(task),
        "children_count": len(task.children) if task.children else 0,
        "is_locked": is_locked(task),
    }


def _task_load_options():
    return [
        selectinload(Task.children).selectinload(Task.children),
        selectinload(Task.lock),
    ]


async def create_task(
    session: AsyncSession,
    project_id: uuid.UUID,
    data: TaskCreate,
    parent_task_id: uuid.UUID | None = None,
) -> Task:
    if parent_task_id:
        parent = await session.get(Task, parent_task_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent task not found")
        if parent.project_id != project_id:
            raise HTTPException(
                status_code=400, detail="Parent task belongs to a different project"
            )

    # Auto-assign position
    position = data.position
    if position is None:
        result = await session.execute(
            select(func.coalesce(func.max(Task.position), -1)).where(
                Task.project_id == project_id,
                Task.parent_task_id == parent_task_id
                if parent_task_id
                else Task.parent_task_id.is_(None),
            )
        )
        position = result.scalar() + 1

    task = Task(
        project_id=project_id,
        parent_task_id=parent_task_id,
        name=data.name,
        description=data.description,
        context=data.context,
        task_type=data.task_type,
        position=position,
    )
    session.add(task)
    await session.flush()

    # Reload with relationships
    result = await session.execute(
        select(Task).where(Task.id == task.id).options(*_task_load_options())
    )
    return result.scalar_one()


async def get_task(session: AsyncSession, task_id: uuid.UUID) -> Task:
    result = await session.execute(
        select(Task).where(Task.id == task_id).options(*_task_load_options())
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def update_task(
    session: AsyncSession, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    task = await get_task(session, task_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await session.flush()

    # Reload with relationships
    result = await session.execute(
        select(Task).where(Task.id == task.id).options(*_task_load_options())
    )
    return result.scalar_one()


async def delete_task(session: AsyncSession, task_id: uuid.UUID) -> None:
    task = await get_task(session, task_id)
    await session.delete(task)
    await session.flush()


async def get_task_tree(session: AsyncSession, task_id: uuid.UUID) -> dict:
    """Fetch full recursive subtree using a recursive CTE."""
    # Verify root exists
    await get_task(session, task_id)

    # Use recursive CTE to get all descendants
    cte = (
        select(Task.id, Task.parent_task_id)
        .where(Task.id == task_id)
        .cte(name="subtree", recursive=True)
    )
    cte = cte.union_all(
        select(Task.id, Task.parent_task_id).join(cte, Task.parent_task_id == cte.c.id)
    )
    result = await session.execute(select(cte.c.id))
    all_ids = [row[0] for row in result.all()]

    # Load all tasks with their children and locks
    result = await session.execute(
        select(Task)
        .where(Task.id.in_(all_ids))
        .options(selectinload(Task.children), selectinload(Task.lock))
    )
    tasks_by_id = {t.id: t for t in result.scalars().all()}

    def build_tree(tid: uuid.UUID) -> dict:
        t = tasks_by_id[tid]
        node = enrich_task(t)
        node["children"] = sorted(
            [build_tree(c.id) for c in t.children if c.id in tasks_by_id],
            key=lambda x: x["position"],
        )
        return node

    return build_tree(task_id)


async def get_task_ancestry(session: AsyncSession, task_id: uuid.UUID) -> list[Task]:
    """Walk parent_task_id chain to root. Returns list ordered root → target."""
    chain = []
    current_id = task_id
    while current_id is not None:
        result = await session.execute(
            select(Task).where(Task.id == current_id).options(*_task_load_options())
        )
        task = result.scalar_one_or_none()
        if task is None:
            if current_id == task_id:
                raise HTTPException(status_code=404, detail="Task not found")
            break
        chain.append(task)
        current_id = task.parent_task_id
    chain.reverse()
    return chain


async def get_task_context(
    session: AsyncSession, task_id: uuid.UUID, include_commits: bool = False
) -> dict:
    """Fetch task + ancestry + work log (+ commits). Compute freshness."""
    # Load task with all relationships needed (deep children for enrich_task)
    children_chain = selectinload(Task.children)
    for _ in range(5):
        children_chain = children_chain.selectinload(Task.children)
    result = await session.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(
            children_chain,
            selectinload(Task.lock),
            selectinload(Task.work_log_entries),
            selectinload(Task.commits),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Capture enriched data and related objects before ancestry query
    # (ancestry reloads same objects and may expire children relationships)
    task_enriched = enrich_task(task)
    work_log_entries = list(task.work_log_entries or [])
    commits_list = list(task.commits or [])
    context_captured_at = task.context_captured_at

    ancestry = await get_task_ancestry(session, task_id)
    # Last item is the target task itself
    ancestors = ancestry[:-1] if ancestry else []
    stale_reasons: list[str] = []
    if context_captured_at is None:
        freshness = "stale"
        stale_reasons.append("Context never captured")
    else:
        for a in ancestors:
            if a.updated_at and a.updated_at > context_captured_at:
                stale_reasons.append(f"{a.name} (updated {a.updated_at.isoformat()})")
        freshness = "stale" if stale_reasons else "fresh"

    return {
        "task": task_enriched,
        "ancestors": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "context": a.context,
                "updated_at": a.updated_at,
            }
            for a in ancestors
        ],
        "work_log": [
            {
                "id": e.id,
                "task_id": e.task_id,
                "author": e.author,
                "operation": e.operation.value if hasattr(e.operation, "value") else e.operation,
                "content": e.content,
                "created_at": e.created_at,
            }
            for e in work_log_entries
        ],
        "commits": [
            {
                "id": c.id,
                "task_id": c.task_id,
                "author": c.author,
                "commit_hash": c.commit_hash,
                "message": c.message,
                "committed_at": c.committed_at,
            }
            for c in commits_list
        ]
        if include_commits
        else None,
        "context_captured_at": context_captured_at,
        "context_freshness": freshness,
        "stale_reasons": stale_reasons,
    }


# Valid status transitions
_VALID_TRANSITIONS: dict[Status, set[Status]] = {
    Status.todo: {Status.doing, Status.wont_do},
    Status.doing: {Status.done, Status.todo, Status.wont_do},
    Status.done: {Status.todo, Status.wont_do},
    Status.wont_do: {Status.todo},
}


def _check_descendants_terminal(task: Task) -> tuple[bool, bool]:
    """Check if all descendants are terminal (done/wont_do) and at least one is done.
    Returns (all_terminal, any_done). Uses the already-loaded children tree."""
    terminal = {Status.done, Status.wont_do}
    all_terminal = True
    any_done = False

    def walk(t: Task) -> None:
        nonlocal all_terminal, any_done
        for child in (t.children or []):
            s = Status(child.status) if isinstance(child.status, str) else child.status
            if s not in terminal:
                all_terminal = False
            if s == Status.done:
                any_done = True
            walk(child)

    walk(task)
    return all_terminal, any_done


async def update_task_status(
    session: AsyncSession, task_id: uuid.UUID, new_status: Status
) -> Task:
    """Update task status with validation rules."""
    # Load with deep enough children for descendant checks
    result = await session.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.children)
            .selectinload(Task.children)
            .selectinload(Task.children)
            .selectinload(Task.children),
            selectinload(Task.lock),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = Status(task.status) if isinstance(task.status, str) else task.status

    if new_status == old_status:
        return task

    if new_status not in _VALID_TRANSITIONS.get(old_status, set()):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid transition from {old_status.value} to {new_status.value}",
        )

    # To done: all descendants must be terminal, at least one done
    if new_status == Status.done:
        has_children = bool(task.children)
        if has_children:
            all_terminal, any_done = _check_descendants_terminal(task)
            if not all_terminal:
                raise HTTPException(
                    status_code=422,
                    detail="Cannot complete: not all descendants are terminal (done/wont_do)",
                )
            if not any_done:
                raise HTTPException(
                    status_code=422,
                    detail="Cannot complete: at least one descendant must be done",
                )

    task.status = new_status
    await session.flush()

    # If reopening a child (done -> todo/doing), reopen parent if it's done
    if old_status == Status.done and new_status in (Status.todo, Status.doing):
        if task.parent_task_id:
            parent = await session.get(Task, task.parent_task_id)
            if parent and (Status(parent.status) if isinstance(parent.status, str) else parent.status) == Status.done:
                parent.status = Status.todo
                await session.flush()

    # Reload with relationships
    result = await session.execute(
        select(Task).where(Task.id == task.id).options(*_task_load_options())
    )
    return result.scalar_one()


async def reorder_task(
    session: AsyncSession, task_id: uuid.UUID, new_position: int
) -> Task:
    """Change a task's position among its siblings."""
    task = await get_task(session, task_id)

    # Shift siblings at >= new_position up by 1
    from sqlalchemy import update

    await session.execute(
        update(Task)
        .where(
            Task.parent_task_id == task.parent_task_id if task.parent_task_id else Task.parent_task_id.is_(None),
            Task.project_id == task.project_id,
            Task.position >= new_position,
            Task.id != task.id,
        )
        .values(position=Task.position + 1)
    )

    task.position = new_position
    await session.flush()

    # Reload
    result = await session.execute(
        select(Task).where(Task.id == task.id).options(*_task_load_options())
    )
    return result.scalar_one()
