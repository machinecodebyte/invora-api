from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.sales.domain.exceptions import (
    InvalidSalesTransactionDateRangeError,
    InvalidSalesTransactionFieldError,
    InvalidSalesTransactionPriceError,
    InvalidSalesTransactionQuantityError,
    InvalidSalesTransactionSortFieldError,
    InvalidSalesTransactionSourceError,
)

ALLOWED_TRANSACTION_SOURCES = ("csv_upload", "manual", "api")
ALLOWED_TRANSACTION_UPDATE_FIELDS = {
    "sale_date",
    "product_id",
    "quantity",
    "unit_price",
    "total_amount",
    "customer_name",
    "channel",
    "notes",
}
PROTECTED_TRANSACTION_FIELDS = {
    "id",
    "user_id",
    "upload_batch_id",
    "source",
    "created_at",
    "updated_at",
    "deleted_at",
    "deleted_reason",
}
TRANSACTION_SORT_FIELDS = {
    "sale_date",
    "quantity",
    "unit_price",
    "total_amount",
    "source",
    "channel",
    "created_at",
    "updated_at",
    "product_name",
    "sku",
}
TREND_INTERVALS = ("day", "week", "month")
QUANTITY_QUANTUM = Decimal("0.001")
MONEY_QUANTUM = Decimal("0.01")


def normalize_transaction_create_values(values: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "product_id": values["product_id"],
        "sale_date": validate_sale_date(values["sale_date"]),
        "quantity": validate_quantity(values["quantity"]),
        "unit_price": validate_money(values.get("unit_price"), field_name="unit_price"),
        "total_amount": validate_money(
            values.get("total_amount"),
            field_name="total_amount",
        ),
        "customer_name": normalize_optional_text(values.get("customer_name"), 255),
        "channel": normalize_optional_text(values.get("channel"), 64),
        "notes": normalize_optional_text(values.get("notes"), 1000),
        "source": "manual",
    }
    normalized["total_amount"] = calculate_total_amount(
        quantity=normalized["quantity"],
        unit_price=normalized["unit_price"],
        total_amount=normalized["total_amount"],
    )
    return normalized


def normalize_transaction_update_values(
    values: dict[str, Any],
    *,
    current_quantity: Decimal,
    current_unit_price: Decimal | None,
    current_total_amount: Decimal | None,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    if "product_id" in values:
        normalized["product_id"] = values["product_id"]
    if "sale_date" in values:
        normalized["sale_date"] = validate_sale_date(values["sale_date"])
    if "quantity" in values:
        normalized["quantity"] = validate_quantity(values["quantity"])
    if "unit_price" in values:
        normalized["unit_price"] = validate_money(
            values.get("unit_price"),
            field_name="unit_price",
        )
    if "total_amount" in values:
        normalized["total_amount"] = validate_money(
            values.get("total_amount"),
            field_name="total_amount",
        )
    if "customer_name" in values:
        normalized["customer_name"] = normalize_optional_text(
            values.get("customer_name"),
            255,
        )
    if "channel" in values:
        normalized["channel"] = normalize_optional_text(values.get("channel"), 64)
    if "notes" in values:
        normalized["notes"] = normalize_optional_text(values.get("notes"), 1000)

    if not normalized:
        raise InvalidSalesTransactionFieldError(
            "At least one sales transaction field is required.",
        )

    if "total_amount" not in values and (
        "quantity" in values or "unit_price" in values
    ):
        effective_quantity = normalized.get("quantity", current_quantity)
        effective_unit_price = normalized.get("unit_price", current_unit_price)
        normalized["total_amount"] = calculate_total_amount(
            quantity=effective_quantity,
            unit_price=effective_unit_price,
            total_amount=current_total_amount,
            recalculate=True,
        )

    return normalized


def ensure_no_unsupported_transaction_fields(
    *,
    extra_fields: set[str],
    allowed_fields: set[str],
) -> None:
    blocked = sorted(extra_fields & PROTECTED_TRANSACTION_FIELDS)
    if blocked:
        raise InvalidSalesTransactionFieldError(
            f"Sales transaction field cannot be set: {', '.join(blocked)}.",
        )

    unsupported = sorted(extra_fields - allowed_fields)
    if unsupported:
        raise InvalidSalesTransactionFieldError(
            f"Unsupported sales transaction field: {', '.join(unsupported)}.",
        )


def validate_sale_date(value: date) -> date:
    if not isinstance(value, date):
        raise InvalidSalesTransactionFieldError("sale_date is invalid.")
    return value


def validate_quantity(value: Any) -> Decimal:
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidSalesTransactionQuantityError() from exc
    if quantity <= Decimal("0"):
        raise InvalidSalesTransactionQuantityError(
            "Sales transaction quantity must be positive.",
        )
    if quantity.as_tuple().exponent < -3:
        raise InvalidSalesTransactionQuantityError(
            "Sales transaction quantity cannot have more than 3 decimals.",
        )
    if quantity >= Decimal("100000000000"):
        raise InvalidSalesTransactionQuantityError(
            "Sales transaction quantity is too large.",
        )
    return quantity.quantize(QUANTITY_QUANTUM)


def validate_money(value: Any, *, field_name: str) -> Decimal | None:
    if value is None:
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidSalesTransactionPriceError(f"{field_name} is invalid.") from exc
    if amount < Decimal("0"):
        raise InvalidSalesTransactionPriceError(f"{field_name} cannot be negative.")
    if amount.as_tuple().exponent < -2:
        raise InvalidSalesTransactionPriceError(
            f"{field_name} cannot have more than 2 decimals.",
        )
    if amount >= Decimal("100000000000"):
        raise InvalidSalesTransactionPriceError(f"{field_name} is too large.")
    return amount.quantize(MONEY_QUANTUM)


def calculate_total_amount(
    *,
    quantity: Decimal,
    unit_price: Decimal | None,
    total_amount: Decimal | None,
    recalculate: bool = False,
) -> Decimal | None:
    if unit_price is None:
        return None if recalculate else total_amount
    if total_amount is None or recalculate:
        return (quantity * unit_price).quantize(MONEY_QUANTUM)
    return total_amount


def validate_date_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidSalesTransactionDateRangeError()


def validate_source(source: str | None) -> str | None:
    if source is None:
        return None
    normalized = source.strip().lower()
    if normalized not in ALLOWED_TRANSACTION_SOURCES:
        raise InvalidSalesTransactionSourceError()
    return normalized


def validate_trend_interval(interval: str) -> str:
    normalized = interval.strip().lower()
    if normalized not in TREND_INTERVALS:
        raise InvalidSalesTransactionFieldError(
            "Sales trend interval must be day, week, or month.",
        )
    return normalized


def ensure_transaction_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in TRANSACTION_SORT_FIELDS:
        raise InvalidSalesTransactionSortFieldError()
    return normalized


def normalize_sort_order(sort_order: str) -> str:
    normalized = sort_order.strip().lower()
    if normalized not in {"asc", "desc"}:
        return "desc"
    return normalized


def normalize_optional_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    return normalized[:max_length]
