from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app.modules.reports.domain.exceptions import (
    InvalidReportDateRangeError,
    InvalidReportFormatError,
    InvalidReportRecommendationStatusError,
    InvalidReportRiskLevelError,
    InvalidReportStockStatusError,
)
from app.shared.utils import utc_now

REPORT_FORMATS = ("json", "csv")
REPORT_TYPES = (
    "model_performance",
    "inventory_risk",
    "reorder_summary",
    "demand_forecast",
    "sales_summary",
)
REPORT_RISK_LEVELS = ("critical", "high", "medium", "low", "overstocked")
REPORT_RECOMMENDATION_STATUSES = ("open", "acknowledged", "dismissed")
REPORT_STOCK_STATUSES = ("low_stock", "out_of_stock", "healthy", "inactive")
REPORT_DATE_FILTERS = (
    "date_from",
    "date_to",
    "forecast_run_id",
    "product_id",
    "category_id",
)
DEFAULT_REPORT_DAYS = 30


@dataclass(frozen=True, slots=True)
class ReportDateRange:
    date_from: date | None
    date_to: date | None


def normalize_report_format(value: str | None) -> str:
    normalized = (value or "json").strip().lower()
    if normalized not in REPORT_FORMATS:
        raise InvalidReportFormatError()
    return normalized


def validate_report_date_range(
    date_from: date | None,
    date_to: date | None,
) -> ReportDateRange:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidReportDateRangeError()
    return ReportDateRange(date_from=date_from, date_to=date_to)


def resolve_default_report_date_range(
    date_from: date | None,
    date_to: date | None,
    *,
    default_days: int = DEFAULT_REPORT_DAYS,
) -> ReportDateRange:
    resolved_to = date_to or utc_now().date()
    resolved_from = date_from or resolved_to - timedelta(days=default_days - 1)
    if resolved_from > resolved_to:
        raise InvalidReportDateRangeError()
    return ReportDateRange(date_from=resolved_from, date_to=resolved_to)


def validate_report_risk_level(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in REPORT_RISK_LEVELS:
        raise InvalidReportRiskLevelError()
    return normalized


def validate_report_recommendation_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in REPORT_RECOMMENDATION_STATUSES:
        raise InvalidReportRecommendationStatusError()
    return normalized


def validate_report_stock_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in REPORT_STOCK_STATUSES:
        raise InvalidReportStockStatusError()
    return normalized


def build_safe_report_filename(report_name: str, generated_date: date) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", report_name.strip().lower())
    safe_name = normalized.strip("_") or "report"
    return f"invora_{safe_name}_{generated_date.isoformat()}.csv"


def report_options() -> dict[str, tuple[str, ...]]:
    return {
        "available_report_types": REPORT_TYPES,
        "supported_formats": REPORT_FORMATS,
        "supported_risk_levels": REPORT_RISK_LEVELS,
        "supported_recommendation_statuses": REPORT_RECOMMENDATION_STATUSES,
        "supported_stock_statuses": REPORT_STOCK_STATUSES,
        "supported_date_filters": REPORT_DATE_FILTERS,
    }
