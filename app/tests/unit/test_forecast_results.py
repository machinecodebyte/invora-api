from dataclasses import dataclass
from datetime import date

import pytest

from app.modules.forecasting.domain.exceptions import (
    ForecastResultNotFoundError,
    ForecastResultsNotReadyError,
    InvalidForecastResultDateRangeError,
    InvalidForecastResultIntervalError,
    InvalidForecastResultSortError,
)
from app.modules.forecasting.domain.results import (
    ensure_product_has_forecast_results,
    ensure_result_sort_field,
    ensure_results_available,
    normalize_result_interval,
    normalize_result_sort_order,
    validate_result_date_range,
)


@dataclass(slots=True)
class RunStub:
    status: str


def test_result_availability_requires_completed_run_with_predictions() -> None:
    ensure_results_available(run=RunStub(status="completed"), prediction_count=1)

    with pytest.raises(ForecastResultsNotReadyError):
        ensure_results_available(run=RunStub(status="pending"), prediction_count=1)
    with pytest.raises(ForecastResultsNotReadyError):
        ensure_results_available(run=RunStub(status="completed"), prediction_count=0)


def test_forecast_result_date_range_validation() -> None:
    validate_result_date_range(date(2026, 7, 1), date(2026, 7, 2))

    with pytest.raises(InvalidForecastResultDateRangeError):
        validate_result_date_range(date(2026, 7, 2), date(2026, 7, 1))


def test_forecast_result_interval_validation() -> None:
    assert normalize_result_interval(" WEEK ") == "week"

    with pytest.raises(InvalidForecastResultIntervalError):
        normalize_result_interval("quarter")


def test_forecast_result_sort_validation() -> None:
    assert ensure_result_sort_field("sku") == "sku"
    assert normalize_result_sort_order("DESC") == "desc"

    with pytest.raises(InvalidForecastResultSortError):
        ensure_result_sort_field("created_at")
    with pytest.raises(InvalidForecastResultSortError):
        normalize_result_sort_order("sideways")


def test_product_forecast_detail_requires_rows() -> None:
    ensure_product_has_forecast_results(1)

    with pytest.raises(ForecastResultNotFoundError):
        ensure_product_has_forecast_results(0)
