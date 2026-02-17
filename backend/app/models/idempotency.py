import uuid

from sqlalchemy import Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        Index("idx_idempotency_key", "key", unique=True),
        Index("idx_idempotency_expires", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    status_code: Mapped[int] = mapped_column(nullable=False)
    response_body = mapped_column(JSONB, nullable=False)
    created_at = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    expires_at = mapped_column(TIMESTAMP(timezone=True), nullable=False)
