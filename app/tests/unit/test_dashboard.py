from datetime import date

import pytest

from app.modules.dashboard.domain.exceptions import (
    InvalidDashboardDateRangeError,
    InvalidDashboardIntervalError,
    InvalidDashboardLimitError,
    InvalidDashboardRecommendationStatusError,
    InvalidDashboardRiskLevelError,
)
from app.modules.dashboard.domain.validators import (
    normalize_dashboard_interval,
    resolve_dashboard_date_range,
    validate_dashboard_limit,
    validate_dashboard_recommendation_status,
    validate_dashboard_risk_level,
)


def test_dashboard_date_range_defaults_to_thirty_days() -> None:
    date_range = resolve_dashboard_date_range(None, date(2026, 7, 10))

    assert date_range.date_from == date(2026, 6, 11)
    assert date_range.date_to == date(2026, 7, 10)


def test_dashboard_date_range_rejects_reversed_dates() -> None:
    with pytest.raises(InvalidDashboardDateRangeError):
        resolve_dashboard_date_range(date(2026, 7, 11), date(2026, 7, 10))


def test_dashboard_interval_validation() -> None:
    assert normalize_dashboard_interval(" WEEK ") == "week"

    with pytest.raises(InvalidDashboardIntervalError):
        normalize_dashboard_interval("quarter")


def test_dashboard_limit_validation() -> None:
    assert validate_dashboard_limit(10, max_limit=50) == 10

    with pytest.raises(InvalidDashboardLimitError):
        validate_dashboard_limit(0)
    with pytest.raises(InvalidDashboardLimitError):
        validate_dashboard_limit(51, max_limit=50)


def test_dashboard_reorder_filter_validation() -> None:
    assert validate_dashboard_risk_level(" HIGH ") == "high"
    assert validate_dashboard_recommendation_status(" OPEN ") == "open"

    with pytest.raises(InvalidDashboardRiskLevelError):
        validate_dashboard_risk_level("urgent")
    with pytest.raises(InvalidDashboardRecommendationStatusError):
        validate_dashboard_recommendation_status("closed")
