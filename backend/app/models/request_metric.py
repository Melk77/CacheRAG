import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class RequestMetric(Base):
    __tablename__ = "request_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    collection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True,
    )

    question: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    cache_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    response_time_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    cache_lookup_time_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    retrieval_time_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    rerank_time_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    llm_time_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    cache_write_time_ms: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_request_metrics_collection_id", "collection_id"),
        Index("ix_request_metrics_cache_status", "cache_status"),
        Index("ix_request_metrics_created_at", "created_at"),
    )