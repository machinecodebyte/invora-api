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


class MLDependencyUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Required ML dependencies are unavailable.",
            code="ml_dependency_unavailable",
            status_code=503,
        )


class InvalidMLForecastRunStatusError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run cannot be processed in its current status.",
            code="invalid_ml_forecast_run_status",
            status_code=409,
        )


class MLForecastPipelineError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast processing failed.",
            code="ml_forecast_pipeline_failed",
            status_code=500,
        )


class ForecastPredictionPersistenceError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast predictions could not be persisted.",
            code="forecast_prediction_persistence_failed",
            status_code=500,
        )


class ForecastResultNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast result was not found.",
            code="forecast_result_not_found",
            status_code=404,
        )


class ForecastResultsNotReadyError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast results are not ready for this run.",
            code="forecast_results_not_ready",
            status_code=409,
        )


class ForecastResultProductNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast result product was not found.",
            code="forecast_result_product_not_found",
            status_code=404,
        )


class ForecastResultMetricsNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast result metrics were not found.",
            code="forecast_result_metrics_not_found",
            status_code=404,
        )


class InvalidForecastResultDateRangeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast result date range is invalid.",
            code="invalid_forecast_result_date_range",
            status_code=400,
        )


class InvalidForecastResultIntervalError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast result chart interval is invalid.",
            code="invalid_forecast_result_interval",
            status_code=400,
        )


class InvalidForecastResultSortError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast result sort value is invalid.",
            code="invalid_forecast_result_sort",
            status_code=400,
        )
