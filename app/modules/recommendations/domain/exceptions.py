from app.core.exceptions import AppError


class RecommendationForecastRunNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run was not found.",
            code="recommendation_forecast_run_not_found",
            status_code=404,
        )


class RecommendationForecastRunNotCompletedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run must be completed before recommendations can be generated.",
            code="recommendation_forecast_run_not_completed",
            status_code=409,
        )


class RecommendationForecastPredictionsNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast predictions were not found for this run.",
            code="recommendation_forecast_predictions_not_found",
            status_code=409,
        )


class RecommendationsAlreadyGeneratedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendations already exist for this forecast run.",
            code="recommendations_already_generated",
            status_code=409,
        )


class RecommendationsNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendations were not found.",
            code="recommendations_not_found",
            status_code=404,
        )


class RecommendationsNotGeneratedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendations have not been generated for this forecast run.",
            code="recommendations_not_generated",
            status_code=409,
        )


class RecommendationNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation was not found.",
            code="recommendation_not_found",
            status_code=404,
        )


class RecommendationInventoryMissingError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Inventory data is missing for one or more forecasted products.",
            code="recommendation_inventory_missing",
            status_code=409,
        )


class RecommendationProductNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation product was not found.",
            code="recommendation_product_not_found",
            status_code=404,
        )


class InvalidRecommendationRiskLevelError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation risk level is invalid.",
            code="invalid_recommendation_risk_level",
            status_code=400,
        )


class InvalidRecommendationStatusError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation status is invalid.",
            code="invalid_recommendation_status",
            status_code=400,
        )


class InvalidRecommendationActionError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation action is invalid.",
            code="invalid_recommendation_action",
            status_code=400,
        )


class InvalidRecommendationStatusTransitionError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation status transition is invalid.",
            code="invalid_recommendation_status_transition",
            status_code=409,
        )


class InvalidRecommendationDateRangeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation date range is invalid.",
            code="invalid_recommendation_date_range",
            status_code=400,
        )


class InvalidRecommendationSortError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Recommendation sort value is invalid.",
            code="invalid_recommendation_sort",
            status_code=400,
        )
