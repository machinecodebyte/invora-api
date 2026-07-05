from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.inventory.domain.stock import (
    ALLOWED_ITEM_UPDATE_FIELDS,
    ALLOWED_MOVEMENT_TYPES,
    PUBLIC_MOVEMENT_TYPES,
    calculate_stock_status,
    ensure_no_protected_item_fields,
)


class InventoryItemCreateRequest(BaseModel):
    product_id: UUID
    opening_stock: Decimal | None = Field(default=Decimal("0.000"))
    minimum_stock: Decimal | None = Field(default=Decimal("0.000"))
    safety_stock: Decimal | None = Field(default=Decimal("0.000"))
    is_active: bool = True
    reason: str | None = Field(default=None, max_length=1000)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: str | None = Field(default=None, max_length=128)
    occurred_at: datetime | None = None

    model_config = ConfigDict(extra="allow")

    def create_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_protected_item_fields(extra_fields)
        return {
            "opening_stock": self.opening_stock,
            "minimum_stock": self.minimum_stock,
            "safety_stock": self.safety_stock,
            "is_active": self.is_active,
            "reason": self.reason,
            "reference_type": self.reference_type,
            "reference_id": self.reference_id,
            "occurred_at": self.occurred_at,
        }


class InventoryItemUpdateRequest(BaseModel):
    minimum_stock: Decimal | None = None
    safety_stock: Decimal | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="allow")

    def update_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_protected_item_fields(extra_fields)
        return {
            field: getattr(self, field)
            for field in ALLOWED_ITEM_UPDATE_FIELDS
            if field in self.model_fields_set
        }


class InventoryProductPublic(BaseModel):
    id: UUID
    name: str
    sku: str
    category_id: UUID | None
    unit: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class InventoryItemPublic(BaseModel):
    id: UUID
    product_id: UUID
    product: InventoryProductPublic
    current_stock: Decimal
    minimum_stock: Decimal
    safety_stock: Decimal
    stock_status: Literal["in_stock", "low_stock", "out_of_stock", "inactive"]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class InventoryItemData(BaseModel):
    item: InventoryItemPublic


class InventoryItemListData(BaseModel):
    items: list[InventoryItemPublic]
    total: int
    limit: int
    offset: int


class InventoryItemResponse(BaseModel):
    success: Literal[True] = True
    data: InventoryItemData


class InventoryItemListResponse(BaseModel):
    success: Literal[True] = True
    data: InventoryItemListData


class StockMovementCreateRequest(BaseModel):
    product_id: UUID
    movement_type: Literal["stock_in", "stock_out", "adjustment", "correction"]
    quantity: Decimal
    reason: str | None = Field(default=None, max_length=1000)
    reference_type: str | None = Field(default=None, max_length=64)
    reference_id: str | None = Field(default=None, max_length=128)
    occurred_at: datetime | None = None


class StockMovementPublic(BaseModel):
    id: UUID
    product_id: UUID
    inventory_item_id: UUID
    movement_type: Literal[
        "opening_stock",
        "stock_in",
        "stock_out",
        "adjustment",
        "correction",
    ]
    quantity_delta: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    reason: str | None
    reference_type: str | None
    reference_id: str | None
    occurred_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StockMovementData(BaseModel):
    movement: StockMovementPublic


class StockMovementListData(BaseModel):
    movements: list[StockMovementPublic]
    total: int
    limit: int
    offset: int


class StockMovementResponse(BaseModel):
    success: Literal[True] = True
    data: StockMovementData


class StockMovementListResponse(BaseModel):
    success: Literal[True] = True
    data: StockMovementListData


class LowStockItemPublic(InventoryItemPublic):
    pass


class LowStockItemListData(BaseModel):
    items: list[LowStockItemPublic]
    total: int
    limit: int
    offset: int


class LowStockItemResponse(BaseModel):
    success: Literal[True] = True
    data: LowStockItemListData


class InventorySummaryData(BaseModel):
    total_inventory_items: int
    total_products_tracked: int
    low_stock_count: int
    out_of_stock_count: int
    total_stock_quantity: Decimal
    recent_movement_count: int


class InventorySummaryResponse(BaseModel):
    success: Literal[True] = True
    data: InventorySummaryData


def inventory_item_public(item: object) -> InventoryItemPublic:
    return InventoryItemPublic(
        id=item.id,
        product_id=item.product_id,
        product=InventoryProductPublic.model_validate(item.product),
        current_stock=item.current_stock,
        minimum_stock=item.minimum_stock,
        safety_stock=item.safety_stock,
        stock_status=calculate_stock_status(
            current_stock=item.current_stock,
            minimum_stock=item.minimum_stock,
            is_active=item.is_active,
        ),
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def low_stock_item_public(item: object) -> LowStockItemPublic:
    return LowStockItemPublic(**inventory_item_public(item).model_dump())


def allowed_inventory_movement_types() -> tuple[str, ...]:
    return ALLOWED_MOVEMENT_TYPES


def public_inventory_movement_types() -> tuple[str, ...]:
    return PUBLIC_MOVEMENT_TYPES
