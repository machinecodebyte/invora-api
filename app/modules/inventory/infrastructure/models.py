from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.modules.products.infrastructure.models import ProductModel
from app.shared.utils import utc_now


class InventoryItemModel(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "product_id",
            name="uq_inventory_items_user_product",
        ),
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
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    current_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0.000"),
    )
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0.000"),
    )
    safety_stock: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        default=Decimal("0.000"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    product: Mapped[ProductModel] = relationship()
    movements: Mapped[list[InventoryStockMovementModel]] = relationship(
        back_populates="inventory_item",
    )


class InventoryStockMovementModel(Base):
    __tablename__ = "inventory_stock_movements"

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
    product_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        index=True,
    )
    inventory_item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        index=True,
    )
    movement_type: Mapped[str] = mapped_column(String(32), index=True)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    quantity_before: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    quantity_after: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
    )

    inventory_item: Mapped[InventoryItemModel] = relationship(
        back_populates="movements",
    )
    product: Mapped[ProductModel] = relationship()
