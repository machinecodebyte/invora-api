from __future__ import annotations

from datetime import datetime
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
