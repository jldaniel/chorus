import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.export import ProjectExportResponse
from app.schemas.project import ProjectCreate, ProjectDetail, ProjectRead, ProjectUpdate
from app.schemas.task import TaskRead
from app.services import project_service, task_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=201)
async def create_project(
    data: ProjectCreate, session: AsyncSession = Depends(get_session)
):
    project = await project_service.create_project(session, data)
    await session.commit()
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(session: AsyncSession = Depends(get_session)):
    return await project_service.list_projects(session)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await project_service.get_project_detail(session, project_id)


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
):
    project = await project_service.update_project(session, project_id, data)
    await session.commit()
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    await project_service.delete_project(session, project_id)
    await session.commit()


@router.get("/{project_id}/export", response_model=ProjectExportResponse)
async def export_project(
    project_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    return await project_service.export_project(session, project_id)


@router.get("/{project_id}/tasks", response_model=list[TaskRead])
async def get_project_tasks(
    project_id: uuid.UUID, session: AsyncSession = Depends(get_session)
):
    tasks = await project_service.get_project_tasks(session, project_id)
    return [task_service.enrich_task(t) for t in tasks]
