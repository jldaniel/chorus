import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.atomic import (
    BreakdownRequest,
    CommitCreate,
    CompleteRequest,
    FlagRefinementRequest,
    RefineRequest,
    SizingRequest,
)
from app.schemas.task import CommitRead, TaskRead, WorkLogEntryRead
from app.schemas.work_log import WorkLogCreate
from app.services import atomic_service
from app.services.task_service import enrich_task

router = APIRouter(tags=["atomic operations"])


@router.post("/tasks/{task_id}/size", response_model=TaskRead)
async def size_task(
    task_id: uuid.UUID,
    data: SizingRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await atomic_service.size_task(session, task_id, data)
    await session.commit()
    return enrich_task(task)


@router.post("/tasks/{task_id}/breakdown", response_model=TaskRead)
async def breakdown_task(
    task_id: uuid.UUID,
    data: BreakdownRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await atomic_service.breakdown_task(session, task_id, data)
    await session.commit()
    return enrich_task(task)


@router.post("/tasks/{task_id}/refine", response_model=TaskRead)
async def refine_task(
    task_id: uuid.UUID,
    data: RefineRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await atomic_service.refine_task(session, task_id, data)
    await session.commit()
    return enrich_task(task)


@router.post("/tasks/{task_id}/flag-refinement", response_model=TaskRead)
async def flag_refinement(
    task_id: uuid.UUID,
    data: FlagRefinementRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await atomic_service.flag_refinement(session, task_id, data)
    await session.commit()
    return enrich_task(task)


@router.post("/tasks/{task_id}/complete", response_model=TaskRead)
async def complete_task(
    task_id: uuid.UUID,
    data: CompleteRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await atomic_service.complete_task(session, task_id, data)
    await session.commit()
    return enrich_task(task)


@router.post("/tasks/{task_id}/work-log", response_model=WorkLogEntryRead, status_code=201)
async def create_work_log(
    task_id: uuid.UUID,
    data: WorkLogCreate,
    session: AsyncSession = Depends(get_session),
):
    entry = await atomic_service.create_work_log_entry(
        session, task_id, data.operation, data.content, data.author
    )
    await session.commit()
    return entry


@router.get("/tasks/{task_id}/work-log", response_model=list[WorkLogEntryRead])
async def get_work_log(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    return await atomic_service.get_work_log(session, task_id)


@router.post("/tasks/{task_id}/commits", response_model=CommitRead, status_code=201)
async def create_commit(
    task_id: uuid.UUID,
    data: CommitCreate,
    session: AsyncSession = Depends(get_session),
):
    commit = await atomic_service.create_commit(session, task_id, data)
    await session.commit()
    return commit


@router.get("/tasks/{task_id}/commits", response_model=list[CommitRead])
async def get_commits(
    task_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    return await atomic_service.get_commits(session, task_id)
