from datetime import date
from decimal import Decimal

import pytest

from app.modules.sales.domain.exceptions import (
    InvalidSalesTransactionDateRangeError,
    InvalidSalesTransactionFieldError,
    InvalidSalesTransactionPriceError,
    InvalidSalesTransactionQuantityError,
    InvalidSalesTransactionSortFieldError,
    InvalidSalesTransactionSourceError,
)
from app.modules.sales.domain.transactions import (
    ALLOWED_TRANSACTION_UPDATE_FIELDS,
    calculate_total_amount,
    ensure_no_unsupported_transaction_fields,
    ensure_transaction_sort_field,
    normalize_transaction_create_values,
    normalize_transaction_update_values,
    validate_date_range,
    validate_money,
    validate_quantity,
    validate_source,
)


def test_sales_transaction_create_values_calculate_amount() -> None:
    values = normalize_transaction_create_values(
        {
            "product_id": "product-id",
            "sale_date": date(2026, 7, 1),
            "quantity": "3.000",
            "unit_price": "12.50",
            "total_amount": None,
            "customer_name": "  Walk   In ",
            "channel": " store ",
            "notes": "",
        }
    )

    assert values["quantity"] == Decimal("3.000")
    assert values["total_amount"] == Decimal("37.50")
    assert values["customer_name"] == "Walk In"
    assert values["notes"] is None
    assert values["source"] == "manual"


def test_sales_transaction_quantity_validation() -> None:
    assert validate_quantity("1.250") == Decimal("1.250")

    with pytest.raises(InvalidSalesTransactionQuantityError):
        validate_quantity("0")


def test_sales_transaction_price_validation() -> None:
    assert validate_money("10.50", field_name="unit_price") == Decimal("10.50")

    with pytest.raises(InvalidSalesTransactionPriceError):
        validate_money("-1.00", field_name="unit_price")


def test_sales_transaction_total_amount_calculation() -> None:
    total = calculate_total_amount(
        quantity=Decimal("2.000"),
        unit_price=Decimal("4.25"),
        total_amount=None,
    )

    assert total == Decimal("8.50")


def test_sales_transaction_update_recalculates_amount() -> None:
    values = normalize_transaction_update_values(
        {"quantity": Decimal("4.000")},
        current_quantity=Decimal("2.000"),
        current_unit_price=Decimal("5.00"),
        current_total_amount=Decimal("10.00"),
    )

    assert values["quantity"] == Decimal("4.000")
    assert values["total_amount"] == Decimal("20.00")


def test_sales_transaction_date_range_validation() -> None:
    validate_date_range(date(2026, 7, 1), date(2026, 7, 2))

    with pytest.raises(InvalidSalesTransactionDateRangeError):
        validate_date_range(date(2026, 7, 2), date(2026, 7, 1))


def test_sales_transaction_source_validation() -> None:
    assert validate_source("CSV_UPLOAD") == "csv_upload"

    with pytest.raises(InvalidSalesTransactionSourceError):
        validate_source("inventory")


def test_sales_transaction_sort_validation() -> None:
    assert ensure_transaction_sort_field("product_name") == "product_name"

    with pytest.raises(InvalidSalesTransactionSortFieldError):
        ensure_transaction_sort_field("deleted_at")


def test_sales_transaction_protected_field_rejection() -> None:
    with pytest.raises(InvalidSalesTransactionFieldError):
        ensure_no_unsupported_transaction_fields(
            extra_fields={"source"},
            allowed_fields=ALLOWED_TRANSACTION_UPDATE_FIELDS,
        )
