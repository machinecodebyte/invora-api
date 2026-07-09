from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Date as SqlDate
from sqlalchemy import and_, asc, cast, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.forecasting.infrastructure.models import (
    ForecastModelMetricModel,
    ForecastPredictionModel,
    ForecastRunModel,
)
from app.modules.inventory.infrastructure.models import InventoryItemModel
from app.modules.products.infrastructure.models import (
    ProductCategoryModel,
    ProductModel,
)
from app.modules.sales.infrastructure.models import SalesTransactionModel
from app.shared.utils import utc_now

FORECAST_RUN_SORT_COLUMNS = {
    "requested_at": ForecastRunModel.requested_at,
    "created_at": ForecastRunModel.created_at,
    "updated_at": ForecastRunModel.updated_at,
}

FORECAST_RESULT_SORT_COLUMNS = {
    "forecast_date": ForecastPredictionModel.forecast_date,
    "predicted_demand": ForecastPredictionModel.predicted_demand,
    "product_name": ProductModel.normalized_name,
    "sku": ProductModel.normalized_sku,
    "model_name": ForecastPredictionModel.model_name,
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

    async def get_active_products_for_user(
        self,
        *,
        user_id: UUID,
    ) -> list[ProductModel]:
        result = await self.session.execute(
            select(ProductModel)
            .where(
                ProductModel.user_id == user_id,
                ProductModel.is_active.is_(True),
            )
            .order_by(asc(ProductModel.normalized_sku))
        )
        return list(result.scalars().all())

    async def get_sales_transactions_for_forecasting(
        self,
        *,
        user_id: UUID,
    ) -> list[SalesTransactionModel]:
        result = await self.session.execute(
            select(SalesTransactionModel)
            .options(selectinload(SalesTransactionModel.product))
            .where(
                SalesTransactionModel.user_id == user_id,
                SalesTransactionModel.deleted_at.is_(None),
            )
            .order_by(
                asc(SalesTransactionModel.sale_date),
                asc(SalesTransactionModel.product_id),
            )
        )
        return list(result.scalars().all())

    async def delete_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> None:
        await self.session.execute(
            delete(ForecastPredictionModel).where(
                ForecastPredictionModel.user_id == user_id,
                ForecastPredictionModel.forecast_run_id == forecast_run_id,
            )
        )
        await self.session.execute(
            delete(ForecastModelMetricModel).where(
                ForecastModelMetricModel.user_id == user_id,
                ForecastModelMetricModel.forecast_run_id == forecast_run_id,
            )
        )
        await self.session.flush()

    async def bulk_create_forecast_predictions(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        rows: list[dict[str, Any]],
    ) -> list[ForecastPredictionModel]:
        predictions = [
            ForecastPredictionModel(
                user_id=user_id,
                forecast_run_id=forecast_run_id,
                **row,
            )
            for row in rows
        ]
        self.session.add_all(predictions)
        await self.session.flush()
        return predictions

    async def create_forecast_metrics(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        values: dict[str, Any],
    ) -> ForecastModelMetricModel:
        metrics = ForecastModelMetricModel(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            **values,
        )
        self.session.add(metrics)
        await self.session.flush()
        return metrics

    async def count_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ForecastPredictionModel).where(
                ForecastPredictionModel.user_id == user_id,
                ForecastPredictionModel.forecast_run_id == forecast_run_id,
            )
        )
        return int(result.scalar_one())

    async def get_prediction_date_range(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> tuple[date | None, date | None]:
        result = await self.session.execute(
            select(
                func.min(ForecastPredictionModel.forecast_date),
                func.max(ForecastPredictionModel.forecast_date),
            ).where(
                ForecastPredictionModel.user_id == user_id,
                ForecastPredictionModel.forecast_run_id == forecast_run_id,
            )
        )
        forecast_start_date, forecast_end_date = result.one()
        return forecast_start_date, forecast_end_date

    async def get_total_predicted_demand(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> Decimal:
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(ForecastPredictionModel.predicted_demand), 0)
            ).where(
                ForecastPredictionModel.user_id == user_id,
                ForecastPredictionModel.forecast_run_id == forecast_run_id,
            )
        )
        return Decimal(str(result.scalar_one()))

    async def list_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = self._prediction_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
        )
        total_result = await self.session.execute(
            select(func.count())
            .select_from(ForecastPredictionModel)
            .join(ProductModel, ProductModel.id == ForecastPredictionModel.product_id)
            .where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = FORECAST_RESULT_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(
                ForecastPredictionModel.product_id,
                ProductModel.name.label("product_name"),
                ProductModel.sku,
                ProductModel.category_id,
                ProductCategoryModel.name.label("category_name"),
                ProductModel.unit,
                InventoryItemModel.current_stock,
                InventoryItemModel.minimum_stock,
                InventoryItemModel.safety_stock,
                ForecastPredictionModel.forecast_date,
                ForecastPredictionModel.predicted_demand,
                ForecastPredictionModel.model_name,
            )
            .join(ProductModel, ProductModel.id == ForecastPredictionModel.product_id)
            .outerjoin(
                ProductCategoryModel,
                ProductCategoryModel.id == ProductModel.category_id,
            )
            .outerjoin(
                InventoryItemModel,
                and_(
                    InventoryItemModel.user_id == user_id,
                    InventoryItemModel.product_id == ForecastPredictionModel.product_id,
                ),
            )
            .where(*filters)
            .order_by(
                sort_expression,
                asc(ForecastPredictionModel.forecast_date),
                asc(ProductModel.normalized_sku),
            )
            .limit(limit)
            .offset(offset)
        )
        return [self._prediction_row_to_dict(row) for row in result.all()], total

    async def get_metrics_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> ForecastModelMetricModel | None:
        result = await self.session.execute(
            select(ForecastModelMetricModel)
            .where(
                ForecastModelMetricModel.user_id == user_id,
                ForecastModelMetricModel.forecast_run_id == forecast_run_id,
            )
            .order_by(desc(ForecastModelMetricModel.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_chart_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        interval: str,
    ) -> list[dict[str, Any]]:
        period_start = self._period_expression(
            ForecastPredictionModel.forecast_date,
            interval,
        )
        filters = [
            ForecastPredictionModel.user_id == user_id,
            ForecastPredictionModel.forecast_run_id == forecast_run_id,
        ]
        if product_id is not None:
            filters.append(ForecastPredictionModel.product_id == product_id)
        if date_from is not None:
            filters.append(ForecastPredictionModel.forecast_date >= date_from)
        if date_to is not None:
            filters.append(ForecastPredictionModel.forecast_date <= date_to)

        result = await self.session.execute(
            select(
                period_start.label("period_start"),
                func.coalesce(func.sum(ForecastPredictionModel.predicted_demand), 0),
            )
            .where(*filters)
            .group_by(period_start)
            .order_by(period_start)
        )
        return [
            {
                "period_start": row[0],
                "predicted_demand": Decimal(str(row[1])),
            }
            for row in result.all()
        ]

    async def get_actual_sales_for_forecast_dates(
        self,
        *,
        user_id: UUID,
        product_id: UUID | None,
        date_from: date,
        date_to: date,
        interval: str,
    ) -> list[dict[str, Any]]:
        period_start = self._period_expression(
            SalesTransactionModel.sale_date,
            interval,
        )
        filters = [
            SalesTransactionModel.user_id == user_id,
            SalesTransactionModel.deleted_at.is_(None),
            SalesTransactionModel.sale_date >= date_from,
            SalesTransactionModel.sale_date <= date_to,
        ]
        if product_id is not None:
            filters.append(SalesTransactionModel.product_id == product_id)

        result = await self.session.execute(
            select(
                period_start.label("period_start"),
                func.coalesce(func.sum(SalesTransactionModel.quantity), 0),
            )
            .where(*filters)
            .group_by(period_start)
            .order_by(period_start)
        )
        return [
            {
                "period_start": row[0],
                "actual_quantity": Decimal(str(row[1])),
            }
            for row in result.all()
        ]

    async def get_product_forecast_detail(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID,
    ) -> list[dict[str, Any]]:
        rows, _ = await self.list_predictions_for_run(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=None,
            date_from=None,
            date_to=None,
            search=None,
            limit=1000,
            offset=0,
            sort_by="forecast_date",
            sort_order="asc",
        )
        return rows

    async def get_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> ProductModel | None:
        result = await self.session.execute(
            select(ProductModel).where(
                ProductModel.id == product_id,
                ProductModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_inventory_snapshot_for_products(
        self,
        *,
        user_id: UUID,
        product_ids: set[UUID],
    ) -> dict[UUID, InventoryItemModel]:
        if not product_ids:
            return {}
        result = await self.session.execute(
            select(InventoryItemModel).where(
                InventoryItemModel.user_id == user_id,
                InventoryItemModel.product_id.in_(product_ids),
            )
        )
        return {item.product_id: item for item in result.scalars().all()}

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    def _prediction_filters(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
    ) -> list[Any]:
        filters = [
            ForecastPredictionModel.user_id == user_id,
            ForecastPredictionModel.forecast_run_id == forecast_run_id,
            ProductModel.user_id == user_id,
        ]
        if product_id is not None:
            filters.append(ForecastPredictionModel.product_id == product_id)
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        if date_from is not None:
            filters.append(ForecastPredictionModel.forecast_date >= date_from)
        if date_to is not None:
            filters.append(ForecastPredictionModel.forecast_date <= date_to)
        if search:
            search_value = search.strip()
            if search_value:
                filters.append(
                    or_(
                        ProductModel.name.ilike(f"%{search_value}%"),
                        ProductModel.normalized_sku.ilike(
                            f"%{search_value.upper()}%"
                        ),
                        ForecastPredictionModel.model_name.ilike(
                            f"%{search_value}%"
                        ),
                    )
                )
        return filters

    def _period_expression(self, column: Any, interval: str) -> Any:
        return cast(func.date_trunc(interval, column), SqlDate)

    def _prediction_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "sku": row.sku,
            "category_id": row.category_id,
            "category_name": row.category_name,
            "unit": row.unit,
            "current_stock": row.current_stock,
            "minimum_stock": row.minimum_stock,
            "safety_stock": row.safety_stock,
            "forecast_date": row.forecast_date,
            "predicted_demand": Decimal(str(row.predicted_demand)),
            "model_name": row.model_name,
        }
