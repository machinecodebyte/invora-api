from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.forecasting.infrastructure.models import ForecastRunModel
from app.modules.products.infrastructure.models import ProductModel
from app.shared.utils import utc_now


class ReorderRecommendationModel(Base):
    __tablename__ = "reorder_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "forecast_run_id",
            "product_id",
            name="uq_reorder_recommendations_run_product",
        ),
        Index("ix_reorder_recommendations_user_run", "user_id", "forecast_run_id"),
        Index("ix_reorder_recommendations_user_risk", "user_id", "risk_level"),
        Index("ix_reorder_recommendations_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    forecast_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        index=True,
    )
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    predicted_demand: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    current_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0.000"),
    )
    safety_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0.000"),
    )
    required_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reorder_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    stock_gap: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    recommended_action: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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

    forecast_run: Mapped[ForecastRunModel] = relationship()
    product: Mapped[ProductModel] = relationship()
