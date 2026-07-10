from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.modules.dashboard.domain.exceptions import (
    InvalidDashboardDateRangeError,
    InvalidDashboardIntervalError,
    InvalidDashboardLimitError,
    InvalidDashboardRecommendationStatusError,
    InvalidDashboardRiskLevelError,
)
from app.shared.utils import utc_now

DASHBOARD_INTERVALS = ("day", "week", "month")
DASHBOARD_RISK_LEVELS = ("low", "medium", "high", "critical", "overstocked")
DASHBOARD_RECOMMENDATION_STATUSES = ("open", "acknowledged", "dismissed")
DEFAULT_DASHBOARD_DAYS = 30
MAX_DASHBOARD_LIMIT = 100


@dataclass(frozen=True, slots=True)
class DashboardDateRange:
    date_from: date
    date_to: date


def resolve_dashboard_date_range(
    date_from: date | None,
    date_to: date | None,
) -> DashboardDateRange:
    resolved_to = date_to or utc_now().date()
    resolved_from = date_from or resolved_to - timedelta(
        days=DEFAULT_DASHBOARD_DAYS - 1,
    )
    if resolved_from > resolved_to:
        raise InvalidDashboardDateRangeError()
    return DashboardDateRange(date_from=resolved_from, date_to=resolved_to)


def validate_dashboard_date_range(
    date_from: date | None,
    date_to: date | None,
) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidDashboardDateRangeError()


def normalize_dashboard_interval(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in DASHBOARD_INTERVALS:
        raise InvalidDashboardIntervalError()
    return normalized


def validate_dashboard_limit(
    value: int,
    *,
    max_limit: int = MAX_DASHBOARD_LIMIT,
) -> int:
    if value < 1 or value > max_limit:
        raise InvalidDashboardLimitError()
    return value


def validate_dashboard_risk_level(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in DASHBOARD_RISK_LEVELS:
        raise InvalidDashboardRiskLevelError()
    return normalized


def validate_dashboard_recommendation_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in DASHBOARD_RECOMMENDATION_STATUSES:
        raise InvalidDashboardRecommendationStatusError()
    return normalized
