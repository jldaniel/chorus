from pydantic import BaseModel

from app.models.base import Operation


class WorkLogCreate(BaseModel):
    author: str | None = None
    operation: Operation
    content: str
