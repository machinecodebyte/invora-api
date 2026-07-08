from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ActiveProductInput:
    id: UUID
    sku: str
    name: str


@dataclass(frozen=True, slots=True)
class SalesRecordInput:
    product_id: UUID
    sale_date: date
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class ForecastPredictionOutput:
    product_id: UUID
    forecast_date: date
    predicted_demand: Decimal
    model_name: str


@dataclass(frozen=True, slots=True)
class ForecastMetricsOutput:
    model_name: str
    mae: Decimal | None
    rmse: Decimal | None
    mape: Decimal | None
    training_rows: int
    validation_rows: int
    total_products: int
    fallback_products: int


@dataclass(frozen=True, slots=True)
class ForecastPipelineResult:
    predictions: list[ForecastPredictionOutput]
    metrics: ForecastMetricsOutput


@dataclass(frozen=True, slots=True)
class MLDependencyStatus:
    pandas_available: bool
    numpy_available: bool
    scikit_learn_available: bool

    @property
    def pipeline_ready(self) -> bool:
        return (
            self.pandas_available
            and self.numpy_available
            and self.scikit_learn_available
        )
