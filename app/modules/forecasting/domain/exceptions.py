from app.core.exceptions import AppError


class InvalidForecastHorizonError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast horizon is invalid.",
            code="invalid_forecast_horizon",
            status_code=400,
        )


class InsufficientForecastSalesDataError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "At least one sales transaction is required before creating a "
            "forecast run.",
            code="insufficient_forecast_sales_data",
            status_code=409,
        )


class NoActiveForecastProductsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "At least one active product is required before creating a forecast run.",
            code="no_active_forecast_products",
            status_code=409,
        )


class ForecastRunNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run was not found.",
            code="forecast_run_not_found",
            status_code=404,
        )


class InvalidForecastStatusTransitionError(AppError):
    def __init__(
        self,
        message: str = "Forecast run status transition is invalid.",
    ) -> None:
        super().__init__(
            message,
            code="invalid_forecast_status_transition",
            status_code=409,
        )


class InvalidForecastStatusError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run status is invalid.",
            code="invalid_forecast_status",
            status_code=400,
        )


class ForecastRunAlreadyCompletedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Completed forecast runs cannot be cancelled.",
            code="forecast_run_already_completed",
            status_code=409,
        )


class ForecastRunAlreadyCancelledError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run is already cancelled.",
            code="forecast_run_already_cancelled",
            status_code=409,
        )


class InvalidForecastDateRangeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run date range is invalid.",
            code="invalid_forecast_date_range",
            status_code=400,
        )


class InvalidForecastSortError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run sort value is invalid.",
            code="invalid_forecast_sort",
            status_code=400,
        )
