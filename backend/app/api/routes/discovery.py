import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.discovery import OperationFilter, TaskWithLockInfo
from app.schemas.task import TaskRead
from app.services import discovery_service, project_service

router = APIRouter(tags=["discovery"])


@router.get("/projects/{project_id}/backlog", response_model=list[TaskRead])
async def get_backlog(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    await project_service.get_project(session, project_id)
    return await discovery_service.get_backlog(session, project_id, limit, offset)


@router.get("/projects/{project_id}/in-progress", response_model=list[TaskWithLockInfo])
async def get_in_progress(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    await project_service.get_project(session, project_id)
    return await discovery_service.get_in_progress(session, project_id, limit, offset)


@router.get("/projects/{project_id}/needs-refinement", response_model=list[TaskRead])
async def get_needs_refinement(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    await project_service.get_project(session, project_id)
    return await discovery_service.get_needs_refinement(session, project_id, limit, offset)


@router.get("/tasks/available", response_model=list[TaskRead])
async def get_available(
    operation: OperationFilter,
    project_id: uuid.UUID | None = Query(None),
    task_type: str | None = Query(None),
    min_points: int | None = Query(None, ge=0),
    max_points: int | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    return await discovery_service.get_available(
        session,
        operation=operation.value,
        project_id=project_id,
        task_type=task_type,
        min_points=min_points,
        max_points=max_points,
        limit=limit,
        offset=offset,
    )
