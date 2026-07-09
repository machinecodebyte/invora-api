from __future__ import annotations

from datetime import date
from typing import Any

from app.modules.forecasting.domain.exceptions import (
    ForecastResultNotFoundError,
    ForecastResultsNotReadyError,
    InvalidForecastResultDateRangeError,
    InvalidForecastResultIntervalError,
    InvalidForecastResultSortError,
)

FORECAST_RESULT_SORT_FIELDS = (
    "forecast_date",
    "predicted_demand",
    "product_name",
    "sku",
    "model_name",
)
FORECAST_RESULT_INTERVALS = ("day", "week", "month")


def validate_result_date_range(
    date_from: date | None,
    date_to: date | None,
) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidForecastResultDateRangeError()


def normalize_result_interval(interval: str) -> str:
    normalized = interval.strip().lower()
    if normalized not in FORECAST_RESULT_INTERVALS:
        raise InvalidForecastResultIntervalError()
    return normalized


def ensure_result_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in FORECAST_RESULT_SORT_FIELDS:
        raise InvalidForecastResultSortError()
    return normalized


def normalize_result_sort_order(sort_order: str) -> str:
    normalized = sort_order.strip().lower()
    if normalized not in {"asc", "desc"}:
        raise InvalidForecastResultSortError()
    return normalized


def ensure_results_available(*, run: Any, prediction_count: int) -> None:
    if getattr(run, "status", None) != "completed" or prediction_count <= 0:
        raise ForecastResultsNotReadyError()


def ensure_product_has_forecast_results(row_count: int) -> None:
    if row_count <= 0:
        raise ForecastResultNotFoundError()
