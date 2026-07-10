from app.core.exceptions import AppError


class InvalidDashboardDateRangeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard date range is invalid.",
            code="invalid_dashboard_date_range",
            status_code=400,
        )


class InvalidDashboardIntervalError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard interval is invalid.",
            code="invalid_dashboard_interval",
            status_code=400,
        )


class InvalidDashboardLimitError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard limit is invalid.",
            code="invalid_dashboard_limit",
            status_code=400,
        )


class InvalidDashboardRiskLevelError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard recommendation risk level is invalid.",
            code="invalid_dashboard_risk_level",
            status_code=400,
        )


class InvalidDashboardRecommendationStatusError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard recommendation status is invalid.",
            code="invalid_dashboard_recommendation_status",
            status_code=400,
        )


class DashboardProductNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard product was not found.",
            code="dashboard_product_not_found",
            status_code=404,
        )


class DashboardCategoryNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard product category was not found.",
            code="dashboard_category_not_found",
            status_code=404,
        )


class DashboardForecastRunNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard forecast run was not found.",
            code="dashboard_forecast_run_not_found",
            status_code=404,
        )


class DashboardAggregationFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Dashboard analytics aggregation failed.",
            code="dashboard_aggregation_failed",
            status_code=500,
        )
