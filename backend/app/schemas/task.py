import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.base import Status, TaskType


class TaskCreate(BaseModel):
    name: str
    description: str | None = None
    context: str | None = None
    task_type: TaskType
    position: int | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    context: str | None = None
    task_type: TaskType | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
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

    # Computed fields
    effective_points: int | None
    rolled_up_points: int | None
    unsized_children: int
    readiness: str
    children_count: int
    is_locked: bool


class TaskTreeNode(TaskRead):
    children: list["TaskTreeNode"] = []


class TaskAncestryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    context: str | None
    updated_at: datetime


class WorkLogEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    author: str | None
    operation: str
    content: str
    created_at: datetime


class CommitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    author: str | None
    commit_hash: str
    message: str | None
    committed_at: datetime


class TaskContextResponse(BaseModel):
    task: TaskRead
    ancestors: list[TaskAncestryItem]
    work_log: list[WorkLogEntryRead]
    commits: list[CommitRead] | None = None
    context_captured_at: datetime | None
    context_freshness: Literal["fresh", "stale"]
    stale_reasons: list[str]


class StatusUpdate(BaseModel):
    status: Status


class ReorderRequest(BaseModel):
    position: int
