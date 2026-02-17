import uuid

from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, lock_purpose_enum


class TaskLock(Base):
    __tablename__ = "task_locks"
    __table_args__ = (
        Index("idx_locks_task", "task_id", unique=True),
        Index("idx_locks_expiry", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    caller_label: Mapped[str] = mapped_column(String(255), nullable=False)
    lock_purpose = mapped_column(lock_purpose_enum, nullable=False)
    acquired_at = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    last_heartbeat_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    expires_at = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    task = relationship("Task", back_populates="lock")
