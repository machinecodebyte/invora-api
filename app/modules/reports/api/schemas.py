from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ReportFormat = Literal["json", "csv"]
RiskLevel = Literal["critical", "high", "medium", "low", "overstocked"]
RecommendationStatus = Literal["open", "acknowledged", "dismissed"]
StockStatus = Literal["low_stock", "out_of_stock", "healthy", "inactive"]


class ReportDateRangeResponse(BaseModel):
    date_from: date | None
    date_to: date | None


class ForecastReportDateRangeResponse(BaseModel):
    date_from: date | None
    date_to: date | None


class ModelPerformanceMetricRowResponse(BaseModel):
    forecast_run_id: UUID
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    horizon_days: Literal[7, 15, 30]
    requested_at: datetime
    completed_at: datetime | None
    model_name: str
    mae: Decimal | None
    rmse: Decimal | None
    mape: Decimal | None
    training_rows: int
    validation_rows: int
    total_products: int
    fallback_products: int
    created_at: datetime


class ModelPerformanceReportData(BaseModel):
    report_name: str
    generated_at: datetime
    date_range: ReportDateRangeResponse
    total_forecast_runs: int
    completed_forecast_runs: int
    failed_forecast_runs: int
    average_mae: Decimal | None
    average_rmse: Decimal | None
    average_mape: Decimal | None
    best_run_by_mape: ModelPerformanceMetricRowResponse | None
    latest_run_metrics: ModelPerformanceMetricRowResponse | None
    rows: list[ModelPerformanceMetricRowResponse]


class ModelPerformanceReportResponse(BaseModel):
    success: Literal[True] = True
    data: ModelPerformanceReportData


class InventoryRiskReportRowResponse(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    current_stock: Decimal
    minimum_stock: Decimal
    safety_stock: Decimal
    stock_status: StockStatus


class InventoryRiskReportData(BaseModel):
    report_name: str
    generated_at: datetime
    category_id: UUID | None
    stock_status: StockStatus | None
    total_inventory_items: int
    low_stock_count: int
    out_of_stock_count: int
    healthy_stock_count: int
    inactive_inventory_count: int
    rows: list[InventoryRiskReportRowResponse]


class InventoryRiskReportResponse(BaseModel):
    success: Literal[True] = True
    data: InventoryRiskReportData


class ReorderSummaryReportRowResponse(BaseModel):
    id: UUID
    forecast_run_id: UUID
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    predicted_demand: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    safety_stock: Decimal
    required_stock: Decimal
    reorder_quantity: Decimal
    risk_level: RiskLevel
    recommended_action: Literal[
        "reorder_now",
        "monitor",
        "no_reorder_needed",
        "overstock_review",
    ]
    status: RecommendationStatus
    generated_at: datetime


class ReorderSummaryReportData(BaseModel):
    report_name: str
    generated_at: datetime
    forecast_run_id: UUID | None
    risk_level: RiskLevel | None
    status: RecommendationStatus | None
    total_recommendations: int
    open_recommendations: int
    acknowledged_recommendations: int
    dismissed_recommendations: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overstocked_count: int
    total_reorder_quantity: Decimal
    top_reorder_items: list[ReorderSummaryReportRowResponse]
    rows: list[ReorderSummaryReportRowResponse]


class ReorderSummaryReportResponse(BaseModel):
    success: Literal[True] = True
    data: ReorderSummaryReportData


class DemandForecastReportRowResponse(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    forecast_date: date
    predicted_demand: Decimal
    model_name: str


class DemandForecastReportData(BaseModel):
    report_name: str
    generated_at: datetime
    forecast_run_id: UUID
    horizon_days: Literal[7, 15, 30]
    forecast_date_range: ForecastReportDateRangeResponse
    total_products: int
    total_predicted_demand: Decimal
    average_predicted_demand: Decimal
    rows: list[DemandForecastReportRowResponse]


class DemandForecastReportResponse(BaseModel):
    success: Literal[True] = True
    data: DemandForecastReportData


class SalesSummaryReportRowResponse(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    total_quantity_sold: Decimal
    total_sales_amount: Decimal
    transaction_count: int
    average_transaction_amount: Decimal


class SalesSummaryReportData(BaseModel):
    report_name: str
    generated_at: datetime
    date_range: ReportDateRangeResponse
    product_id: UUID | None
    category_id: UUID | None
    channel: str | None
    total_transactions: int
    total_quantity_sold: Decimal
    total_sales_amount: Decimal
    unique_products_sold: int
    average_transaction_amount: Decimal
    rows: list[SalesSummaryReportRowResponse]


class SalesSummaryReportResponse(BaseModel):
    success: Literal[True] = True
    data: SalesSummaryReportData


class ReportsOptionsData(BaseModel):
    available_report_types: tuple[str, ...]
    supported_formats: tuple[ReportFormat, ...]
    supported_risk_levels: tuple[RiskLevel, ...]
    supported_recommendation_statuses: tuple[RecommendationStatus, ...]
    supported_stock_statuses: tuple[StockStatus, ...]
    supported_date_filters: tuple[str, ...]


class ReportsOptionsResponse(BaseModel):
    success: Literal[True] = True
    data: ReportsOptionsData
