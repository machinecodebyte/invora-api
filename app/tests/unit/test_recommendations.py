from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.modules.recommendations.domain.exceptions import (
    InvalidRecommendationActionError,
    InvalidRecommendationDateRangeError,
    InvalidRecommendationRiskLevelError,
    InvalidRecommendationSortError,
    InvalidRecommendationStatusError,
    InvalidRecommendationStatusTransitionError,
    RecommendationForecastRunNotCompletedError,
    RecommendationsAlreadyGeneratedError,
)
from app.modules.recommendations.domain.reorder_policy import (
    calculate_reorder_quantity,
    calculate_required_stock,
    calculate_stock_gap,
    quantize_stock,
)
from app.modules.recommendations.domain.risk_engine import (
    calculate_risk_level,
    recommended_action_for_risk,
)
from app.modules.recommendations.domain.validators import (
    ensure_status_transition,
    normalize_recommendation_sort_field,
    normalize_recommendation_sort_order,
    validate_action,
    validate_completed_forecast_run,
    validate_recommendation_date_range,
    validate_regeneration_policy,
    validate_risk_level,
    validate_status,
)


@dataclass(slots=True)
class RunStub:
    status: str


def test_reorder_formula_uses_forecast_plus_safety_minus_current_stock() -> None:
    predicted_demand = Decimal("15.1234")
    safety_stock = Decimal("3.1111")
    current_stock = Decimal("10.0000")

    required_stock = calculate_required_stock(
        predicted_demand=predicted_demand,
        safety_stock=safety_stock,
    )
    stock_gap = calculate_stock_gap(
        required_stock=required_stock,
        current_stock=current_stock,
    )
    reorder_quantity = calculate_reorder_quantity(stock_gap=stock_gap)

    assert required_stock == Decimal("18.234")
    assert stock_gap == Decimal("8.234")
    assert reorder_quantity == Decimal("8.234")
    assert quantize_stock(Decimal("1.2344")) == Decimal("1.234")


def test_reorder_quantity_never_goes_below_zero() -> None:
    stock_gap = calculate_stock_gap(
        required_stock=Decimal("5.000"),
        current_stock=Decimal("12.000"),
    )

    assert stock_gap == Decimal("-7.000")
    assert calculate_reorder_quantity(stock_gap=stock_gap) == Decimal("0.000")


@pytest.mark.parametrize(
    ("predicted_demand", "current_stock", "required_stock", "reorder_quantity", "risk"),
    [
        (
            Decimal("5.000"),
            Decimal("0.000"),
            Decimal("5.000"),
            Decimal("5.000"),
            "critical",
        ),
        (
            Decimal("10.000"),
            Decimal("3.000"),
            Decimal("12.000"),
            Decimal("9.000"),
            "high",
        ),
        (
            Decimal("10.000"),
            Decimal("11.000"),
            Decimal("12.000"),
            Decimal("1.000"),
            "medium",
        ),
        (
            Decimal("10.000"),
            Decimal("12.000"),
            Decimal("12.000"),
            Decimal("0.000"),
            "low",
        ),
        (
            Decimal("10.000"),
            Decimal("24.000"),
            Decimal("12.000"),
            Decimal("0.000"),
            "overstocked",
        ),
    ],
)
def test_risk_engine_is_deterministic(
    predicted_demand: Decimal,
    current_stock: Decimal,
    required_stock: Decimal,
    reorder_quantity: Decimal,
    risk: str,
) -> None:
    assert (
        calculate_risk_level(
            predicted_demand=predicted_demand,
            current_stock=current_stock,
            required_stock=required_stock,
            reorder_quantity=reorder_quantity,
        )
        == risk
    )


@pytest.mark.parametrize(
    ("risk", "action"),
    [
        ("critical", "reorder_now"),
        ("high", "reorder_now"),
        ("medium", "monitor"),
        ("low", "no_reorder_needed"),
        ("overstocked", "overstock_review"),
    ],
)
def test_recommended_action_follows_risk_level(risk: str, action: str) -> None:
    assert recommended_action_for_risk(risk) == action


def test_recommendations_require_completed_forecast_run() -> None:
    validate_completed_forecast_run(RunStub(status="completed"))

    with pytest.raises(RecommendationForecastRunNotCompletedError):
        validate_completed_forecast_run(RunStub(status="pending"))


def test_regeneration_policy_requires_refresh_when_rows_exist() -> None:
    validate_regeneration_policy(existing_count=1, refresh=True)
    validate_regeneration_policy(existing_count=0, refresh=False)

    with pytest.raises(RecommendationsAlreadyGeneratedError):
        validate_regeneration_policy(existing_count=1, refresh=False)


def test_recommendation_filter_validation() -> None:
    assert validate_risk_level(" HIGH ") == "high"
    assert validate_status(" ACKNOWLEDGED ") == "acknowledged"
    assert validate_action(" reorder_now ") == "reorder_now"

    with pytest.raises(InvalidRecommendationRiskLevelError):
        validate_risk_level("urgent")
    with pytest.raises(InvalidRecommendationStatusError):
        validate_status("closed")
    with pytest.raises(InvalidRecommendationActionError):
        validate_action("buy_now")


def test_status_transition_validation() -> None:
    assert ensure_status_transition("open", "acknowledged") == "acknowledged"
    assert ensure_status_transition("acknowledged", "dismissed") == "dismissed"
    assert ensure_status_transition("dismissed", "dismissed") == "dismissed"

    with pytest.raises(InvalidRecommendationStatusTransitionError):
        ensure_status_transition("dismissed", "open")


def test_sort_and_date_range_validation() -> None:
    assert normalize_recommendation_sort_field(" SKU ") == "sku"
    assert normalize_recommendation_sort_order("ASC") == "asc"
    validate_recommendation_date_range(
        datetime(2026, 7, 1, tzinfo=UTC),
        datetime(2026, 7, 2, tzinfo=UTC),
    )

    with pytest.raises(InvalidRecommendationSortError):
        normalize_recommendation_sort_field("created_at")
    with pytest.raises(InvalidRecommendationSortError):
        normalize_recommendation_sort_order("sideways")
    with pytest.raises(InvalidRecommendationDateRangeError):
        validate_recommendation_date_range(
            datetime(2026, 7, 2, tzinfo=UTC),
            datetime(2026, 7, 1, tzinfo=UTC),
        )
