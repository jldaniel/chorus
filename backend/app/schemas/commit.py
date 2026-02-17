from datetime import datetime

from pydantic import BaseModel


class CommitCreate(BaseModel):
    commit_hash: str
    message: str | None = None
    author: str | None = None
    committed_at: datetime
