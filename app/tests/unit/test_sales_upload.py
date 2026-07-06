from decimal import Decimal

import pytest

from app.modules.sales.domain.exceptions import (
    InvalidSalesCsvFormatError,
    MissingSalesCsvColumnsError,
)
from app.modules.sales.domain.upload import (
    ParsedCsvRow,
    RejectedSalesRow,
    ValidSalesRow,
    calculate_upload_status,
    parse_sales_csv,
    sanitize_filename,
    validate_sales_row,
)


def test_required_column_validation() -> None:
    with pytest.raises(MissingSalesCsvColumnsError):
        parse_sales_csv(b"sale_date,product_sku\n2026-07-01,MILK-1\n")


def test_sku_normalization_for_sales_rows() -> None:
    row = ParsedCsvRow(
        row_number=2,
        raw_data={
            "sale_date": "2026-07-01",
            "product_sku": " milk 1 ",
            "quantity": "2.000",
        },
    )

    result = validate_sales_row(row, known_skus={"MILK-1"})

    assert isinstance(result, ValidSalesRow)
    assert result.product_sku == "MILK-1"


def test_sale_date_parsing_and_quantity_validation() -> None:
    valid_row = ParsedCsvRow(
        row_number=2,
        raw_data={
            "sale_date": "01-07-2026",
            "product_sku": "MILK-1",
            "quantity": "2.500",
        },
    )
    invalid_row = ParsedCsvRow(
        row_number=3,
        raw_data={
            "sale_date": "not-a-date",
            "product_sku": "MILK-1",
            "quantity": "2.500",
        },
    )

    valid_result = validate_sales_row(valid_row, known_skus={"MILK-1"})
    invalid_result = validate_sales_row(invalid_row, known_skus={"MILK-1"})

    assert isinstance(valid_result, ValidSalesRow)
    assert valid_result.quantity == Decimal("2.500")
    assert isinstance(invalid_result, RejectedSalesRow)
    assert invalid_result.error_code == "invalid_sale_date"


def test_price_validation_and_total_amount_calculation() -> None:
    row = ParsedCsvRow(
        row_number=2,
        raw_data={
            "sale_date": "2026-07-01",
            "product_sku": "MILK-1",
            "quantity": "3.000",
            "unit_price": "12.50",
            "total_amount": "",
        },
    )

    result = validate_sales_row(row, known_skus={"MILK-1"})

    assert isinstance(result, ValidSalesRow)
    assert result.total_amount == Decimal("37.50")


def test_invalid_price_rejection() -> None:
    row = ParsedCsvRow(
        row_number=2,
        raw_data={
            "sale_date": "2026-07-01",
            "product_sku": "MILK-1",
            "quantity": "3.000",
            "unit_price": "-1.00",
        },
    )

    result = validate_sales_row(row, known_skus={"MILK-1"})

    assert isinstance(result, RejectedSalesRow)
    assert result.error_code == "invalid_unit_price"


def test_upload_status_calculation() -> None:
    assert calculate_upload_status(accepted_rows=2, rejected_rows=0) == "completed"
    assert (
        calculate_upload_status(accepted_rows=2, rejected_rows=1)
        == "completed_with_errors"
    )
    assert (
        calculate_upload_status(accepted_rows=0, rejected_rows=1)
        == "completed_with_errors"
    )


def test_safe_filename_handling() -> None:
    assert sanitize_filename("../bad name.csv") == "bad_name.csv"


def test_csv_parser_rejects_invalid_format() -> None:
    with pytest.raises(InvalidSalesCsvFormatError):
        parse_sales_csv(b"")


def test_row_validation_unknown_sku_reason() -> None:
    row = ParsedCsvRow(
        row_number=2,
        raw_data={
            "sale_date": "2026-07-01",
            "product_sku": "UNKNOWN",
            "quantity": "3.000",
        },
    )

    result = validate_sales_row(row, known_skus={"MILK-1"})

    assert isinstance(result, RejectedSalesRow)
    assert result.error_code == "unknown_product_sku"
