from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.modules.auth.api.dependencies import get_current_user
from app.modules.reports.api.dependencies import get_reports_service
from app.modules.reports.api.schemas import (
    DemandForecastReportData,
    DemandForecastReportResponse,
    InventoryRiskReportData,
    InventoryRiskReportResponse,
    ModelPerformanceReportData,
    ModelPerformanceReportResponse,
    ReorderSummaryReportData,
    ReorderSummaryReportResponse,
    ReportsOptionsData,
    ReportsOptionsResponse,
    SalesSummaryReportData,
    SalesSummaryReportResponse,
)
from app.modules.reports.application.exporters import generate_csv_response
from app.modules.reports.application.service import ReportsService
from app.modules.reports.domain.validators import normalize_report_format

router = APIRouter(prefix="/reports", tags=["Reports"])

MODEL_PERFORMANCE_FIELDS = (
    "forecast_run_id",
    "status",
    "horizon_days",
    "requested_at",
    "completed_at",
    "model_name",
    "mae",
    "rmse",
    "mape",
    "training_rows",
    "validation_rows",
    "total_products",
    "fallback_products",
    "created_at",
)
INVENTORY_RISK_FIELDS = (
    "product_id",
    "product_name",
    "sku",
    "category_id",
    "category_name",
    "current_stock",
    "minimum_stock",
    "safety_stock",
    "stock_status",
)
REORDER_SUMMARY_FIELDS = (
    "id",
    "forecast_run_id",
    "product_id",
    "product_name",
    "sku",
    "category_id",
    "category_name",
    "predicted_demand",
    "current_stock",
    "minimum_stock",
    "safety_stock",
    "required_stock",
    "reorder_quantity",
    "risk_level",
    "recommended_action",
    "status",
    "generated_at",
)
DEMAND_FORECAST_FIELDS = (
    "product_id",
    "product_name",
    "sku",
    "category_id",
    "category_name",
    "forecast_date",
    "predicted_demand",
    "model_name",
)
SALES_SUMMARY_FIELDS = (
    "product_id",
    "product_name",
    "sku",
    "category_id",
    "category_name",
    "total_quantity_sold",
    "total_sales_amount",
    "transaction_count",
    "average_transaction_amount",
)


@router.get(
    "/model-performance",
    response_model=ModelPerformanceReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get model performance report",
    description=(
        "Requires a Bearer access token and returns a report-ready model "
        "performance summary from forecast runs and model metrics. Use "
        "`format=csv` to export the rows as text/csv."
    ),
)
async def get_model_performance_report(
    current_user: Annotated[object, Depends(get_current_user)],
    reports_service: Annotated[ReportsService, Depends(get_reports_service)],
    forecast_run_id: UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    report_format: str = Query(default="json", alias="format"),
) -> ModelPerformanceReportResponse | Response:
    export_format = normalize_report_format(report_format)
    report = await reports_service.get_model_performance_report(
        user_id=current_user.id,
        forecast_run_id=forecast_run_id,
        date_from=date_from,
        date_to=date_to,
    )
    if export_format == "csv":
        return _csv_response(report, fieldnames=MODEL_PERFORMANCE_FIELDS)
    return ModelPerformanceReportResponse(data=ModelPerformanceReportData(**report))


@router.get(
    "/inventory-risk",
    response_model=InventoryRiskReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get inventory risk report",
    description=(
        "Requires a Bearer access token and returns a report-ready inventory "
        "risk summary for the current user's inventory. Use `format=csv` to "
        "export the rows as text/csv."
    ),
)
async def get_inventory_risk_report(
    current_user: Annotated[object, Depends(get_current_user)],
    reports_service: Annotated[ReportsService, Depends(get_reports_service)],
    category_id: UUID | None = Query(default=None),
    stock_status: str | None = Query(default=None),
    report_format: str = Query(default="json", alias="format"),
) -> InventoryRiskReportResponse | Response:
    export_format = normalize_report_format(report_format)
    report = await reports_service.get_inventory_risk_report(
        user_id=current_user.id,
        category_id=category_id,
        stock_status=stock_status,
    )
    if export_format == "csv":
        return _csv_response(report, fieldnames=INVENTORY_RISK_FIELDS)
    return InventoryRiskReportResponse(data=InventoryRiskReportData(**report))


@router.get(
    "/reorder-summary",
    response_model=ReorderSummaryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reorder summary report",
    description=(
        "Requires a Bearer access token and returns a report-ready reorder "
        "recommendation summary. This endpoint reads existing recommendations "
        "only. Use `format=csv` to export the rows as text/csv."
    ),
)
async def get_reorder_summary_report(
    current_user: Annotated[object, Depends(get_current_user)],
    reports_service: Annotated[ReportsService, Depends(get_reports_service)],
    forecast_run_id: UUID | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    recommendation_status: str | None = Query(default=None, alias="status"),
    report_format: str = Query(default="json", alias="format"),
) -> ReorderSummaryReportResponse | Response:
    export_format = normalize_report_format(report_format)
    report = await reports_service.get_reorder_summary_report(
        user_id=current_user.id,
        forecast_run_id=forecast_run_id,
        risk_level=risk_level,
        status=recommendation_status,
    )
    if export_format == "csv":
        return _csv_response(report, fieldnames=REORDER_SUMMARY_FIELDS)
    return ReorderSummaryReportResponse(data=ReorderSummaryReportData(**report))


@router.get(
    "/demand-forecast",
    response_model=DemandForecastReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get demand forecast report",
    description=(
        "Requires a Bearer access token and returns report-ready forecast "
        "prediction rows for one owned forecast run. `forecast_run_id` is "
        "required to avoid ambiguous report output. Use `format=csv` to export "
        "the rows as text/csv."
    ),
)
async def get_demand_forecast_report(
    current_user: Annotated[object, Depends(get_current_user)],
    reports_service: Annotated[ReportsService, Depends(get_reports_service)],
    forecast_run_id: UUID = Query(...),
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    report_format: str = Query(default="json", alias="format"),
) -> DemandForecastReportResponse | Response:
    export_format = normalize_report_format(report_format)
    report = await reports_service.get_demand_forecast_report(
        user_id=current_user.id,
        forecast_run_id=forecast_run_id,
        product_id=product_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
    )
    if export_format == "csv":
        return _csv_response(report, fieldnames=DEMAND_FORECAST_FIELDS)
    return DemandForecastReportResponse(data=DemandForecastReportData(**report))


@router.get(
    "/sales-summary",
    response_model=SalesSummaryReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sales summary report",
    description=(
        "Requires a Bearer access token and returns a report-ready sales "
        "summary from non-deleted Sales Transactions. If no date range is "
        "provided, the last 30 days are used. Use `format=csv` to export rows "
        "as text/csv."
    ),
)
async def get_sales_summary_report(
    current_user: Annotated[object, Depends(get_current_user)],
    reports_service: Annotated[ReportsService, Depends(get_reports_service)],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    channel: str | None = Query(default=None, max_length=64),
    report_format: str = Query(default="json", alias="format"),
) -> SalesSummaryReportResponse | Response:
    export_format = normalize_report_format(report_format)
    report = await reports_service.get_sales_summary_report(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
        category_id=category_id,
        channel=channel,
    )
    if export_format == "csv":
        return _csv_response(report, fieldnames=SALES_SUMMARY_FIELDS)
    return SalesSummaryReportResponse(data=SalesSummaryReportData(**report))


@router.get(
    "/options",
    response_model=ReportsOptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reports options",
    description=(
        "Requires a Bearer access token and returns report metadata for UI "
        "controls. This endpoint does not return or create settings."
    ),
)
async def get_reports_options(
    _: Annotated[object, Depends(get_current_user)],
    reports_service: Annotated[ReportsService, Depends(get_reports_service)],
) -> ReportsOptionsResponse:
    options = await reports_service.get_report_options()
    return ReportsOptionsResponse(data=ReportsOptionsData(**options))


def _csv_response(report: dict, *, fieldnames: tuple[str, ...]) -> Response:
    return generate_csv_response(
        report_name=report["report_name"],
        generated_at=report["generated_at"],
        rows=report["rows"],
        fieldnames=fieldnames,
    )
