import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ChorusError
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
        raise ChorusError(404, "NOT_FOUND", "Project not found")
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


async def export_project(session: AsyncSession, project_id: uuid.UUID) -> dict:
    project = await get_project(session, project_id)

    result = await session.execute(
        select(Task)
        .where(Task.project_id == project_id)
        .options(
            selectinload(Task.work_log_entries),
            selectinload(Task.commits),
        )
        .order_by(Task.position)
    )
    tasks = list(result.scalars().all())

    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "exported_at": datetime.now(timezone.utc),
        "tasks": [
            {
                "id": t.id,
                "parent_task_id": t.parent_task_id,
                "name": t.name,
                "description": t.description,
                "context": t.context,
                "task_type": t.task_type,
                "status": t.status,
                "points": t.points,
                "position": t.position,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
                "work_log_entries": [
                    {
                        "id": e.id,
                        "task_id": e.task_id,
                        "author": e.author,
                        "operation": e.operation.value if hasattr(e.operation, "value") else e.operation,
                        "content": e.content,
                        "created_at": e.created_at,
                    }
                    for e in (t.work_log_entries or [])
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
                    for c in (t.commits or [])
                ],
            }
            for t in tasks
        ],
    }
