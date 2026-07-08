from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.forecasting.domain.exceptions import (
    ForecastPredictionPersistenceError,
    ForecastRunNotFoundError,
    InvalidMLForecastRunStatusError,
    MLDependencyUnavailableError,
    MLForecastPipelineError,
)
from app.modules.forecasting.domain.runs import (
    ALLOWED_FORECAST_HORIZONS,
    FORECAST_RUN_STATUSES,
    ensure_cancellable_status,
    ensure_sort_field,
    normalize_sort_order,
    sales_span_metadata,
    validate_date_range,
    validate_horizon,
    validate_minimum_data,
    validate_status_filter,
)
from app.modules.forecasting.ml.dependencies import check_ml_dependencies
from app.shared.utils import utc_now


class ForecastRunService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def create_run(
        self,
        *,
        user_id: UUID,
        horizon_days: int,
    ) -> Any:
        horizon_days = validate_horizon(horizon_days)
        active_product_count = await self.repository.count_user_active_products(
            user_id=user_id,
        )
        sales_transaction_count = await self.repository.count_user_sales_transactions(
            user_id=user_id,
        )
        validate_minimum_data(
            active_product_count=active_product_count,
            sales_transaction_count=sales_transaction_count,
        )
        sales_date_from, sales_date_to = await self.repository.get_user_sales_date_span(
            user_id=user_id,
        )
        now = utc_now()
        try:
            run = await self.repository.create_forecast_run(
                user_id=user_id,
                values={
                    "horizon_days": horizon_days,
                    "status": "pending",
                    "requested_at": now,
                    "started_at": None,
                    "completed_at": None,
                    "failed_at": None,
                    "cancelled_at": None,
                    "failure_reason": None,
                    "total_products": active_product_count,
                    "total_sales_records": sales_transaction_count,
                    "run_metadata": sales_span_metadata(
                        sales_date_from=sales_date_from,
                        sales_date_to=sales_date_to,
                    ),
                },
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        return run

    async def list_runs(
        self,
        *,
        user_id: UUID,
        status: str | None,
        horizon_days: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Any], int]:
        validate_date_range(date_from, date_to)
        if horizon_days is not None:
            horizon_days = validate_horizon(horizon_days)
        return await self.repository.list_forecast_runs_for_user(
            user_id=user_id,
            status=validate_status_filter(status),
            horizon_days=horizon_days,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            sort_by=ensure_sort_field(sort_by),
            sort_order=normalize_sort_order(sort_order),
        )

    async def get_run(self, *, user_id: UUID, run_id: UUID) -> Any:
        run = await self.repository.get_forecast_run_for_user(
            user_id=user_id,
            run_id=run_id,
        )
        if run is None:
            raise ForecastRunNotFoundError()
        return run

    async def cancel_run(self, *, user_id: UUID, run_id: UUID) -> Any:
        run = await self.get_run(user_id=user_id, run_id=run_id)
        ensure_cancellable_status(run.status)
        try:
            run = await self.repository.update_forecast_run_status(
                run,
                {
                    "status": "cancelled",
                    "cancelled_at": utc_now(),
                    "failure_reason": None,
                },
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        return run

    async def get_options(self) -> dict[str, tuple[int, ...] | tuple[str, ...]]:
        return {
            "horizons": ALLOWED_FORECAST_HORIZONS,
            "statuses": FORECAST_RUN_STATUSES,
        }


class MLForecastingService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def process_forecast_run(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> dict[str, Any]:
        run = await self.repository.get_forecast_run_for_user(
            user_id=user_id,
            run_id=run_id,
        )
        if run is None:
            raise ForecastRunNotFoundError()
        if run.status not in {"pending", "failed"}:
            raise InvalidMLForecastRunStatusError()
        if not check_ml_dependencies().pipeline_ready:
            await self._mark_failed(run, "Required ML dependencies are unavailable.")
            raise MLDependencyUnavailableError()

        try:
            run = await self.repository.update_forecast_run_status(
                run,
                {
                    "status": "running",
                    "started_at": utc_now(),
                    "completed_at": None,
                    "failed_at": None,
                    "failure_reason": None,
                },
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        products = await self.repository.get_active_products_for_user(user_id=user_id)
        sales = await self.repository.get_sales_transactions_for_forecasting(
            user_id=user_id,
        )
        try:
            validate_minimum_data(
                active_product_count=len(products),
                sales_transaction_count=len(sales),
            )
            from app.modules.forecasting.ml.pipeline import run_forecasting_pipeline

            pipeline_result = run_forecasting_pipeline(
                products=products,
                sales_transactions=sales,
                horizon_days=run.horizon_days,
            )
        except AppError as exc:
            await self._mark_failed(run, exc.message)
            raise
        except Exception as exc:
            await self._mark_failed(run, "Forecast processing failed.")
            raise MLForecastPipelineError() from exc

        try:
            await self.repository.delete_predictions_for_run(
                user_id=user_id,
                forecast_run_id=run.id,
            )
            await self.repository.bulk_create_forecast_predictions(
                user_id=user_id,
                forecast_run_id=run.id,
                rows=[
                    {
                        "product_id": prediction.product_id,
                        "forecast_date": prediction.forecast_date,
                        "predicted_demand": prediction.predicted_demand,
                        "model_name": prediction.model_name,
                    }
                    for prediction in pipeline_result.predictions
                ],
            )
            await self.repository.create_forecast_metrics(
                user_id=user_id,
                forecast_run_id=run.id,
                values={
                    "model_name": pipeline_result.metrics.model_name,
                    "mae": pipeline_result.metrics.mae,
                    "rmse": pipeline_result.metrics.rmse,
                    "mape": pipeline_result.metrics.mape,
                    "training_rows": pipeline_result.metrics.training_rows,
                    "validation_rows": pipeline_result.metrics.validation_rows,
                    "total_products": pipeline_result.metrics.total_products,
                    "fallback_products": pipeline_result.metrics.fallback_products,
                },
            )
            run = await self.repository.update_forecast_run_status(
                run,
                {
                    "status": "completed",
                    "completed_at": utc_now(),
                    "failed_at": None,
                    "failure_reason": None,
                    "total_products": len(products),
                    "total_sales_records": len(sales),
                    "run_metadata": {
                        "model_name": pipeline_result.metrics.model_name,
                        "predictions_created": len(pipeline_result.predictions),
                        "fallback_products": pipeline_result.metrics.fallback_products,
                    },
                },
            )
            await self.repository.commit()
        except Exception as exc:
            await self.repository.rollback()
            await self._mark_failed(run, "Forecast predictions could not be persisted.")
            raise ForecastPredictionPersistenceError() from exc

        return {
            "run_id": run.id,
            "status": run.status,
            "horizon_days": run.horizon_days,
            "total_products": len(products),
            "total_sales_records": len(sales),
            "predictions_created": len(pipeline_result.predictions),
            "metrics": {
                "model_name": pipeline_result.metrics.model_name,
                "mae": pipeline_result.metrics.mae,
                "rmse": pipeline_result.metrics.rmse,
                "mape": pipeline_result.metrics.mape,
                "training_rows": pipeline_result.metrics.training_rows,
                "validation_rows": pipeline_result.metrics.validation_rows,
                "fallback_products": pipeline_result.metrics.fallback_products,
            },
        }

    async def get_forecasting_options(self) -> dict[str, Any]:
        return {
            "supported_horizons": ALLOWED_FORECAST_HORIZONS,
            "default_model": "random_forest_regressor_v1",
            "fallback_strategy": "recent_average_baseline_v1",
            "required_minimum_data_notes": (
                "At least one active product and one non-deleted sales transaction "
                "are required. Products with short history use the baseline fallback."
            ),
        }

    async def get_ml_health(self) -> dict[str, bool]:
        status = check_ml_dependencies()
        return {
            "pandas_available": status.pandas_available,
            "numpy_available": status.numpy_available,
            "scikit_learn_available": status.scikit_learn_available,
            "pipeline_ready": status.pipeline_ready,
        }

    async def _mark_failed(self, run: Any, failure_reason: str) -> None:
        try:
            await self.repository.update_forecast_run_status(
                run,
                {
                    "status": "failed",
                    "failed_at": utc_now(),
                    "failure_reason": failure_reason[:1000],
                },
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
