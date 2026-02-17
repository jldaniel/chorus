import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.task import (
    ReorderRequest,
    StatusUpdate,
    TaskContextResponse,
    TaskCreate,
    TaskRead,
    TaskTreeNode,
    TaskUpdate,
)
from app.services import task_service

router = APIRouter(tags=["tasks"])


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create_task(
    project_id: uuid.UUID,
    data: TaskCreate,
    session: AsyncSession = Depends(get_session),
):
    task = await task_service.create_task(session, project_id, data)
    await session.commit()
    return task_service.enrich_task(task)


@router.post("/tasks/{task_id}/subtasks", response_model=TaskRead, status_code=201)
async def create_subtask(
    task_id: uuid.UUID,
    data: TaskCreate,
    session: AsyncSession = Depends(get_session),
):
    parent = await task_service.get_task(session, task_id)
    task = await task_service.create_task(session, parent.project_id, data, parent_task_id=task_id)
    await session.commit()
    return task_service.enrich_task(task)


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    task = await task_service.get_task(session, task_id)
    return task_service.enrich_task(task)


@router.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_session),
):
    task = await task_service.update_task(session, task_id, data)
    await session.commit()
    return task_service.enrich_task(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    await task_service.delete_task(session, task_id)
    await session.commit()


@router.get("/tasks/{task_id}/tree", response_model=TaskTreeNode)
async def get_task_tree(
    task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await task_service.get_task_tree(session, task_id)


@router.get("/tasks/{task_id}/ancestry", response_model=list[TaskRead])
async def get_task_ancestry(
    task_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    tasks = await task_service.get_task_ancestry(session, task_id)
    return [task_service.enrich_task(t) for t in tasks]


@router.get("/tasks/{task_id}/context", response_model=TaskContextResponse)
async def get_task_context(
    task_id: uuid.UUID,
    include_commits: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    return await task_service.get_task_context(session, task_id, include_commits)


@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
async def update_task_status(
    task_id: uuid.UUID,
    data: StatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    task = await task_service.update_task_status(session, task_id, data.status)
    await session.commit()
    return task_service.enrich_task(task)


@router.patch("/tasks/{task_id}/reorder", response_model=TaskRead)
async def reorder_task(
    task_id: uuid.UUID,
    data: ReorderRequest,
    session: AsyncSession = Depends(get_session),
):
    task = await task_service.reorder_task(session, task_id, data.position)
    await session.commit()
    return task_service.enrich_task(task)
