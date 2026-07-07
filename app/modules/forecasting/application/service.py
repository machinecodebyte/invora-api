from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.forecasting.domain.exceptions import ForecastRunNotFoundError
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
