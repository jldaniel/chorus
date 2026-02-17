import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, status_enum, task_type_enum


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("points >= 0 AND points <= 10", name="ck_tasks_points_range"),
        CheckConstraint(
            "sizing_confidence >= 0 AND sizing_confidence <= 5",
            name="ck_tasks_sizing_confidence_range",
        ),
        Index("idx_tasks_project", "project_id"),
        Index("idx_tasks_parent", "parent_task_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_points", "points"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    parent_task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type = mapped_column(task_type_enum, nullable=False)
    status = mapped_column(status_enum, nullable=False, server_default=text("'todo'"))
    points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    points_breakdown = mapped_column(JSONB, nullable=True)
    sizing_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    needs_refinement: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    refinement_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_captured_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"), onupdate=text("now()")
    )

    project = relationship("Project", back_populates="tasks")
    parent = relationship("Task", remote_side="Task.id", back_populates="children")
    children = relationship("Task", back_populates="parent", cascade="all, delete-orphan")
    lock = relationship("TaskLock", back_populates="task", uselist=False, cascade="all, delete-orphan")
    commits = relationship("TaskCommit", back_populates="task", cascade="all, delete-orphan")
    work_log_entries = relationship("WorkLogEntry", back_populates="task", cascade="all, delete-orphan")
