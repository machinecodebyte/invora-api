from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.products.domain.exceptions import (
    InvalidProductFieldError,
    InvalidProductPriceError,
    InvalidProductSkuError,
    InvalidProductSortFieldError,
    InvalidProductUnitError,
)

ALLOWED_PRODUCT_UNITS = (
    "pcs",
    "kg",
    "gram",
    "liter",
    "ml",
    "box",
    "packet",
    "dozen",
)

ALLOWED_PRODUCT_FIELDS = {
    "name",
    "sku",
    "category_id",
    "description",
    "unit",
    "selling_price",
    "cost_price",
    "is_active",
}
ALLOWED_CATEGORY_FIELDS = {"name", "description", "is_active"}
PROTECTED_CATALOG_FIELDS = {
    "id",
    "user_id",
    "created_at",
    "updated_at",
    "current_stock",
    "stock",
    "quantity_on_hand",
}
PRODUCT_SORT_FIELDS = {
    "name",
    "sku",
    "selling_price",
    "cost_price",
    "created_at",
    "updated_at",
    "is_active",
}
CATEGORY_SORT_FIELDS = {
    "name",
    "created_at",
    "updated_at",
    "is_active",
}

SKU_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
MAX_NAME_LENGTH = 255
MAX_SKU_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 2000
MONEY_QUANTUM = Decimal("0.01")


def normalize_product_name(value: str) -> str:
    return _normalize_required_text(value, "Product name", MAX_NAME_LENGTH)


def normalize_category_name(value: str) -> str:
    return _normalize_required_text(value, "Category name", MAX_NAME_LENGTH)


def normalize_category_key(value: str) -> str:
    return normalize_category_name(value).casefold()


def normalize_sku(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidProductSkuError("Product SKU must be a string.")

    normalized = re.sub(r"\s+", "-", value.strip().upper())
    normalized = normalized.strip(".-_")
    if not normalized:
        raise InvalidProductSkuError("Product SKU is required.")
    if len(normalized) > MAX_SKU_LENGTH:
        raise InvalidProductSkuError("Product SKU is too long.")
    if not SKU_PATTERN.fullmatch(normalized):
        raise InvalidProductSkuError(
            "Product SKU may contain only letters, numbers, dots, dashes, "
            "or underscores."
        )
    return normalized


def validate_unit(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidProductUnitError()
    normalized = value.strip().lower()
    if normalized not in ALLOWED_PRODUCT_UNITS:
        raise InvalidProductUnitError()
    return normalized


def validate_price(
    value: Decimal | int | str | None,
    *,
    field_name: str,
) -> Decimal | None:
    if value is None:
        return None

    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidProductPriceError(f"{field_name} must be a valid number.") from exc

    if price < Decimal("0"):
        raise InvalidProductPriceError(f"{field_name} cannot be negative.")
    if price.as_tuple().exponent < -2:
        raise InvalidProductPriceError(
            f"{field_name} cannot have more than 2 decimals."
        )
    if price >= Decimal("10000000000"):
        raise InvalidProductPriceError(f"{field_name} is too large.")

    return price.quantize(MONEY_QUANTUM)


def normalize_optional_description(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidProductFieldError("Description must be a string or null.")
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    if len(normalized) > MAX_DESCRIPTION_LENGTH:
        raise InvalidProductFieldError("Description is too long.")
    return normalized


def ensure_no_unsupported_fields(
    *,
    extra_fields: set[str],
    allowed_fields: set[str],
    resource_name: str,
) -> None:
    blocked = sorted(extra_fields & PROTECTED_CATALOG_FIELDS)
    if blocked:
        raise InvalidProductFieldError(
            f"{resource_name} field cannot be set: {', '.join(blocked)}."
        )

    unsupported = sorted(extra_fields - allowed_fields)
    if unsupported:
        raise InvalidProductFieldError(
            f"Unsupported {resource_name.lower()} field: {', '.join(unsupported)}."
        )


def normalize_product_values(
    values: dict[str, Any],
    *,
    partial: bool,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for field, value in values.items():
        if field not in ALLOWED_PRODUCT_FIELDS:
            raise InvalidProductFieldError(f"Unsupported product field: {field}.")

        if field == "name":
            normalized["name"] = normalize_product_name(value)
            normalized["normalized_name"] = normalized["name"].casefold()
        elif field == "sku":
            normalized_sku = normalize_sku(value)
            normalized["sku"] = normalized_sku
            normalized["normalized_sku"] = normalized_sku
        elif field == "description":
            normalized["description"] = normalize_optional_description(value)
        elif field == "unit":
            normalized["unit"] = validate_unit(value)
        elif field == "selling_price":
            price = validate_price(value, field_name="selling_price")
            normalized["selling_price"] = price or Decimal("0.00")
        elif field == "cost_price":
            normalized["cost_price"] = validate_price(value, field_name="cost_price")
        elif field == "is_active":
            normalized["is_active"] = _validate_bool(value, "is_active")
        elif field == "category_id":
            normalized["category_id"] = value

    if not partial:
        missing = {"name", "sku", "unit"} - values.keys()
        if missing:
            raise InvalidProductFieldError(
                f"Missing product field: {', '.join(sorted(missing))}."
            )
        normalized.setdefault("selling_price", Decimal("0.00"))

    if not normalized:
        raise InvalidProductFieldError("At least one product field is required.")

    return normalized


def normalize_category_values(
    values: dict[str, Any],
    *,
    partial: bool,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}

    for field, value in values.items():
        if field not in ALLOWED_CATEGORY_FIELDS:
            raise InvalidProductFieldError(f"Unsupported category field: {field}.")

        if field == "name":
            normalized["name"] = normalize_category_name(value)
            normalized["normalized_name"] = normalized["name"].casefold()
        elif field == "description":
            normalized["description"] = normalize_optional_description(value)
        elif field == "is_active":
            normalized["is_active"] = _validate_bool(value, "is_active")

    if not partial and "name" not in values:
        raise InvalidProductFieldError("Missing category field: name.")
    if not normalized:
        raise InvalidProductFieldError("At least one category field is required.")

    return normalized


def ensure_product_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in PRODUCT_SORT_FIELDS:
        raise InvalidProductSortFieldError()
    return normalized


def ensure_category_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in CATEGORY_SORT_FIELDS:
        raise InvalidProductSortFieldError()
    return normalized


def normalize_sort_order(sort_order: str) -> str:
    normalized = sort_order.strip().lower()
    if normalized not in {"asc", "desc"}:
        raise InvalidProductSortFieldError()
    return normalized


def _normalize_required_text(value: str, label: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise InvalidProductFieldError(f"{label} must be a string.")
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise InvalidProductFieldError(f"{label} is required.")
    if len(normalized) > max_length:
        raise InvalidProductFieldError(f"{label} is too long.")
    return normalized


def _validate_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidProductFieldError(f"{field_name} must be a boolean.")
    return value
