import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Operation, Status
from app.models.commit import TaskCommit
from app.models.task import Task
from app.models.work_log import WorkLogEntry
from app.schemas.atomic import (
    BreakdownRequest,
    CommitCreate,
    CompleteRequest,
    FlagRefinementRequest,
    RefineRequest,
    SizingRequest,
)
from app.services.task_service import _task_load_options, get_task


async def _reload_task(session: AsyncSession, task_id: uuid.UUID) -> Task:
    # Expire all to ensure fresh relationship loading (e.g. new children)
    session.expire_all()
    result = await session.execute(
        select(Task).where(Task.id == task_id).options(*_task_load_options())
    )
    return result.scalar_one()


async def create_work_log_entry(
    session: AsyncSession,
    task_id: uuid.UUID,
    operation: Operation,
    content: str,
    author: str | None = None,
) -> WorkLogEntry:
    entry = WorkLogEntry(
        task_id=task_id,
        operation=operation,
        content=content,
        author=author,
    )
    session.add(entry)
    return entry


async def size_task(
    session: AsyncSession, task_id: uuid.UUID, data: SizingRequest
) -> Task:
    task = await get_task(session, task_id)

    dimensions = {
        "scope_clarity": data.scope_clarity.model_dump(),
        "decision_points": data.decision_points.model_dump(),
        "context_window_demand": data.context_window_demand.model_dump(),
        "verification_complexity": data.verification_complexity.model_dump(),
        "domain_specificity": data.domain_specificity.model_dump(),
    }
    total = sum(d["score"] for d in dimensions.values())

    points_breakdown = {
        "dimensions": dimensions,
        "total": total,
        "confidence": data.confidence,
        "risk_factors": data.risk_factors,
        "breakdown_suggestions": data.breakdown_suggestions,
        "scored_by": data.scored_by,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }

    task.points = total
    task.points_breakdown = points_breakdown
    task.sizing_confidence = data.confidence

    await create_work_log_entry(
        session, task_id, Operation.sizing, data.work_log_content, data.author
    )
    await session.flush()
    return await _reload_task(session, task_id)


async def breakdown_task(
    session: AsyncSession, task_id: uuid.UUID, data: BreakdownRequest
) -> Task:
    task = await get_task(session, task_id)

    if data.parent_description_update:
        task.description = data.parent_description_update

    from sqlalchemy import func

    # Compute base position once for all subtasks without explicit positions
    result = await session.execute(
        select(func.coalesce(func.max(Task.position), -1)).where(
            Task.project_id == task.project_id,
            Task.parent_task_id == task_id,
        )
    )
    next_position = result.scalar() + 1

    for i, subtask_data in enumerate(data.subtasks):
        position = subtask_data.position if subtask_data.position is not None else next_position + i

        child = Task(
            project_id=task.project_id,
            parent_task_id=task_id,
            name=subtask_data.name,
            description=subtask_data.description,
            context=subtask_data.context,
            task_type=subtask_data.task_type,
            position=position,
        )
        session.add(child)

    await create_work_log_entry(
        session, task_id, Operation.breakdown, data.work_log_content, data.author
    )
    await session.flush()
    return await _reload_task(session, task_id)


async def refine_task(
    session: AsyncSession, task_id: uuid.UUID, data: RefineRequest
) -> Task:
    task = await get_task(session, task_id)

    if data.description is not None:
        task.description = data.description
    if data.context is not None:
        task.context = data.context
    if data.context_captured_at is not None:
        task.context_captured_at = data.context_captured_at

    task.needs_refinement = False

    await create_work_log_entry(
        session, task_id, Operation.refinement, data.work_log_content, data.author
    )
    await session.flush()
    return await _reload_task(session, task_id)


async def flag_refinement(
    session: AsyncSession, task_id: uuid.UUID, data: FlagRefinementRequest
) -> Task:
    task = await get_task(session, task_id)
    task.needs_refinement = True
    task.refinement_notes = data.refinement_notes
    await session.flush()
    return await _reload_task(session, task_id)


async def complete_task(
    session: AsyncSession, task_id: uuid.UUID, data: CompleteRequest
) -> Task:
    from app.services.task_service import update_task_status

    await create_work_log_entry(
        session, task_id, Operation.implementation, data.work_log_content, data.author
    )

    if data.commits:
        for commit_data in data.commits:
            commit = TaskCommit(
                task_id=task_id,
                commit_hash=commit_data.commit_hash,
                message=commit_data.message,
                author=commit_data.author,
                committed_at=commit_data.committed_at,
            )
            session.add(commit)

    # This handles status transition validation (e.g. children must be terminal)
    task = await update_task_status(session, task_id, Status.done)
    return task


async def get_work_log(
    session: AsyncSession, task_id: uuid.UUID
) -> list[WorkLogEntry]:
    # Verify task exists
    await get_task(session, task_id)
    result = await session.execute(
        select(WorkLogEntry)
        .where(WorkLogEntry.task_id == task_id)
        .order_by(WorkLogEntry.created_at)
    )
    return list(result.scalars().all())


async def create_commit(
    session: AsyncSession, task_id: uuid.UUID, data: CommitCreate
) -> TaskCommit:
    await get_task(session, task_id)
    commit = TaskCommit(
        task_id=task_id,
        commit_hash=data.commit_hash,
        message=data.message,
        author=data.author,
        committed_at=data.committed_at,
    )
    session.add(commit)
    await session.flush()
    return commit


async def get_commits(
    session: AsyncSession, task_id: uuid.UUID
) -> list[TaskCommit]:
    await get_task(session, task_id)
    result = await session.execute(
        select(TaskCommit)
        .where(TaskCommit.task_id == task_id)
        .order_by(TaskCommit.committed_at)
    )
    return list(result.scalars().all())
