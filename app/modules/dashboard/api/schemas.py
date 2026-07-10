from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class DashboardKpiData(BaseModel):
    total_products: int
    active_products: int
    total_sales_records: int
    total_inventory_items: int
    low_stock_count: int
    out_of_stock_count: int
    total_forecast_runs: int
    completed_forecast_runs: int
    latest_forecast_mape: Decimal | None
    open_recommendations: int
    high_risk_recommendations: int
    critical_risk_recommendations: int
    total_reorder_quantity: Decimal


class DashboardKpiResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardKpiData


class DashboardDemandTrendPointResponse(BaseModel):
    period: date
    total_quantity_sold: Decimal
    total_sales_amount: Decimal
    transaction_count: int


class DashboardDemandTrendData(BaseModel):
    date_from: date
    date_to: date
    interval: Literal["day", "week", "month"]
    product_id: UUID | None
    category_id: UUID | None
    points: list[DashboardDemandTrendPointResponse]


class DashboardDemandTrendResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardDemandTrendData


class DashboardInventoryRiskItemResponse(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    current_stock: Decimal
    minimum_stock: Decimal
    safety_stock: Decimal
    stock_status: Literal["in_stock", "low_stock", "out_of_stock", "inactive"]


class DashboardInventoryRiskData(BaseModel):
    total_inventory_items: int
    low_stock_count: int
    out_of_stock_count: int
    healthy_stock_count: int
    inactive_inventory_count: int
    low_stock_items: list[DashboardInventoryRiskItemResponse]
    out_of_stock_items: list[DashboardInventoryRiskItemResponse]


class DashboardInventoryRiskResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardInventoryRiskData


class DashboardForecastRunPublic(BaseModel):
    id: UUID
    horizon_days: Literal[7, 15, 30]
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    failure_reason: str | None
    total_products: int
    total_sales_records: int


class DashboardForecastMetricsPublic(BaseModel):
    model_name: str
    mae: Decimal | None
    rmse: Decimal | None
    mape: Decimal | None
    training_rows: int
    validation_rows: int
    total_products: int
    fallback_products: int
    created_at: datetime


class DashboardForecastDateRange(BaseModel):
    date_from: date | None
    date_to: date | None


class DashboardForecastOverviewData(BaseModel):
    latest_forecast_run: DashboardForecastRunPublic | None
    latest_completed_forecast_run: DashboardForecastRunPublic | None
    forecast_run_counts_by_status: dict[str, int]
    latest_metrics: DashboardForecastMetricsPublic | None
    total_predictions_in_latest_run: int
    forecast_date_range: DashboardForecastDateRange
    total_predicted_demand: Decimal


class DashboardForecastOverviewResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardForecastOverviewData


class DashboardReorderAlertItemResponse(BaseModel):
    id: UUID
    forecast_run_id: UUID
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    predicted_demand: Decimal
    current_stock: Decimal
    required_stock: Decimal
    reorder_quantity: Decimal
    risk_level: Literal["low", "medium", "high", "critical", "overstocked"]
    recommended_action: Literal[
        "reorder_now",
        "monitor",
        "no_reorder_needed",
        "overstock_review",
    ]
    status: Literal["open", "acknowledged", "dismissed"]
    generated_at: datetime


class DashboardReorderAlertsData(BaseModel):
    forecast_run_id: UUID | None
    risk_level: str | None
    status: str | None
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overstocked_count: int
    open_count: int
    acknowledged_count: int
    dismissed_count: int
    total_reorder_quantity: Decimal
    top_reorder_items: list[DashboardReorderAlertItemResponse]


class DashboardReorderAlertsResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardReorderAlertsData


class DashboardRecentActivityItemResponse(BaseModel):
    event_type: Literal[
        "sales_upload",
        "forecast_run",
        "stock_movement",
        "reorder_recommendation",
    ]
    event_label: str
    entity_id: UUID
    occurred_at: datetime
    metadata: dict[str, Any]


class DashboardRecentActivityData(BaseModel):
    activities: list[DashboardRecentActivityItemResponse]
    limit: int


class DashboardRecentActivityResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardRecentActivityData


class DashboardSummaryData(BaseModel):
    date_from: date
    date_to: date
    forecast_run_id: UUID | None
    kpis: DashboardKpiData
    demand_trends: DashboardDemandTrendData
    inventory_risk: DashboardInventoryRiskData
    forecast_overview: DashboardForecastOverviewData
    reorder_alerts: DashboardReorderAlertsData
    recent_activity: DashboardRecentActivityData


class DashboardSummaryResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardSummaryData
