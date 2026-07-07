from __future__ import annotations

from datetime import date, datetime

from app.modules.forecasting.domain.exceptions import (
    ForecastRunAlreadyCancelledError,
    ForecastRunAlreadyCompletedError,
    InsufficientForecastSalesDataError,
    InvalidForecastDateRangeError,
    InvalidForecastHorizonError,
    InvalidForecastSortError,
    InvalidForecastStatusError,
    InvalidForecastStatusTransitionError,
    NoActiveForecastProductsError,
)

ALLOWED_FORECAST_HORIZONS = (7, 15, 30)
FORECAST_RUN_STATUSES = ("pending", "running", "completed", "failed", "cancelled")
CANCELLABLE_FORECAST_STATUSES = ("pending", "running")
FORECAST_RUN_SORT_FIELDS = ("requested_at", "created_at", "updated_at")


def validate_horizon(value: int) -> int:
    if value not in ALLOWED_FORECAST_HORIZONS:
        raise InvalidForecastHorizonError()
    return value


def validate_status_filter(status: str | None) -> str | None:
    if status is None:
        return None
    normalized = status.strip().lower()
    if normalized not in FORECAST_RUN_STATUSES:
        raise InvalidForecastStatusError()
    return normalized


def ensure_cancellable_status(status: str) -> None:
    normalized = status.strip().lower()
    if normalized in CANCELLABLE_FORECAST_STATUSES:
        return
    if normalized == "completed":
        raise ForecastRunAlreadyCompletedError()
    if normalized == "cancelled":
        raise ForecastRunAlreadyCancelledError()
    raise InvalidForecastStatusTransitionError(
        "Only pending or running forecast runs can be cancelled.",
    )


def validate_date_range(
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidForecastDateRangeError()


def normalize_sort_order(sort_order: str) -> str:
    normalized = sort_order.strip().lower()
    if normalized not in {"asc", "desc"}:
        raise InvalidForecastSortError()
    return normalized


def ensure_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in FORECAST_RUN_SORT_FIELDS:
        raise InvalidForecastSortError()
    return normalized


def validate_minimum_data(
    *,
    active_product_count: int,
    sales_transaction_count: int,
) -> None:
    if active_product_count <= 0:
        raise NoActiveForecastProductsError()
    if sales_transaction_count <= 0:
        raise InsufficientForecastSalesDataError()


def sales_span_metadata(
    *,
    sales_date_from: date | None,
    sales_date_to: date | None,
) -> dict[str, str | None]:
    return {
        "sales_date_from": sales_date_from.isoformat() if sales_date_from else None,
        "sales_date_to": sales_date_to.isoformat() if sales_date_to else None,
    }
