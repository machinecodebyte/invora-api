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
from app.modules.inventory.infrastructure.models import InventoryItemModel
from app.modules.products.infrastructure.models import (
    ProductCategoryModel,
    ProductModel,
)
from app.modules.recommendations.infrastructure.models import (
    ReorderRecommendationModel,
)
from app.modules.sales.infrastructure.models import SalesTransactionModel


class ReportsRepository:
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
    ) -> ForecastRunModel | None:
        result = await self.session.execute(
            select(ForecastRunModel).where(
                ForecastRunModel.id == forecast_run_id,
                ForecastRunModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_model_performance_summary_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        run_filters = self._forecast_run_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            date_from=date_from,
            date_to=date_to,
        )
        run_result = await self.session.execute(
            select(
                func.count(ForecastRunModel.id),
                func.count(case((ForecastRunModel.status == "completed", 1))),
                func.count(case((ForecastRunModel.status == "failed", 1))),
            ).where(*run_filters)
        )
        total_runs, completed_runs, failed_runs = run_result.one()
        metric_result = await self.session.execute(
            select(
                func.avg(ForecastModelMetricModel.mae),
                func.avg(ForecastModelMetricModel.rmse),
                func.avg(ForecastModelMetricModel.mape),
            )
            .join(
                ForecastRunModel,
                ForecastRunModel.id == ForecastModelMetricModel.forecast_run_id,
            )
            .where(*run_filters)
        )
        avg_mae, avg_rmse, avg_mape = metric_result.one()
        return {
            "total_forecast_runs": int(total_runs),
            "completed_forecast_runs": int(completed_runs),
            "failed_forecast_runs": int(failed_runs),
            "average_mae": _optional_decimal(avg_mae),
            "average_rmse": _optional_decimal(avg_rmse),
            "average_mape": _optional_decimal(avg_mape),
        }

    async def get_model_performance_rows_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, Any]]:
        filters = self._forecast_run_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.session.execute(
            select(
                ForecastRunModel.id.label("forecast_run_id"),
                ForecastRunModel.status,
                ForecastRunModel.horizon_days,
                ForecastRunModel.requested_at,
                ForecastRunModel.completed_at,
                ForecastModelMetricModel.model_name,
                ForecastModelMetricModel.mae,
                ForecastModelMetricModel.rmse,
                ForecastModelMetricModel.mape,
                ForecastModelMetricModel.training_rows,
                ForecastModelMetricModel.validation_rows,
                ForecastModelMetricModel.total_products,
                ForecastModelMetricModel.fallback_products,
                ForecastModelMetricModel.created_at,
            )
            .join(
                ForecastRunModel,
                ForecastRunModel.id == ForecastModelMetricModel.forecast_run_id,
            )
            .where(*filters)
            .order_by(
                desc(ForecastRunModel.requested_at),
                desc(ForecastModelMetricModel.created_at),
            )
        )
        return [
            {
                "forecast_run_id": row.forecast_run_id,
                "status": row.status,
                "horizon_days": row.horizon_days,
                "requested_at": row.requested_at,
                "completed_at": row.completed_at,
                "model_name": row.model_name,
                "mae": _optional_decimal(row.mae),
                "rmse": _optional_decimal(row.rmse),
                "mape": _optional_decimal(row.mape),
                "training_rows": row.training_rows,
                "validation_rows": row.validation_rows,
                "total_products": row.total_products,
                "fallback_products": row.fallback_products,
                "created_at": row.created_at,
            }
            for row in result.all()
        ]

    async def get_inventory_risk_summary_for_user(
        self,
        *,
        user_id: UUID,
        category_id: UUID | None,
        stock_status: str | None,
    ) -> dict[str, int]:
        filters = self._inventory_filters(
            user_id=user_id,
            category_id=category_id,
            stock_status=stock_status,
        )
        low_condition = self._stock_status_condition("low_stock")
        out_condition = self._stock_status_condition("out_of_stock")
        healthy_condition = self._stock_status_condition("healthy")
        inactive_condition = self._stock_status_condition("inactive")
        query = (
            select(
                func.count(InventoryItemModel.id),
                func.count(case((low_condition, 1))),
                func.count(case((out_condition, 1))),
                func.count(case((healthy_condition, 1))),
                func.count(case((inactive_condition, 1))),
            )
            .join(ProductModel, ProductModel.id == InventoryItemModel.product_id)
            .where(*filters)
        )
        total, low, out, healthy, inactive = (await self.session.execute(query)).one()
        return {
            "total_inventory_items": int(total),
            "low_stock_count": int(low),
            "out_of_stock_count": int(out),
            "healthy_stock_count": int(healthy),
            "inactive_inventory_count": int(inactive),
        }

    async def get_inventory_risk_rows_for_user(
        self,
        *,
        user_id: UUID,
        category_id: UUID | None,
        stock_status: str | None,
    ) -> list[dict[str, Any]]:
        filters = self._inventory_filters(
            user_id=user_id,
            category_id=category_id,
            stock_status=stock_status,
        )
        result = await self.session.execute(
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
            .where(*filters)
            .order_by(ProductModel.normalized_sku)
        )
        return [self._inventory_row(row) for row in result.all()]

    async def get_reorder_summary_counts_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
    ) -> dict[str, Any]:
        filters = self._recommendation_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            risk_level=risk_level,
            status=status,
        )
        total_result = await self.session.execute(
            select(
                func.count(ReorderRecommendationModel.id),
                func.coalesce(func.sum(ReorderRecommendationModel.reorder_quantity), 0),
            ).where(*filters)
        )
        total, reorder_quantity = total_result.one()
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
            "total_recommendations": int(total),
            "open_recommendations": status_counts.get("open", 0),
            "acknowledged_recommendations": status_counts.get("acknowledged", 0),
            "dismissed_recommendations": status_counts.get("dismissed", 0),
            "critical_count": risk_counts.get("critical", 0),
            "high_count": risk_counts.get("high", 0),
            "medium_count": risk_counts.get("medium", 0),
            "low_count": risk_counts.get("low", 0),
            "overstocked_count": risk_counts.get("overstocked", 0),
            "total_reorder_quantity": Decimal(str(reorder_quantity)),
        }

    async def get_reorder_summary_rows_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
    ) -> list[dict[str, Any]]:
        filters = self._recommendation_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            risk_level=risk_level,
            status=status,
        )
        result = await self.session.execute(
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
            .where(*filters)
            .order_by(
                desc(ReorderRecommendationModel.reorder_quantity),
                desc(ReorderRecommendationModel.generated_at),
                ProductModel.normalized_sku,
            )
        )
        return [self._recommendation_row(row) for row in result.all()]

    async def get_demand_forecast_summary_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        filters = self._prediction_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.session.execute(
            select(
                func.min(ForecastPredictionModel.forecast_date),
                func.max(ForecastPredictionModel.forecast_date),
                func.count(func.distinct(ForecastPredictionModel.product_id)),
                func.coalesce(func.sum(ForecastPredictionModel.predicted_demand), 0),
                func.coalesce(func.avg(ForecastPredictionModel.predicted_demand), 0),
            )
            .join(ProductModel, ProductModel.id == ForecastPredictionModel.product_id)
            .where(*filters)
        )
        date_from_result, date_to_result, products, total, average = result.one()
        return {
            "forecast_date_range": {
                "date_from": date_from_result,
                "date_to": date_to_result,
            },
            "total_products": int(products),
            "total_predicted_demand": Decimal(str(total)),
            "average_predicted_demand": Decimal(str(average)),
        }

    async def get_demand_forecast_rows_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, Any]]:
        filters = self._prediction_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.session.execute(
            select(
                ForecastPredictionModel.product_id,
                ProductModel.name.label("product_name"),
                ProductModel.sku,
                ProductModel.category_id,
                ProductCategoryModel.name.label("category_name"),
                ForecastPredictionModel.forecast_date,
                ForecastPredictionModel.predicted_demand,
                ForecastPredictionModel.model_name,
            )
            .join(ProductModel, ProductModel.id == ForecastPredictionModel.product_id)
            .outerjoin(
                ProductCategoryModel,
                ProductCategoryModel.id == ProductModel.category_id,
            )
            .where(*filters)
            .order_by(
                ForecastPredictionModel.forecast_date,
                ProductModel.normalized_sku,
            )
        )
        return [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "sku": row.sku,
                "category_id": row.category_id,
                "category_name": row.category_name,
                "forecast_date": row.forecast_date,
                "predicted_demand": Decimal(str(row.predicted_demand)),
                "model_name": row.model_name,
            }
            for row in result.all()
        ]

    async def get_sales_summary_totals_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
        product_id: UUID | None,
        category_id: UUID | None,
        channel: str | None,
    ) -> dict[str, Any]:
        filters = self._sales_filters(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            product_id=product_id,
            category_id=category_id,
            channel=channel,
        )
        result = await self.session.execute(
            select(
                func.count(SalesTransactionModel.id),
                func.coalesce(func.sum(SalesTransactionModel.quantity), 0),
                func.coalesce(func.sum(SalesTransactionModel.total_amount), 0),
                func.count(func.distinct(SalesTransactionModel.product_id)),
                func.coalesce(func.avg(SalesTransactionModel.total_amount), 0),
            )
            .join(ProductModel, ProductModel.id == SalesTransactionModel.product_id)
            .where(*filters)
        )
        total, quantity, amount, unique_products, average = result.one()
        return {
            "total_transactions": int(total),
            "total_quantity_sold": Decimal(str(quantity)),
            "total_sales_amount": Decimal(str(amount)),
            "unique_products_sold": int(unique_products),
            "average_transaction_amount": Decimal(str(average)),
        }

    async def get_sales_summary_rows_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
        product_id: UUID | None,
        category_id: UUID | None,
        channel: str | None,
    ) -> list[dict[str, Any]]:
        filters = self._sales_filters(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            product_id=product_id,
            category_id=category_id,
            channel=channel,
        )
        total_amount = func.coalesce(func.sum(SalesTransactionModel.total_amount), 0)
        transaction_count = func.count(SalesTransactionModel.id)
        result = await self.session.execute(
            select(
                ProductModel.id.label("product_id"),
                ProductModel.name.label("product_name"),
                ProductModel.sku,
                ProductModel.category_id,
                ProductCategoryModel.name.label("category_name"),
                func.coalesce(func.sum(SalesTransactionModel.quantity), 0),
                total_amount,
                transaction_count,
                func.coalesce(func.avg(SalesTransactionModel.total_amount), 0),
            )
            .join(ProductModel, ProductModel.id == SalesTransactionModel.product_id)
            .outerjoin(
                ProductCategoryModel,
                ProductCategoryModel.id == ProductModel.category_id,
            )
            .where(*filters)
            .group_by(
                ProductModel.id,
                ProductModel.name,
                ProductModel.sku,
                ProductModel.category_id,
                ProductCategoryModel.name,
            )
            .order_by(desc(total_amount), ProductModel.normalized_sku)
        )
        return [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "sku": row.sku,
                "category_id": row.category_id,
                "category_name": row.category_name,
                "total_quantity_sold": Decimal(str(row[5])),
                "total_sales_amount": Decimal(str(row[6])),
                "transaction_count": int(row[7]),
                "average_transaction_amount": Decimal(str(row[8])),
            }
            for row in result.all()
        ]

    def _forecast_run_filters(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> list[Any]:
        filters = [ForecastRunModel.user_id == user_id]
        if forecast_run_id is not None:
            filters.append(ForecastRunModel.id == forecast_run_id)
        requested_date = cast(ForecastRunModel.requested_at, Date)
        if date_from is not None:
            filters.append(requested_date >= date_from)
        if date_to is not None:
            filters.append(requested_date <= date_to)
        return filters

    def _inventory_filters(
        self,
        *,
        user_id: UUID,
        category_id: UUID | None,
        stock_status: str | None,
    ) -> list[Any]:
        filters = [
            InventoryItemModel.user_id == user_id,
            ProductModel.user_id == user_id,
        ]
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        if stock_status is not None:
            filters.append(self._stock_status_condition(stock_status))
        return filters

    def _stock_status_condition(self, stock_status: str) -> Any:
        zero = Decimal("0.000")
        if stock_status == "low_stock":
            return and_(
                InventoryItemModel.is_active.is_(True),
                InventoryItemModel.current_stock > zero,
                InventoryItemModel.current_stock <= InventoryItemModel.minimum_stock,
            )
        if stock_status == "out_of_stock":
            return and_(
                InventoryItemModel.is_active.is_(True),
                InventoryItemModel.current_stock == zero,
            )
        if stock_status == "healthy":
            return and_(
                InventoryItemModel.is_active.is_(True),
                InventoryItemModel.current_stock > InventoryItemModel.minimum_stock,
            )
        return InventoryItemModel.is_active.is_(False)

    def _recommendation_filters(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
    ) -> list[Any]:
        filters = [ReorderRecommendationModel.user_id == user_id]
        if forecast_run_id is not None:
            filters.append(
                ReorderRecommendationModel.forecast_run_id == forecast_run_id
            )
        if risk_level is not None:
            filters.append(ReorderRecommendationModel.risk_level == risk_level)
        if status is not None:
            filters.append(ReorderRecommendationModel.status == status)
        return filters

    def _prediction_filters(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
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
        return filters

    def _sales_filters(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
        product_id: UUID | None,
        category_id: UUID | None,
        channel: str | None,
    ) -> list[Any]:
        filters = [
            SalesTransactionModel.user_id == user_id,
            SalesTransactionModel.deleted_at.is_(None),
            ProductModel.user_id == user_id,
        ]
        if date_from is not None:
            filters.append(SalesTransactionModel.sale_date >= date_from)
        if date_to is not None:
            filters.append(SalesTransactionModel.sale_date <= date_to)
        if product_id is not None:
            filters.append(SalesTransactionModel.product_id == product_id)
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        if channel is not None:
            filters.append(SalesTransactionModel.channel == channel)
        return filters

    def _inventory_row(self, row: Any) -> dict[str, Any]:
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
            "stock_status": _report_stock_status(
                current_stock=item.current_stock,
                minimum_stock=item.minimum_stock,
                is_active=item.is_active,
            ),
        }

    def _recommendation_row(self, row: Any) -> dict[str, Any]:
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
            "minimum_stock": recommendation.minimum_stock,
            "safety_stock": recommendation.safety_stock,
            "required_stock": recommendation.required_stock,
            "reorder_quantity": recommendation.reorder_quantity,
            "risk_level": recommendation.risk_level,
            "recommended_action": recommendation.recommended_action,
            "status": recommendation.status,
            "generated_at": recommendation.generated_at,
        }


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _report_stock_status(
    *,
    current_stock: Decimal,
    minimum_stock: Decimal,
    is_active: bool,
) -> str:
    status = calculate_stock_status(
        current_stock=current_stock,
        minimum_stock=minimum_stock,
        is_active=is_active,
    )
    return "healthy" if status == "in_stock" else status
