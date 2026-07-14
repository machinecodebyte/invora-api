from app.core.exceptions import AppError


class InvalidReportFormatError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report export format is invalid.",
            code="invalid_report_format",
            status_code=400,
        )


class InvalidReportDateRangeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report date range is invalid.",
            code="invalid_report_date_range",
            status_code=400,
        )


class InvalidReportRiskLevelError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report risk level is invalid.",
            code="invalid_report_risk_level",
            status_code=400,
        )


class InvalidReportRecommendationStatusError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report recommendation status is invalid.",
            code="invalid_report_recommendation_status",
            status_code=400,
        )


class InvalidReportStockStatusError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report stock status is invalid.",
            code="invalid_report_stock_status",
            status_code=400,
        )


class ReportProductNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report product was not found.",
            code="report_product_not_found",
            status_code=404,
        )


class ReportCategoryNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report product category was not found.",
            code="report_category_not_found",
            status_code=404,
        )


class ReportForecastRunNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report forecast run was not found.",
            code="report_forecast_run_not_found",
            status_code=404,
        )


class ReportGenerationFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report generation failed.",
            code="report_generation_failed",
            status_code=500,
        )


class ReportCsvExportFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Report CSV export failed.",
            code="report_csv_export_failed",
            status_code=500,
        )
