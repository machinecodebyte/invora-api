from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from app.modules.inventory.domain.exceptions import (
    InsufficientStockError,
    InvalidInventoryFieldError,
    InvalidInventoryMovementTypeError,
    InvalidInventorySortFieldError,
    InvalidInventoryThresholdError,
    InvalidStockQuantityError,
)

MovementType = Literal[
    "opening_stock",
    "stock_in",
    "stock_out",
    "adjustment",
    "correction",
]
StockStatus = Literal["in_stock", "low_stock", "out_of_stock", "inactive"]

ALLOWED_MOVEMENT_TYPES = (
    "opening_stock",
    "stock_in",
    "stock_out",
    "adjustment",
    "correction",
)
PUBLIC_MOVEMENT_TYPES = ("stock_in", "stock_out", "adjustment", "correction")
ALLOWED_STOCK_STATUSES = ("in_stock", "low_stock", "out_of_stock", "inactive")
ALLOWED_ITEM_UPDATE_FIELDS = {"minimum_stock", "safety_stock", "is_active"}
PROTECTED_ITEM_FIELDS = {
    "id",
    "user_id",
    "product_id",
    "current_stock",
    "opening_stock",
    "stock",
    "created_at",
    "updated_at",
}
ITEM_SORT_FIELDS = {
    "product_name",
    "sku",
    "current_stock",
    "minimum_stock",
    "safety_stock",
    "created_at",
    "updated_at",
    "is_active",
}
MOVEMENT_SORT_FIELDS = {"occurred_at", "created_at"}

QUANTITY_QUANTUM = Decimal("0.001")
MAX_STOCK_QUANTITY = Decimal("100000000000")


def normalize_stock_quantity(
    value: Decimal | int | str | None,
    *,
    field_name: str,
) -> Decimal:
    if value is None:
        raise InvalidStockQuantityError(f"{field_name} is required.")

    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidStockQuantityError(
            f"{field_name} must be a valid number."
        ) from exc

    if quantity < Decimal("0"):
        raise InvalidStockQuantityError(f"{field_name} cannot be negative.")
    if quantity.as_tuple().exponent < -3:
        raise InvalidStockQuantityError(
            f"{field_name} cannot have more than 3 decimals."
        )
    if quantity >= MAX_STOCK_QUANTITY:
        raise InvalidStockQuantityError(f"{field_name} is too large.")

    return quantity.quantize(QUANTITY_QUANTUM)


def normalize_signed_quantity(
    value: Decimal | int | str | None,
    *,
    field_name: str,
) -> Decimal:
    if value is None:
        raise InvalidStockQuantityError(f"{field_name} is required.")

    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidStockQuantityError(
            f"{field_name} must be a valid number."
        ) from exc

    if quantity == Decimal("0"):
        raise InvalidStockQuantityError(f"{field_name} cannot be zero.")
    if quantity.as_tuple().exponent < -3:
        raise InvalidStockQuantityError(
            f"{field_name} cannot have more than 3 decimals."
        )
    if abs(quantity) >= MAX_STOCK_QUANTITY:
        raise InvalidStockQuantityError(f"{field_name} is too large.")

    return quantity.quantize(QUANTITY_QUANTUM)


def normalize_threshold(
    value: Decimal | int | str | None,
    *,
    field_name: str,
) -> Decimal:
    try:
        return normalize_stock_quantity(value, field_name=field_name)
    except InvalidStockQuantityError as exc:
        raise InvalidInventoryThresholdError(exc.message) from exc


def validate_public_movement_type(value: str) -> str:
    normalized = _normalize_movement_type(value)
    if normalized not in PUBLIC_MOVEMENT_TYPES:
        raise InvalidInventoryMovementTypeError()
    return normalized


def validate_internal_movement_type(value: str) -> str:
    normalized = _normalize_movement_type(value)
    if normalized not in ALLOWED_MOVEMENT_TYPES:
        raise InvalidInventoryMovementTypeError()
    return normalized


def calculate_movement(
    *,
    movement_type: str,
    current_stock: Decimal,
    quantity: Decimal,
) -> tuple[Decimal, Decimal]:
    movement_type = validate_internal_movement_type(movement_type)
    current_stock = normalize_stock_quantity(
        current_stock,
        field_name="current_stock",
    )

    if movement_type in {"opening_stock", "stock_in"}:
        normalized_quantity = normalize_stock_quantity(quantity, field_name="quantity")
        if normalized_quantity <= Decimal("0"):
            raise InvalidStockQuantityError("quantity must be greater than zero.")
        quantity_delta = normalized_quantity
        quantity_after = current_stock + quantity_delta
    elif movement_type == "stock_out":
        normalized_quantity = normalize_stock_quantity(quantity, field_name="quantity")
        if normalized_quantity <= Decimal("0"):
            raise InvalidStockQuantityError("quantity must be greater than zero.")
        quantity_delta = -normalized_quantity
        quantity_after = current_stock + quantity_delta
    elif movement_type == "adjustment":
        quantity_after = normalize_stock_quantity(quantity, field_name="quantity")
        quantity_delta = quantity_after - current_stock
    else:
        quantity_delta = normalize_signed_quantity(quantity, field_name="quantity")
        quantity_after = current_stock + quantity_delta

    if quantity_after < Decimal("0"):
        raise InsufficientStockError()

    return quantity_delta.quantize(QUANTITY_QUANTUM), quantity_after.quantize(
        QUANTITY_QUANTUM
    )


def calculate_stock_status(
    *,
    current_stock: Decimal,
    minimum_stock: Decimal,
    is_active: bool,
) -> StockStatus:
    current_stock = normalize_stock_quantity(
        current_stock,
        field_name="current_stock",
    )
    minimum_stock = normalize_threshold(minimum_stock, field_name="minimum_stock")

    if not is_active:
        return "inactive"
    if current_stock == Decimal("0.000"):
        return "out_of_stock"
    if current_stock <= minimum_stock:
        return "low_stock"
    return "in_stock"


def normalize_item_create_values(values: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "opening_stock": normalize_stock_quantity(
            values.get("opening_stock", Decimal("0")),
            field_name="opening_stock",
        ),
        "minimum_stock": normalize_threshold(
            values.get("minimum_stock", Decimal("0")),
            field_name="minimum_stock",
        ),
        "safety_stock": normalize_threshold(
            values.get("safety_stock", Decimal("0")),
            field_name="safety_stock",
        ),
    }
    if not isinstance(values.get("is_active", True), bool):
        raise InvalidInventoryFieldError("is_active must be a boolean.")
    normalized["is_active"] = values.get("is_active", True)
    return normalized


def normalize_item_update_values(values: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for field, value in values.items():
        if field not in ALLOWED_ITEM_UPDATE_FIELDS:
            raise InvalidInventoryFieldError(f"Unsupported inventory field: {field}.")
        if field in {"minimum_stock", "safety_stock"}:
            normalized[field] = normalize_threshold(value, field_name=field)
        elif field == "is_active":
            if not isinstance(value, bool):
                raise InvalidInventoryFieldError("is_active must be a boolean.")
            normalized[field] = value

    if not normalized:
        raise InvalidInventoryFieldError("At least one inventory field is required.")

    return normalized


def ensure_no_protected_item_fields(extra_fields: set[str]) -> None:
    blocked = sorted(extra_fields & PROTECTED_ITEM_FIELDS)
    if blocked:
        raise InvalidInventoryFieldError(
            f"Inventory field cannot be set directly: {', '.join(blocked)}."
        )

    if extra_fields:
        raise InvalidInventoryFieldError(
            f"Unsupported inventory field: {', '.join(sorted(extra_fields))}."
        )


def ensure_item_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in ITEM_SORT_FIELDS:
        raise InvalidInventorySortFieldError()
    return normalized


def ensure_movement_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in MOVEMENT_SORT_FIELDS:
        raise InvalidInventorySortFieldError()
    return normalized


def normalize_sort_order(sort_order: str) -> str:
    normalized = sort_order.strip().lower()
    if normalized not in {"asc", "desc"}:
        raise InvalidInventorySortFieldError()
    return normalized


def normalize_stock_status_filter(stock_status: str | None) -> str | None:
    if stock_status is None:
        return None
    normalized = stock_status.strip().lower()
    if normalized not in ALLOWED_STOCK_STATUSES:
        raise InvalidInventoryFieldError("stock_status is invalid.")
    return normalized


def _normalize_movement_type(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidInventoryMovementTypeError()
    return value.strip().lower()
