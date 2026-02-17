import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Status
from app.models.task import Task
from app.services.task_service import (
    _task_load_options,
    compute_readiness,
    enrich_task,
    is_locked,
)


def _sort_key(enriched: dict):
    ep = enriched["effective_points"]
    return (ep if ep is not None else float("inf"), enriched["created_at"], enriched["id"])


async def _load_project_tasks(
    session: AsyncSession, project_id: uuid.UUID, *filters
) -> list[Task]:
    stmt = (
        select(Task)
        .where(Task.project_id == project_id, *filters)
        .options(*_task_load_options())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_backlog(
    session: AsyncSession, project_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[dict]:
    tasks = await _load_project_tasks(session, project_id, Task.status == Status.todo)
    enriched = [enrich_task(t) for t in tasks]
    enriched = [e for e in enriched if e["readiness"] == "ready"]
    enriched.sort(key=_sort_key)
    return enriched[offset : offset + limit]


async def get_in_progress(
    session: AsyncSession, project_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[dict]:
    tasks = await _load_project_tasks(session, project_id, Task.status == Status.doing)
    result = []
    for t in tasks:
        e = enrich_task(t)
        if t.lock and is_locked(t):
            e["lock_caller_label"] = t.lock.caller_label
            e["lock_purpose"] = t.lock.lock_purpose.value if hasattr(t.lock.lock_purpose, "value") else t.lock.lock_purpose
            e["lock_expires_at"] = t.lock.expires_at
        else:
            e["lock_caller_label"] = None
            e["lock_purpose"] = None
            e["lock_expires_at"] = None
        result.append(e)
    result.sort(key=_sort_key)
    return result[offset : offset + limit]


async def get_needs_refinement(
    session: AsyncSession, project_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> list[dict]:
    from sqlalchemy import or_

    tasks = await _load_project_tasks(
        session,
        project_id,
        or_(Task.needs_refinement == True, Task.sizing_confidence.isnot(None)),  # noqa: E712
    )
    enriched = []
    for t in tasks:
        e = enrich_task(t)
        if t.needs_refinement or (t.sizing_confidence is not None and t.sizing_confidence <= 2):
            enriched.append(e)
    enriched.sort(key=_sort_key)
    return enriched[offset : offset + limit]


async def get_available(
    session: AsyncSession,
    operation: str,
    project_id: uuid.UUID | None = None,
    task_type: str | None = None,
    min_points: int | None = None,
    max_points: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    filters = []
    if project_id:
        filters.append(Task.project_id == project_id)

    if operation == "sizing":
        filters.append(Task.points.is_(None))
        stmt = select(Task).where(*filters).options(*_task_load_options())
        result = await session.execute(stmt)
        tasks = list(result.scalars().all())
        # Only leaf tasks (no children)
        tasks = [t for t in tasks if not t.children]
    elif operation == "breakdown":
        filters.append(Task.status == Status.todo)
        stmt = select(Task).where(*filters).options(*_task_load_options())
        result = await session.execute(stmt)
        tasks = list(result.scalars().all())
        tasks = [t for t in tasks if compute_readiness(t) == "needs_breakdown"]
    elif operation == "implementation":
        filters.append(Task.status == Status.todo)
        stmt = select(Task).where(*filters).options(*_task_load_options())
        result = await session.execute(stmt)
        tasks = list(result.scalars().all())
        tasks = [t for t in tasks if compute_readiness(t) == "ready"]
    else:
        return []

    # Exclude locked tasks
    tasks = [t for t in tasks if not is_locked(t)]

    enriched = [enrich_task(t) for t in tasks]

    # Apply optional filters
    if task_type:
        enriched = [e for e in enriched if e["task_type"].value == task_type or e["task_type"] == task_type]
    if min_points is not None:
        enriched = [e for e in enriched if e["effective_points"] is not None and e["effective_points"] >= min_points]
    if max_points is not None:
        enriched = [e for e in enriched if e["effective_points"] is not None and e["effective_points"] <= max_points]

    enriched.sort(key=_sort_key)
    return enriched[offset : offset + limit]
