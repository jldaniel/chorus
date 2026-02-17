import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import Status, TaskType


class ExportWorkLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    author: str | None
    operation: str
    content: str
    created_at: datetime


class ExportCommit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    author: str | None
    commit_hash: str
    message: str | None
    committed_at: datetime


class ExportTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_task_id: uuid.UUID | None
    name: str
    description: str | None
    context: str | None
    task_type: TaskType
    status: Status
    points: int | None
    position: int
    created_at: datetime
    updated_at: datetime
    work_log_entries: list[ExportWorkLogEntry] = []
    commits: list[ExportCommit] = []


class ProjectExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    exported_at: datetime
    tasks: list[ExportTask]
