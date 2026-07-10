from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Date, and_, case, cast, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forecasting.infrastructure.models import (
    ForecastModelMetricModel,
    ForecastPredictionModel,
    ForecastRunModel,
)
from app.modules.inventory.domain.stock import calculate_stock_status
from app.modules.inventory.infrastructure.models import (
    InventoryItemModel,
    InventoryStockMovementModel,
)
from app.modules.products.infrastructure.models import (
    ProductCategoryModel,
    ProductModel,
)
from app.modules.recommendations.infrastructure.models import (
    ReorderRecommendationModel,
)
from app.modules.sales.infrastructure.models import (
    SalesTransactionModel,
    SalesUploadBatchModel,
)


class DashboardAnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def validate_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> bool:
        result = await self.session.execute(
            select(ProductModel.id).where(
                ProductModel.id == product_id,
                ProductModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def validate_category_for_user(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> bool:
        result = await self.session.execute(
            select(ProductCategoryModel.id).where(
                ProductCategoryModel.id == category_id,
                ProductCategoryModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def validate_forecast_run_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> bool:
        result = await self.session.execute(
            select(ForecastRunModel.id).where(
                ForecastRunModel.id == forecast_run_id,
                ForecastRunModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_product_counts_for_user(self, *, user_id: UUID) -> dict[str, int]:
        result = await self.session.execute(
            select(
                func.count(ProductModel.id),
                func.count(case((ProductModel.is_active.is_(True), 1))),
            ).where(ProductModel.user_id == user_id)
        )
        total_products, active_products = result.one()
        return {
            "total_products": int(total_products),
            "active_products": int(active_products),
        }

    async def get_sales_counts_for_user(self, *, user_id: UUID) -> dict[str, int]:
        result = await self.session.execute(
            select(func.count(SalesTransactionModel.id)).where(
                SalesTransactionModel.user_id == user_id,
                SalesTransactionModel.deleted_at.is_(None),
            )
        )
        return {"total_sales_records": int(result.scalar_one())}

    async def get_inventory_counts_for_user(self, *, user_id: UUID) -> dict[str, int]:
        zero = Decimal("0.000")
        low_condition = and_(
            InventoryItemModel.is_active.is_(True),
            InventoryItemModel.current_stock > zero,
            InventoryItemModel.current_stock <= InventoryItemModel.minimum_stock,
        )
        out_condition = and_(
            InventoryItemModel.is_active.is_(True),
            InventoryItemModel.current_stock == zero,
        )
        healthy_condition = and_(
            InventoryItemModel.is_active.is_(True),
            InventoryItemModel.current_stock > InventoryItemModel.minimum_stock,
        )
        inactive_condition = InventoryItemModel.is_active.is_(False)
        result = await self.session.execute(
            select(
                func.count(InventoryItemModel.id),
                func.count(case((low_condition, 1))),
                func.count(case((out_condition, 1))),
                func.count(case((healthy_condition, 1))),
                func.count(case((inactive_condition, 1))),
            ).where(InventoryItemModel.user_id == user_id)
        )
        total, low, out, healthy, inactive = result.one()
        return {
            "total_inventory_items": int(total),
            "low_stock_count": int(low),
            "out_of_stock_count": int(out),
            "healthy_stock_count": int(healthy),
            "inactive_inventory_count": int(inactive),
        }

    async def get_low_stock_preview_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        zero = Decimal("0.000")
        result = await self.session.execute(
            self._inventory_preview_select()
            .where(
                InventoryItemModel.user_id == user_id,
                InventoryItemModel.is_active.is_(True),
                InventoryItemModel.current_stock > zero,
                InventoryItemModel.current_stock <= InventoryItemModel.minimum_stock,
            )
            .order_by(
                InventoryItemModel.current_stock.asc(),
                ProductModel.normalized_sku,
            )
            .limit(limit)
        )
        return [self._inventory_preview_row(row) for row in result.all()]

    async def get_out_of_stock_preview_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            self._inventory_preview_select()
            .where(
                InventoryItemModel.user_id == user_id,
                InventoryItemModel.is_active.is_(True),
                InventoryItemModel.current_stock == Decimal("0.000"),
            )
            .order_by(ProductModel.normalized_sku)
            .limit(limit)
        )
        return [self._inventory_preview_row(row) for row in result.all()]

    async def get_demand_trends_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date,
        date_to: date,
        interval: str,
        product_id: UUID | None,
        category_id: UUID | None,
    ) -> list[dict[str, Any]]:
        period = self._sales_period_expression(interval)
        filters = [
            SalesTransactionModel.user_id == user_id,
            SalesTransactionModel.deleted_at.is_(None),
            SalesTransactionModel.sale_date >= date_from,
            SalesTransactionModel.sale_date <= date_to,
        ]
        query = select(
            period.label("period"),
            func.coalesce(func.sum(SalesTransactionModel.quantity), 0),
            func.coalesce(func.sum(SalesTransactionModel.total_amount), 0),
            func.count(SalesTransactionModel.id),
        ).where(*filters)
        if product_id is not None:
            query = query.where(SalesTransactionModel.product_id == product_id)
        if category_id is not None:
            query = query.join(
                ProductModel,
                ProductModel.id == SalesTransactionModel.product_id,
            ).where(ProductModel.category_id == category_id)
        query = query.group_by(period).order_by(period)
        result = await self.session.execute(query)
        return [
            {
                "period": row[0],
                "total_quantity_sold": Decimal(str(row[1])),
                "total_sales_amount": Decimal(str(row[2])),
                "transaction_count": int(row[3]),
            }
            for row in result.all()
        ]

    async def get_latest_forecast_overview_for_user(
        self,
        *,
        user_id: UUID,
    ) -> dict[str, Any]:
        latest_run_result = await self.session.execute(
            select(ForecastRunModel)
            .where(ForecastRunModel.user_id == user_id)
            .order_by(desc(ForecastRunModel.requested_at))
            .limit(1)
        )
        latest_completed_result = await self.session.execute(
            select(ForecastRunModel)
            .where(
                ForecastRunModel.user_id == user_id,
                ForecastRunModel.status == "completed",
            )
            .order_by(desc(ForecastRunModel.completed_at))
            .limit(1)
        )
        latest_run = latest_run_result.scalar_one_or_none()
        latest_completed = latest_completed_result.scalar_one_or_none()
        return {
            "latest_forecast_run": self._forecast_run_to_dict(latest_run),
            "latest_completed_forecast_run": self._forecast_run_to_dict(
                latest_completed
            ),
        }

    async def get_forecast_run_counts_for_user(
        self,
        *,
        user_id: UUID,
    ) -> dict[str, int]:
        result = await self.session.execute(
            select(ForecastRunModel.status, func.count(ForecastRunModel.id))
            .where(ForecastRunModel.user_id == user_id)
            .group_by(ForecastRunModel.status)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def get_latest_forecast_metrics_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
    ) -> dict[str, Any] | None:
        if forecast_run_id is None:
            return None
        result = await self.session.execute(
            select(ForecastModelMetricModel)
            .where(
                ForecastModelMetricModel.user_id == user_id,
                ForecastModelMetricModel.forecast_run_id == forecast_run_id,
            )
            .order_by(desc(ForecastModelMetricModel.created_at))
            .limit(1)
        )
        return self._metric_to_dict(result.scalar_one_or_none())

    async def get_prediction_summary_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
    ) -> dict[str, Any]:
        if forecast_run_id is None:
            return self._empty_prediction_summary()
        result = await self.session.execute(
            select(
                func.count(ForecastPredictionModel.id),
                func.min(ForecastPredictionModel.forecast_date),
                func.max(ForecastPredictionModel.forecast_date),
                func.coalesce(func.sum(ForecastPredictionModel.predicted_demand), 0),
            ).where(
                ForecastPredictionModel.user_id == user_id,
                ForecastPredictionModel.forecast_run_id == forecast_run_id,
            )
        )
        total, date_from, date_to, total_predicted = result.one()
        return {
            "total_predictions_in_latest_run": int(total),
            "forecast_date_range": {"date_from": date_from, "date_to": date_to},
            "total_predicted_demand": Decimal(str(total_predicted)),
        }

    async def get_reorder_alert_counts_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
    ) -> dict[str, Any]:
        filters = [ReorderRecommendationModel.user_id == user_id]
        if forecast_run_id is not None:
            filters.append(
                ReorderRecommendationModel.forecast_run_id == forecast_run_id
            )
        aggregate_result = await self.session.execute(
            select(
                func.coalesce(func.sum(ReorderRecommendationModel.reorder_quantity), 0),
            ).where(*filters)
        )
        risk_result = await self.session.execute(
            select(
                ReorderRecommendationModel.risk_level,
                func.count(ReorderRecommendationModel.id),
            )
            .where(*filters)
            .group_by(ReorderRecommendationModel.risk_level)
        )
        status_result = await self.session.execute(
            select(
                ReorderRecommendationModel.status,
                func.count(ReorderRecommendationModel.id),
            )
            .where(*filters)
            .group_by(ReorderRecommendationModel.status)
        )
        risk_counts = {row[0]: int(row[1]) for row in risk_result.all()}
        status_counts = {row[0]: int(row[1]) for row in status_result.all()}
        return {
            "critical_count": risk_counts.get("critical", 0),
            "high_count": risk_counts.get("high", 0),
            "medium_count": risk_counts.get("medium", 0),
            "low_count": risk_counts.get("low", 0),
            "overstocked_count": risk_counts.get("overstocked", 0),
            "open_count": status_counts.get("open", 0),
            "acknowledged_count": status_counts.get("acknowledged", 0),
            "dismissed_count": status_counts.get("dismissed", 0),
            "total_reorder_quantity": Decimal(str(aggregate_result.scalar_one())),
        }

    async def get_top_reorder_items_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        filters = [ReorderRecommendationModel.user_id == user_id]
        if forecast_run_id is not None:
            filters.append(
                ReorderRecommendationModel.forecast_run_id == forecast_run_id
            )
        if risk_level is not None:
            filters.append(ReorderRecommendationModel.risk_level == risk_level)
        if status is not None:
            filters.append(ReorderRecommendationModel.status == status)
        result = await self.session.execute(
            self._recommendation_alert_select()
            .where(*filters)
            .order_by(
                desc(ReorderRecommendationModel.reorder_quantity),
                desc(ReorderRecommendationModel.generated_at),
                ProductModel.normalized_sku,
            )
            .limit(limit)
        )
        return [self._recommendation_alert_row(row) for row in result.all()]

    async def get_recent_sales_uploads_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(SalesUploadBatchModel)
            .where(SalesUploadBatchModel.user_id == user_id)
            .order_by(desc(SalesUploadBatchModel.started_at))
            .limit(limit)
        )
        return [
            {
                "id": row.id,
                "filename": row.original_filename,
                "status": row.status,
                "accepted_rows": row.accepted_rows,
                "rejected_rows": row.rejected_rows,
                "occurred_at": row.completed_at or row.started_at,
            }
            for row in result.scalars().all()
        ]

    async def get_recent_forecast_runs_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(ForecastRunModel)
            .where(ForecastRunModel.user_id == user_id)
            .order_by(desc(ForecastRunModel.updated_at))
            .limit(limit)
        )
        return [
            {
                "id": row.id,
                "status": row.status,
                "horizon_days": row.horizon_days,
                "occurred_at": row.updated_at,
            }
            for row in result.scalars().all()
        ]

    async def get_recent_stock_movements_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(
                InventoryStockMovementModel,
                ProductModel.name.label("product_name"),
                ProductModel.sku,
            )
            .join(
                ProductModel,
                ProductModel.id == InventoryStockMovementModel.product_id,
            )
            .where(InventoryStockMovementModel.user_id == user_id)
            .order_by(desc(InventoryStockMovementModel.occurred_at))
            .limit(limit)
        )
        return [
            {
                "id": row[0].id,
                "product_id": row[0].product_id,
                "product_name": row.product_name,
                "sku": row.sku,
                "movement_type": row[0].movement_type,
                "quantity_delta": row[0].quantity_delta,
                "occurred_at": row[0].occurred_at,
            }
            for row in result.all()
        ]

    async def get_recent_recommendations_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(
                ReorderRecommendationModel,
                ProductModel.name.label("product_name"),
                ProductModel.sku,
            )
            .join(
                ProductModel,
                ProductModel.id == ReorderRecommendationModel.product_id,
            )
            .where(ReorderRecommendationModel.user_id == user_id)
            .order_by(desc(ReorderRecommendationModel.generated_at))
            .limit(limit)
        )
        return [
            {
                "id": row[0].id,
                "forecast_run_id": row[0].forecast_run_id,
                "product_id": row[0].product_id,
                "product_name": row.product_name,
                "sku": row.sku,
                "risk_level": row[0].risk_level,
                "reorder_quantity": row[0].reorder_quantity,
                "status": row[0].status,
                "occurred_at": row[0].generated_at,
            }
            for row in result.all()
        ]

    def _sales_period_expression(self, interval: str) -> Any:
        if interval == "day":
            return SalesTransactionModel.sale_date
        return cast(func.date_trunc(interval, SalesTransactionModel.sale_date), Date)

    def _inventory_preview_select(self) -> Any:
        return (
            select(
                InventoryItemModel,
                ProductModel.name.label("product_name"),
                ProductModel.sku,
                ProductModel.category_id,
                ProductCategoryModel.name.label("category_name"),
            )
            .join(ProductModel, ProductModel.id == InventoryItemModel.product_id)
            .outerjoin(
                ProductCategoryModel,
                ProductCategoryModel.id == ProductModel.category_id,
            )
        )

    def _inventory_preview_row(self, row: Any) -> dict[str, Any]:
        item = row[0]
        return {
            "product_id": item.product_id,
            "product_name": row.product_name,
            "sku": row.sku,
            "category_id": row.category_id,
            "category_name": row.category_name,
            "current_stock": item.current_stock,
            "minimum_stock": item.minimum_stock,
            "safety_stock": item.safety_stock,
            "stock_status": calculate_stock_status(
                current_stock=item.current_stock,
                minimum_stock=item.minimum_stock,
                is_active=item.is_active,
            ),
        }

    def _recommendation_alert_select(self) -> Any:
        return (
            select(
                ReorderRecommendationModel,
                ProductModel.name.label("product_name"),
                ProductModel.sku,
                ProductModel.category_id,
                ProductCategoryModel.name.label("category_name"),
            )
            .join(
                ProductModel,
                ProductModel.id == ReorderRecommendationModel.product_id,
            )
            .outerjoin(
                ProductCategoryModel,
                ProductCategoryModel.id == ProductModel.category_id,
            )
        )

    def _recommendation_alert_row(self, row: Any) -> dict[str, Any]:
        recommendation = row[0]
        return {
            "id": recommendation.id,
            "forecast_run_id": recommendation.forecast_run_id,
            "product_id": recommendation.product_id,
            "product_name": row.product_name,
            "sku": row.sku,
            "category_id": row.category_id,
            "category_name": row.category_name,
            "predicted_demand": recommendation.predicted_demand,
            "current_stock": recommendation.current_stock,
            "required_stock": recommendation.required_stock,
            "reorder_quantity": recommendation.reorder_quantity,
            "risk_level": recommendation.risk_level,
            "recommended_action": recommendation.recommended_action,
            "status": recommendation.status,
            "generated_at": recommendation.generated_at,
        }

    def _forecast_run_to_dict(
        self,
        run: ForecastRunModel | None,
    ) -> dict[str, Any] | None:
        if run is None:
            return None
        return {
            "id": run.id,
            "horizon_days": run.horizon_days,
            "status": run.status,
            "requested_at": run.requested_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "failed_at": run.failed_at,
            "cancelled_at": run.cancelled_at,
            "failure_reason": run.failure_reason,
            "total_products": run.total_products,
            "total_sales_records": run.total_sales_records,
        }

    def _metric_to_dict(
        self,
        metric: ForecastModelMetricModel | None,
    ) -> dict[str, Any] | None:
        if metric is None:
            return None
        return {
            "model_name": metric.model_name,
            "mae": metric.mae,
            "rmse": metric.rmse,
            "mape": metric.mape,
            "training_rows": metric.training_rows,
            "validation_rows": metric.validation_rows,
            "total_products": metric.total_products,
            "fallback_products": metric.fallback_products,
            "created_at": metric.created_at,
        }

    def _empty_prediction_summary(self) -> dict[str, Any]:
        return {
            "total_predictions_in_latest_run": 0,
            "forecast_date_range": {"date_from": None, "date_to": None},
            "total_predicted_demand": Decimal("0.000"),
        }
