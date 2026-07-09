from __future__ import annotations

from datetime import datetime
from typing import Any

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

RECOMMENDATION_RISK_LEVELS = ("low", "medium", "high", "critical", "overstocked")
RECOMMENDATION_STATUSES = ("open", "acknowledged", "dismissed")
RECOMMENDATION_ACTIONS = (
    "reorder_now",
    "monitor",
    "no_reorder_needed",
    "overstock_review",
)
RECOMMENDATION_SORT_FIELDS = (
    "generated_at",
    "risk_level",
    "reorder_quantity",
    "predicted_demand",
    "current_stock",
    "product_name",
    "sku",
    "status",
)


def validate_completed_forecast_run(run: Any) -> None:
    if getattr(run, "status", None) != "completed":
        raise RecommendationForecastRunNotCompletedError()


def validate_regeneration_policy(
    *,
    existing_count: int,
    refresh: bool,
) -> None:
    if existing_count > 0 and not refresh:
        raise RecommendationsAlreadyGeneratedError()


def validate_recommendation_date_range(
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidRecommendationDateRangeError()


def normalize_recommendation_sort_field(sort_by: str) -> str:
    normalized = sort_by.strip().lower()
    if normalized not in RECOMMENDATION_SORT_FIELDS:
        raise InvalidRecommendationSortError()
    return normalized


def normalize_recommendation_sort_order(sort_order: str) -> str:
    normalized = sort_order.strip().lower()
    if normalized not in {"asc", "desc"}:
        raise InvalidRecommendationSortError()
    return normalized


def validate_risk_level(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in RECOMMENDATION_RISK_LEVELS:
        raise InvalidRecommendationRiskLevelError()
    return normalized


def validate_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in RECOMMENDATION_STATUSES:
        raise InvalidRecommendationStatusError()
    return normalized


def validate_action(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in RECOMMENDATION_ACTIONS:
        raise InvalidRecommendationActionError()
    return normalized


def ensure_status_transition(current_status: str, next_status: str) -> str:
    current = validate_status(current_status)
    target = validate_status(next_status)
    if current == target:
        return target
    allowed = {
        "open": {"acknowledged", "dismissed"},
        "acknowledged": {"dismissed"},
        "dismissed": set(),
    }
    if target not in allowed[current]:
        raise InvalidRecommendationStatusTransitionError()
    return target
