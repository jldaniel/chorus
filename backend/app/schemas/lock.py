import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.base import LockPurpose


class LockAcquireRequest(BaseModel):
    caller_label: str
    lock_purpose: LockPurpose


class LockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    caller_label: str
    lock_purpose: LockPurpose
    acquired_at: datetime
    last_heartbeat_at: datetime | None
    expires_at: datetime
