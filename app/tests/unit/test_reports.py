from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.reports.application.exporters import serialize_report_rows_to_csv
from app.modules.reports.domain.exceptions import (
    InvalidReportDateRangeError,
    InvalidReportFormatError,
    InvalidReportRecommendationStatusError,
    InvalidReportRiskLevelError,
    InvalidReportStockStatusError,
)
from app.modules.reports.domain.validators import (
    build_safe_report_filename,
    normalize_report_format,
    validate_report_date_range,
    validate_report_recommendation_status,
    validate_report_risk_level,
    validate_report_stock_status,
)


def test_report_format_validation() -> None:
    assert normalize_report_format(None) == "json"
    assert normalize_report_format(" CSV ") == "csv"

    with pytest.raises(InvalidReportFormatError):
        normalize_report_format("pdf")


def test_report_date_range_validation() -> None:
    valid = validate_report_date_range(date(2026, 7, 1), date(2026, 7, 10))
    assert valid.date_from == date(2026, 7, 1)
    assert valid.date_to == date(2026, 7, 10)

    with pytest.raises(InvalidReportDateRangeError):
        validate_report_date_range(date(2026, 7, 10), date(2026, 7, 1))


def test_report_filter_validators() -> None:
    assert validate_report_risk_level("HIGH") == "high"
    assert validate_report_recommendation_status(" acknowledged ") == "acknowledged"
    assert validate_report_stock_status("healthy") == "healthy"

    with pytest.raises(InvalidReportRiskLevelError):
        validate_report_risk_level("urgent")
    with pytest.raises(InvalidReportRecommendationStatusError):
        validate_report_recommendation_status("closed")
    with pytest.raises(InvalidReportStockStatusError):
        validate_report_stock_status("ok")


def test_safe_report_filename_generation() -> None:
    assert build_safe_report_filename(
        "Demand Forecast / Report!",
        date(2026, 7, 10),
    ) == "invora_demand_forecast_report_2026-07-10.csv"


def test_csv_serialization_formats_public_values() -> None:
    product_id = uuid4()
    csv_text = serialize_report_rows_to_csv(
        [
            {
                "product_id": product_id,
                "product_name": "Rice",
                "total": Decimal("12.500"),
                "created_at": datetime(2026, 7, 10, 12, 30),
                "empty": None,
            }
        ],
        fieldnames=("product_id", "product_name", "total", "created_at", "empty"),
    )

    assert "product_id,product_name,total,created_at,empty" in csv_text
    assert str(product_id) in csv_text
    assert "Rice" in csv_text
    assert "12.500" in csv_text
    assert "2026-07-10T12:30:00" in csv_text


def test_csv_serialization_escapes_spreadsheet_formulas() -> None:
    csv_text = serialize_report_rows_to_csv(
        [
            {
                "product_name": '=HYPERLINK("https://example.test")',
                "customer_name": "  +1+1",
                "notes": "Normal text",
            }
        ],
        fieldnames=("product_name", "customer_name", "notes"),
    )

    assert "'=HYPERLINK" in csv_text
    assert "'  +1+1" in csv_text
    assert "Normal text" in csv_text
