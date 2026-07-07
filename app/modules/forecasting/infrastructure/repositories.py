from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forecasting.infrastructure.models import ForecastRunModel
from app.modules.products.infrastructure.models import ProductModel
from app.modules.sales.infrastructure.models import SalesTransactionModel
from app.shared.utils import utc_now

FORECAST_RUN_SORT_COLUMNS = {
    "requested_at": ForecastRunModel.requested_at,
    "created_at": ForecastRunModel.created_at,
    "updated_at": ForecastRunModel.updated_at,
}


class ForecastRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_forecast_run(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> ForecastRunModel:
        run = ForecastRunModel(user_id=user_id, **values)
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_forecast_run_for_user(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> ForecastRunModel | None:
        result = await self.session.execute(
            select(ForecastRunModel).where(
                ForecastRunModel.id == run_id,
                ForecastRunModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_forecast_runs_for_user(
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
    ) -> tuple[list[ForecastRunModel], int]:
        filters = [ForecastRunModel.user_id == user_id]
        if status is not None:
            filters.append(ForecastRunModel.status == status)
        if horizon_days is not None:
            filters.append(ForecastRunModel.horizon_days == horizon_days)
        if date_from is not None:
            filters.append(ForecastRunModel.requested_at >= date_from)
        if date_to is not None:
            filters.append(ForecastRunModel.requested_at <= date_to)

        total_result = await self.session.execute(
            select(func.count()).select_from(ForecastRunModel).where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = FORECAST_RUN_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(ForecastRunModel)
            .where(*filters)
            .order_by(sort_expression, desc(ForecastRunModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update_forecast_run_status(
        self,
        run: ForecastRunModel,
        values: dict[str, Any],
    ) -> ForecastRunModel:
        for field, value in values.items():
            setattr(run, field, value)
        run.updated_at = utc_now()
        await self.session.flush()
        return run

    async def count_user_active_products(self, *, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ProductModel)
            .where(
                ProductModel.user_id == user_id,
                ProductModel.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def count_user_sales_transactions(self, *, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(SalesTransactionModel)
            .where(
                SalesTransactionModel.user_id == user_id,
                SalesTransactionModel.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def get_user_sales_date_span(
        self,
        *,
        user_id: UUID,
    ) -> tuple[date | None, date | None]:
        result = await self.session.execute(
            select(
                func.min(SalesTransactionModel.sale_date),
                func.max(SalesTransactionModel.sale_date),
            ).where(
                SalesTransactionModel.user_id == user_id,
                SalesTransactionModel.deleted_at.is_(None),
            )
        )
        sales_date_from, sales_date_to = result.one()
        return sales_date_from, sales_date_to

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
