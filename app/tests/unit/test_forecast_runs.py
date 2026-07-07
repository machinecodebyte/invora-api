from datetime import UTC, datetime

import pytest

from app.modules.forecasting.domain.exceptions import (
    ForecastRunAlreadyCancelledError,
    ForecastRunAlreadyCompletedError,
    InsufficientForecastSalesDataError,
    InvalidForecastDateRangeError,
    InvalidForecastHorizonError,
    InvalidForecastSortError,
    NoActiveForecastProductsError,
)
from app.modules.forecasting.domain.runs import (
    ensure_cancellable_status,
    ensure_sort_field,
    normalize_sort_order,
    validate_date_range,
    validate_horizon,
    validate_minimum_data,
)


def test_forecast_horizon_validation() -> None:
    assert validate_horizon(7) == 7
    assert validate_horizon(15) == 15
    assert validate_horizon(30) == 30

    with pytest.raises(InvalidForecastHorizonError):
        validate_horizon(14)


def test_forecast_cancel_rule_validation() -> None:
    ensure_cancellable_status("pending")
    ensure_cancellable_status("running")

    with pytest.raises(ForecastRunAlreadyCompletedError):
        ensure_cancellable_status("completed")
    with pytest.raises(ForecastRunAlreadyCancelledError):
        ensure_cancellable_status("cancelled")


def test_forecast_date_range_validation() -> None:
    validate_date_range(
        datetime(2026, 7, 1, tzinfo=UTC),
        datetime(2026, 7, 2, tzinfo=UTC),
    )

    with pytest.raises(InvalidForecastDateRangeError):
        validate_date_range(
            datetime(2026, 7, 2, tzinfo=UTC),
            datetime(2026, 7, 1, tzinfo=UTC),
        )


def test_forecast_sort_validation() -> None:
    assert ensure_sort_field("requested_at") == "requested_at"
    assert normalize_sort_order("asc") == "asc"

    with pytest.raises(InvalidForecastSortError):
        ensure_sort_field("status")
    with pytest.raises(InvalidForecastSortError):
        normalize_sort_order("sideways")


def test_forecast_minimum_data_requires_active_products() -> None:
    with pytest.raises(NoActiveForecastProductsError):
        validate_minimum_data(active_product_count=0, sales_transaction_count=1)


def test_forecast_minimum_data_requires_sales_transactions() -> None:
    with pytest.raises(InsufficientForecastSalesDataError):
        validate_minimum_data(active_product_count=1, sales_transaction_count=0)


def test_forecast_minimum_data_accepts_practical_capstone_seed() -> None:
    validate_minimum_data(active_product_count=1, sales_transaction_count=1)
