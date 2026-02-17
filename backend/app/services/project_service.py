import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import Status
from app.models.project import Project
from app.models.task import Task
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create_project(session: AsyncSession, data: ProjectCreate) -> Project:
    project = Project(**data.model_dump())
    session.add(project)
    await session.flush()
    await session.refresh(project)
    return project


async def list_projects(session: AsyncSession) -> list[Project]:
    result = await session.execute(select(Project).order_by(Project.created_at))
    return list(result.scalars().all())


async def get_project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def update_project(
    session: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate
) -> Project:
    project = await get_project(session, project_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.flush()
    await session.refresh(project)
    return project


async def delete_project(session: AsyncSession, project_id: uuid.UUID) -> None:
    project = await get_project(session, project_id)
    await session.delete(project)
    await session.flush()


async def get_project_detail(session: AsyncSession, project_id: uuid.UUID) -> dict:
    project = await get_project(session, project_id)

    result = await session.execute(
        select(
            func.count(Task.id),
            func.coalesce(func.sum(Task.points), 0),
            func.coalesce(
                func.sum(Task.points).filter(Task.status == Status.done), 0
            ),
        ).where(Task.project_id == project_id)
    )
    row = result.one()

    return {
        **ProjectCreate.model_validate(project, from_attributes=True).model_dump(),
        "id": project.id,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "task_count": row[0],
        "points_total": row[1],
        "points_completed": row[2],
    }


async def get_project_tasks(
    session: AsyncSession, project_id: uuid.UUID
) -> list[Task]:
    await get_project(session, project_id)  # 404 check
    result = await session.execute(
        select(Task)
        .where(Task.project_id == project_id, Task.parent_task_id.is_(None))
        .options(selectinload(Task.children), selectinload(Task.lock))
        .order_by(Task.position)
    )
    return list(result.scalars().all())
