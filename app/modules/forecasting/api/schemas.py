from __future__ import annotations

from datetime import datetime
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
