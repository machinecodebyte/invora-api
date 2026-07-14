from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.shared.utils import utc_now

JSON_DATA = JSON().with_variant(JSONB, "postgresql")


class BackgroundJobModel(Base):
    __tablename__ = "background_jobs"
    __table_args__ = (
        Index("ix_background_jobs_user_status", "user_id", "status"),
        Index("ix_background_jobs_user_job_type", "user_id", "job_type"),
        Index("ix_background_jobs_user_entity", "user_id", "entity_id"),
        Index("ix_background_jobs_queue_status", "queue_name", "status"),
        Index(
            "uq_background_jobs_active_forecast_run",
            "job_type",
            "entity_type",
            "entity_id",
            unique=True,
            postgresql_where=text(
                "status IN ('queued', 'started', 'retrying') "
                "AND entity_type = 'forecast_run' "
                "AND entity_id IS NOT NULL"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    rq_job_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    queue_name: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    timeout_seconds: Mapped[int] = mapped_column(Integer)
    enqueued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_DATA,
        nullable=True,
    )
    job_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON_DATA,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
