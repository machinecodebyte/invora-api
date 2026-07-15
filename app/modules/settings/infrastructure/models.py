from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.shared.utils import utc_now

JSON_DATA = JSON().with_variant(JSONB, "postgresql")


class UserSystemSettingsModel(Base):
    __tablename__ = "user_system_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_system_settings_user_id"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    forecast_default_horizon_days: Mapped[int] = mapped_column(Integer, default=30)
    forecast_min_history_days: Mapped[int] = mapped_column(Integer, default=7)
    forecast_default_model: Mapped[str] = mapped_column(
        String(64),
        default="random_forest",
    )
    forecast_auto_process_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    inventory_default_minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0.000"),
    )
    inventory_default_safety_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0.000"),
    )
    inventory_low_stock_alert_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    sales_upload_duplicate_policy: Mapped[str] = mapped_column(
        String(32),
        default="reject",
    )
    sales_upload_date_format: Mapped[str] = mapped_column(
        String(32),
        default="yyyy-mm-dd",
    )
    reports_default_format: Mapped[str] = mapped_column(String(16), default="json")
    reports_include_inactive_products: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    dashboard_default_date_range_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
    )
    background_jobs_auto_retry_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    locale: Mapped[str] = mapped_column(String(16), default="en")
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON_DATA,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )
