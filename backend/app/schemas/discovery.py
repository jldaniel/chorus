from datetime import datetime
from enum import Enum

from app.schemas.task import TaskRead


class OperationFilter(str, Enum):
    sizing = "sizing"
    breakdown = "breakdown"
    implementation = "implementation"


class TaskWithLockInfo(TaskRead):
    lock_caller_label: str | None = None
    lock_purpose: str | None = None
    lock_expires_at: datetime | None = None
