from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ForecastRunCreateRequest(BaseModel):
    horizon_days: int


class ForecastRunPublic(BaseModel):
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
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="run_metadata",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForecastRunData(BaseModel):
    run: ForecastRunPublic


class ForecastRunListData(BaseModel):
    runs: list[ForecastRunPublic]
    total: int
    limit: int
    offset: int


class ForecastRunResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastRunData


class ForecastRunListResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastRunListData


class ForecastRunCancelResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastRunData


class ForecastRunOptionsData(BaseModel):
    horizons: tuple[Literal[7, 15, 30], ...]
    statuses: tuple[
        Literal["pending", "running", "completed", "failed", "cancelled"],
        ...,
    ]


class ForecastRunOptionsResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastRunOptionsData


class MLForecastingMetricsSummary(BaseModel):
    model_name: str
    mae: Decimal | None
    rmse: Decimal | None
    mape: Decimal | None
    training_rows: int
    validation_rows: int
    fallback_products: int


class MLForecastingProcessData(BaseModel):
    run_id: UUID
    status: Literal["completed", "failed", "running", "pending", "cancelled"]
    horizon_days: Literal[7, 15, 30]
    total_products: int
    total_sales_records: int
    predictions_created: int
    metrics: MLForecastingMetricsSummary


class MLForecastingProcessResponse(BaseModel):
    success: Literal[True] = True
    data: MLForecastingProcessData


class MLForecastingOptionsData(BaseModel):
    supported_horizons: tuple[Literal[7, 15, 30], ...]
    default_model: str
    fallback_strategy: str
    required_minimum_data_notes: str


class MLForecastingOptionsResponse(BaseModel):
    success: Literal[True] = True
    data: MLForecastingOptionsData


class MLForecastingHealthData(BaseModel):
    pandas_available: bool
    numpy_available: bool
    scikit_learn_available: bool
    pipeline_ready: bool


class MLForecastingHealthResponse(BaseModel):
    success: Literal[True] = True
    data: MLForecastingHealthData


class ForecastResultMetricsPublic(BaseModel):
    model_name: str
    mae: Decimal | None
    rmse: Decimal | None
    mape: Decimal | None
    training_rows: int
    validation_rows: int
    total_products: int
    fallback_products: int
    created_at: datetime


class ForecastResultOverviewData(BaseModel):
    run_id: UUID
    status: Literal["completed"]
    horizon_days: Literal[7, 15, 30]
    requested_at: datetime
    completed_at: datetime | None
    model_name: str | None
    total_products: int
    total_predictions: int
    forecast_start_date: date | None
    forecast_end_date: date | None
    total_predicted_demand: Decimal
    average_predicted_demand: Decimal
    metrics: ForecastResultMetricsPublic | None


class ForecastResultOverviewResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastResultOverviewData


class ForecastPredictionPublic(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    unit: str
    current_stock: Decimal | None
    minimum_stock: Decimal | None
    safety_stock: Decimal | None
    forecast_date: date
    predicted_demand: Decimal
    model_name: str


class ForecastPredictionResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastPredictionPublic


class ForecastPredictionListData(BaseModel):
    predictions: list[ForecastPredictionPublic]
    total: int
    limit: int
    offset: int


class ForecastPredictionListResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastPredictionListData


class ForecastMetricsData(BaseModel):
    metrics: ForecastResultMetricsPublic


class ForecastMetricsResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastMetricsData


class ForecastChartPointResponse(BaseModel):
    period_start: date
    predicted_demand: Decimal
    actual_quantity: Decimal | None


class ForecastChartMetadata(BaseModel):
    run_id: UUID
    horizon_days: Literal[7, 15, 30]
    interval: Literal["day", "week", "month"]


class ForecastChartData(BaseModel):
    metadata: ForecastChartMetadata
    points: list[ForecastChartPointResponse]


class ForecastChartResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastChartData


class ProductForecastPointResponse(BaseModel):
    forecast_date: date
    predicted_demand: Decimal
    actual_quantity: Decimal | None
    model_name: str


class ProductForecastDetailData(BaseModel):
    run_id: UUID
    horizon_days: Literal[7, 15, 30]
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    unit: str
    current_stock: Decimal | None
    minimum_stock: Decimal | None
    safety_stock: Decimal | None
    total_predicted_demand: Decimal
    points: list[ProductForecastPointResponse]


class ProductForecastDetailResponse(BaseModel):
    success: Literal[True] = True
    data: ProductForecastDetailData
