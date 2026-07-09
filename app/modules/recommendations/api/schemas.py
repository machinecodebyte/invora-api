from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

RecommendationRiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
    "overstocked",
]
RecommendationStatus = Literal["open", "acknowledged", "dismissed"]
RecommendationAction = Literal[
    "reorder_now",
    "monitor",
    "no_reorder_needed",
    "overstock_review",
]


class GenerateRecommendationsRequest(BaseModel):
    refresh: bool = False


class RecommendationStatusUpdateRequest(BaseModel):
    status: RecommendationStatus


class RecommendationForecastRunPublic(BaseModel):
    id: UUID
    horizon_days: Literal[7, 15, 30]
    status: str
    requested_at: datetime
    completed_at: datetime | None


class ReorderRecommendationPublic(BaseModel):
    id: UUID
    forecast_run_id: UUID
    product_id: UUID
    product_name: str
    sku: str
    category_id: UUID | None
    category_name: str | None
    unit: str
    predicted_demand: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    safety_stock: Decimal
    required_stock: Decimal
    reorder_quantity: Decimal
    stock_gap: Decimal
    risk_level: RecommendationRiskLevel
    recommended_action: RecommendationAction
    reason: str | None
    status: RecommendationStatus
    generated_at: datetime
    acknowledged_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    forecast_run: RecommendationForecastRunPublic


class GenerateRecommendationsData(BaseModel):
    forecast_run_id: UUID
    total_products: int
    recommendations_created: int
    refreshed: bool
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overstocked_count: int


class GenerateRecommendationsResponse(BaseModel):
    success: Literal[True] = True
    data: GenerateRecommendationsData


class ReorderRecommendationData(BaseModel):
    recommendation: ReorderRecommendationPublic


class ReorderRecommendationResponse(BaseModel):
    success: Literal[True] = True
    data: ReorderRecommendationData


class ReorderRecommendationListData(BaseModel):
    recommendations: list[ReorderRecommendationPublic]
    total: int
    limit: int
    offset: int


class RunRecommendationListData(ReorderRecommendationListData):
    forecast_run_id: UUID


class ReorderRecommendationListResponse(BaseModel):
    success: Literal[True] = True
    data: ReorderRecommendationListData


class RunRecommendationListResponse(BaseModel):
    success: Literal[True] = True
    data: RunRecommendationListData


class RecommendationSummaryData(BaseModel):
    forecast_run_id: UUID
    total_recommendations: int
    total_reorder_quantity: Decimal
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overstocked_count: int
    total_predicted_demand: Decimal
    total_current_stock: Decimal
    latest_generated_at: datetime
    top_reorder_products: list[ReorderRecommendationPublic]


class RecommendationSummaryResponse(BaseModel):
    success: Literal[True] = True
    data: RecommendationSummaryData


class RecommendationStatusUpdateResponse(BaseModel):
    success: Literal[True] = True
    data: ReorderRecommendationData
