from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.forecasting.domain.exceptions import (
    ForecastPredictionPersistenceError,
    ForecastResultMetricsNotFoundError,
    ForecastResultProductNotFoundError,
    ForecastRunNotFoundError,
    InvalidMLForecastRunStatusError,
    MLDependencyUnavailableError,
    MLForecastPipelineError,
)
from app.modules.forecasting.domain.results import (
    ensure_product_has_forecast_results,
    ensure_result_sort_field,
    ensure_results_available,
    normalize_result_interval,
    normalize_result_sort_order,
    validate_result_date_range,
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


class ForecastResultService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def get_result_overview(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> dict[str, Any]:
        run, prediction_count = await self._get_ready_run(
            user_id=user_id,
            run_id=run_id,
        )
        forecast_start_date, forecast_end_date = (
            await self.repository.get_prediction_date_range(
                user_id=user_id,
                forecast_run_id=run.id,
            )
        )
        total_predicted_demand = await self.repository.get_total_predicted_demand(
            user_id=user_id,
            forecast_run_id=run.id,
        )
        metrics = await self.repository.get_metrics_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
        )
        return {
            "run_id": run.id,
            "status": run.status,
            "horizon_days": run.horizon_days,
            "requested_at": run.requested_at,
            "completed_at": run.completed_at,
            "model_name": self._model_name(run=run, metrics=metrics),
            "total_products": run.total_products,
            "total_predictions": prediction_count,
            "forecast_start_date": forecast_start_date,
            "forecast_end_date": forecast_end_date,
            "total_predicted_demand": total_predicted_demand,
            "average_predicted_demand": self._average_decimal(
                total_predicted_demand,
                prediction_count,
            ),
            "metrics": self._metrics_to_dict(metrics),
        }

    async def list_predictions(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        validate_result_date_range(date_from, date_to)
        sort_by = ensure_result_sort_field(sort_by)
        sort_order = normalize_result_sort_order(sort_order)
        run, _ = await self._get_ready_run(user_id=user_id, run_id=run_id)
        if product_id is not None:
            await self._ensure_product_owned(user_id=user_id, product_id=product_id)
        predictions, total = await self.repository.list_predictions_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
            product_id=product_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {
            "predictions": predictions,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_metrics(self, *, user_id: UUID, run_id: UUID) -> dict[str, Any]:
        run, _ = await self._get_ready_run(user_id=user_id, run_id=run_id)
        metrics = await self.repository.get_metrics_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
        )
        if metrics is None:
            raise ForecastResultMetricsNotFoundError()
        return {"metrics": self._metrics_to_dict(metrics)}

    async def get_chart_data(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
        product_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        interval: str,
    ) -> dict[str, Any]:
        validate_result_date_range(date_from, date_to)
        interval = normalize_result_interval(interval)
        run, _ = await self._get_ready_run(user_id=user_id, run_id=run_id)
        if product_id is not None:
            await self._ensure_product_owned(user_id=user_id, product_id=product_id)
        forecast_start_date, forecast_end_date = (
            await self.repository.get_prediction_date_range(
                user_id=user_id,
                forecast_run_id=run.id,
            )
        )
        prediction_points = await self.repository.get_chart_predictions_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
            product_id=product_id,
            date_from=date_from,
            date_to=date_to,
            interval=interval,
        )
        actual_by_period: dict[date, Decimal] = {}
        if prediction_points and forecast_start_date is not None:
            actual_rows = await self.repository.get_actual_sales_for_forecast_dates(
                user_id=user_id,
                product_id=product_id,
                date_from=date_from or forecast_start_date,
                date_to=date_to or forecast_end_date,
                interval=interval,
            )
            actual_by_period = {
                row["period_start"]: row["actual_quantity"] for row in actual_rows
            }
        return {
            "metadata": {
                "run_id": run.id,
                "horizon_days": run.horizon_days,
                "interval": interval,
            },
            "points": [
                {
                    "period_start": row["period_start"],
                    "predicted_demand": row["predicted_demand"],
                    "actual_quantity": actual_by_period.get(row["period_start"]),
                }
                for row in prediction_points
            ],
        }

    async def get_product_forecast_detail(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
        product_id: UUID,
    ) -> dict[str, Any]:
        run, _ = await self._get_ready_run(user_id=user_id, run_id=run_id)
        await self._ensure_product_owned(user_id=user_id, product_id=product_id)
        rows = await self.repository.get_product_forecast_detail(
            user_id=user_id,
            forecast_run_id=run.id,
            product_id=product_id,
        )
        ensure_product_has_forecast_results(len(rows))
        forecast_dates = [row["forecast_date"] for row in rows]
        actual_rows = await self.repository.get_actual_sales_for_forecast_dates(
            user_id=user_id,
            product_id=product_id,
            date_from=min(forecast_dates),
            date_to=max(forecast_dates),
            interval="day",
        )
        actual_by_date = {
            row["period_start"]: row["actual_quantity"] for row in actual_rows
        }
        total_predicted = sum(
            (row["predicted_demand"] for row in rows),
            Decimal("0.000"),
        )
        first = rows[0]
        return {
            "run_id": run.id,
            "horizon_days": run.horizon_days,
            "product_id": product_id,
            "product_name": first["product_name"],
            "sku": first["sku"],
            "category_id": first["category_id"],
            "category_name": first["category_name"],
            "unit": first["unit"],
            "current_stock": first["current_stock"],
            "minimum_stock": first["minimum_stock"],
            "safety_stock": first["safety_stock"],
            "total_predicted_demand": total_predicted,
            "points": [
                {
                    "forecast_date": row["forecast_date"],
                    "predicted_demand": row["predicted_demand"],
                    "actual_quantity": actual_by_date.get(row["forecast_date"]),
                    "model_name": row["model_name"],
                }
                for row in rows
            ],
        }

    async def _get_ready_run(self, *, user_id: UUID, run_id: UUID) -> tuple[Any, int]:
        run = await self.repository.get_forecast_run_for_user(
            user_id=user_id,
            run_id=run_id,
        )
        if run is None:
            raise ForecastRunNotFoundError()
        prediction_count = await self.repository.count_predictions_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
        )
        ensure_results_available(run=run, prediction_count=prediction_count)
        return run, prediction_count

    async def _ensure_product_owned(self, *, user_id: UUID, product_id: UUID) -> None:
        product = await self.repository.get_product_for_user(
            user_id=user_id,
            product_id=product_id,
        )
        if product is None:
            raise ForecastResultProductNotFoundError()

    def _metrics_to_dict(self, metrics: Any | None) -> dict[str, Any] | None:
        if metrics is None:
            return None
        return {
            "model_name": metrics.model_name,
            "mae": metrics.mae,
            "rmse": metrics.rmse,
            "mape": metrics.mape,
            "training_rows": metrics.training_rows,
            "validation_rows": metrics.validation_rows,
            "total_products": metrics.total_products,
            "fallback_products": metrics.fallback_products,
            "created_at": metrics.created_at,
        }

    def _model_name(self, *, run: Any, metrics: Any | None) -> str | None:
        if metrics is not None:
            return metrics.model_name
        metadata = run.run_metadata or {}
        value = metadata.get("model_name") if isinstance(metadata, dict) else None
        return str(value) if value else None

    def _average_decimal(self, total: Decimal, count: int) -> Decimal:
        if count <= 0:
            return Decimal("0.000")
        return (total / Decimal(count)).quantize(Decimal("0.001"))
