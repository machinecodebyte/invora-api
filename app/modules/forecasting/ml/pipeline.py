from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pandas as pd

from app.modules.forecasting.domain.exceptions import MLDependencyUnavailableError
from app.modules.forecasting.ml.dependencies import check_ml_dependencies
from app.modules.forecasting.ml.dto import (
    ForecastMetricsOutput,
    ForecastPipelineResult,
    ForecastPredictionOutput,
)
from app.modules.forecasting.ml.evaluation import calculate_metrics
from app.modules.forecasting.ml.features import (
    FEATURE_COLUMNS,
    build_feature_frame,
    future_feature_row,
    product_code_map,
)
from app.modules.forecasting.ml.preprocessing import (
    active_products_from_objects,
    aggregate_daily_sales,
    sales_records_from_objects,
)
from app.modules.forecasting.ml.training import (
    COMBINED_MODEL_NAME,
    FALLBACK_MODEL_NAME,
    MODEL_NAME,
    train_with_validation,
)

DEMAND_QUANTUM = Decimal("0.001")
MIN_PRODUCT_HISTORY_DAYS = 7
MIN_PRODUCT_POSITIVE_DAYS = 2


def run_forecasting_pipeline(
    *,
    products: list[object],
    sales_transactions: list[object],
    horizon_days: int,
) -> ForecastPipelineResult:
    if not check_ml_dependencies().pipeline_ready:
        raise MLDependencyUnavailableError()

    active_products = active_products_from_objects(products)
    sales_records = sales_records_from_objects(sales_transactions)
    daily_sales = aggregate_daily_sales(
        products=active_products,
        sales_records=sales_records,
    )
    product_ids = [str(product.id) for product in active_products]
    codes = product_code_map(product_ids)
    feature_frame = build_feature_frame(daily_sales, product_codes=codes)
    model, train_frame, validation_frame = train_with_validation(feature_frame)
    metrics = _metrics_from_validation(
        validation_frame=validation_frame,
        training_rows=len(train_frame),
        total_products=len(active_products),
        fallback_products=0,
    )

    fallback_product_ids = _fallback_product_ids(daily_sales)
    predictions: list[ForecastPredictionOutput] = []
    last_date = pd.to_datetime(daily_sales["sale_date"]).max().date()
    histories = {
        product_id: _history_for_product(daily_sales, product_id)
        for product_id in product_ids
    }

    for day_offset in range(1, horizon_days + 1):
        forecast_date = last_date + timedelta(days=day_offset)
        for product in active_products:
            product_id = str(product.id)
            use_fallback = model is None or product_id in fallback_product_ids
            if use_fallback:
                predicted = _fallback_prediction(histories[product_id])
                model_name = FALLBACK_MODEL_NAME
            else:
                row = future_feature_row(
                    product_id=product_id,
                    forecast_date=forecast_date,
                    product_code=codes[product_id],
                    history=histories[product_id],
                )
                future_frame = pd.DataFrame([row])
                predicted = float(model.predict(future_frame[list(FEATURE_COLUMNS)])[0])
                model_name = MODEL_NAME
            predicted = max(0.0, predicted)
            histories[product_id].append(predicted)
            predictions.append(
                ForecastPredictionOutput(
                    product_id=UUID(product_id),
                    forecast_date=forecast_date,
                    predicted_demand=_to_demand_decimal(predicted),
                    model_name=model_name,
                )
            )

    metrics = ForecastMetricsOutput(
        model_name=COMBINED_MODEL_NAME,
        mae=metrics.mae,
        rmse=metrics.rmse,
        mape=metrics.mape,
        training_rows=metrics.training_rows,
        validation_rows=metrics.validation_rows,
        total_products=len(active_products),
        fallback_products=len(fallback_product_ids)
        if model is not None
        else len(active_products),
    )
    return ForecastPipelineResult(predictions=predictions, metrics=metrics)


def _metrics_from_validation(
    *,
    validation_frame: pd.DataFrame,
    training_rows: int,
    total_products: int,
    fallback_products: int,
) -> ForecastMetricsOutput:
    if validation_frame.empty or "predicted" not in validation_frame:
        calculated = {"mae": None, "rmse": None, "mape": None}
        validation_rows = 0
    else:
        clipped = validation_frame["predicted"].clip(lower=0)
        calculated = calculate_metrics(validation_frame["quantity"], clipped)
        validation_rows = len(validation_frame)
    return ForecastMetricsOutput(
        model_name=COMBINED_MODEL_NAME,
        mae=calculated["mae"],
        rmse=calculated["rmse"],
        mape=calculated["mape"],
        training_rows=training_rows,
        validation_rows=validation_rows,
        total_products=total_products,
        fallback_products=fallback_products,
    )


def _fallback_product_ids(daily_sales: pd.DataFrame) -> set[str]:
    fallback_ids: set[str] = set()
    for product_id, product_frame in daily_sales.groupby("product_id"):
        positive_days = int((product_frame["quantity"] > 0).sum())
        if (
            len(product_frame) < MIN_PRODUCT_HISTORY_DAYS
            or positive_days < MIN_PRODUCT_POSITIVE_DAYS
        ):
            fallback_ids.add(str(product_id))
    return fallback_ids


def _history_for_product(daily_sales: pd.DataFrame, product_id: str) -> list[float]:
    product_frame = daily_sales[daily_sales["product_id"] == product_id]
    return [float(value) for value in product_frame["quantity"].tolist()]


def _fallback_prediction(history: list[float]) -> float:
    positive_history = [value for value in history if value > 0]
    if history:
        recent_values = history[-7:]
        recent_mean = sum(recent_values) / len(recent_values)
        if recent_mean > 0:
            return recent_mean
    if positive_history:
        return sum(positive_history) / len(positive_history)
    return 0.0


def _to_demand_decimal(value: float) -> Decimal:
    return Decimal(str(round(max(0.0, value), 3))).quantize(DEMAND_QUANTUM)
