from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import asc, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.forecasting.infrastructure.models import (
    ForecastPredictionModel,
    ForecastRunModel,
)
from app.modules.inventory.infrastructure.models import InventoryItemModel
from app.modules.products.infrastructure.models import (
    ProductCategoryModel,
    ProductModel,
)
from app.modules.recommendations.infrastructure.models import (
    ReorderRecommendationModel,
)
from app.shared.utils import utc_now

RECOMMENDATION_SORT_COLUMNS = {
    "generated_at": ReorderRecommendationModel.generated_at,
    "risk_level": ReorderRecommendationModel.risk_level,
    "reorder_quantity": ReorderRecommendationModel.reorder_quantity,
    "predicted_demand": ReorderRecommendationModel.predicted_demand,
    "current_stock": ReorderRecommendationModel.current_stock,
    "product_name": ProductModel.normalized_name,
    "sku": ProductModel.normalized_sku,
    "status": ReorderRecommendationModel.status,
}


class ReorderRecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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

    async def get_predictions_grouped_by_product_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(
                ForecastPredictionModel.product_id,
                func.coalesce(func.sum(ForecastPredictionModel.predicted_demand), 0),
            )
            .where(
                ForecastPredictionModel.user_id == user_id,
                ForecastPredictionModel.forecast_run_id == forecast_run_id,
            )
            .group_by(ForecastPredictionModel.product_id)
            .order_by(ForecastPredictionModel.product_id)
        )
        return [
            {
                "product_id": row[0],
                "predicted_demand": Decimal(str(row[1])),
            }
            for row in result.all()
        ]

    async def get_inventory_items_for_products(
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

    async def get_products_for_user_by_ids(
        self,
        *,
        user_id: UUID,
        product_ids: set[UUID],
    ) -> dict[UUID, ProductModel]:
        if not product_ids:
            return {}
        result = await self.session.execute(
            select(ProductModel).where(
                ProductModel.user_id == user_id,
                ProductModel.id.in_(product_ids),
            )
        )
        return {product.id: product for product in result.scalars().all()}

    async def count_existing_recommendations_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ReorderRecommendationModel).where(
                ReorderRecommendationModel.user_id == user_id,
                ReorderRecommendationModel.forecast_run_id == forecast_run_id,
            )
        )
        return int(result.scalar_one())

    async def delete_recommendations_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> None:
        await self.session.execute(
            delete(ReorderRecommendationModel).where(
                ReorderRecommendationModel.user_id == user_id,
                ReorderRecommendationModel.forecast_run_id == forecast_run_id,
            )
        )
        await self.session.flush()

    async def bulk_create_recommendations(
        self,
        *,
        user_id: UUID,
        rows: list[dict[str, Any]],
    ) -> list[ReorderRecommendationModel]:
        recommendations = [
            ReorderRecommendationModel(user_id=user_id, **row) for row in rows
        ]
        self.session.add_all(recommendations)
        await self.session.flush()
        return recommendations

    async def list_recommendations_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        product_id: UUID | None,
        category_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        action: str | None,
        generated_from: datetime | None,
        generated_to: datetime | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = self._recommendation_filters(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=category_id,
            risk_level=risk_level,
            status=status,
            action=action,
            generated_from=generated_from,
            generated_to=generated_to,
            search=search,
        )
        total_result = await self.session.execute(
            select(func.count())
            .select_from(ReorderRecommendationModel)
            .join(
                ProductModel,
                ProductModel.id == ReorderRecommendationModel.product_id,
            )
            .where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = RECOMMENDATION_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            self._recommendation_select()
            .where(*filters)
            .order_by(
                sort_expression,
                desc(ReorderRecommendationModel.generated_at),
                asc(ProductModel.normalized_sku),
            )
            .limit(limit)
            .offset(offset)
        )
        return [self._row_to_recommendation_dict(row) for row in result.all()], total

    async def list_recommendations_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[dict[str, Any]], int]:
        return await self.list_recommendations_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=None,
            risk_level=risk_level,
            status=status,
            action=None,
            generated_from=None,
            generated_to=None,
            search=None,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_recommendation_for_user(
        self,
        *,
        user_id: UUID,
        recommendation_id: UUID,
    ) -> dict[str, Any] | None:
        result = await self.session.execute(
            self._recommendation_select().where(
                ReorderRecommendationModel.id == recommendation_id,
                ReorderRecommendationModel.user_id == user_id,
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return self._row_to_recommendation_dict(row)

    async def get_recommendation_model_for_user(
        self,
        *,
        user_id: UUID,
        recommendation_id: UUID,
    ) -> ReorderRecommendationModel | None:
        result = await self.session.execute(
            select(ReorderRecommendationModel)
            .options(selectinload(ReorderRecommendationModel.product))
            .where(
                ReorderRecommendationModel.id == recommendation_id,
                ReorderRecommendationModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_summary_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> dict[str, Any] | None:
        filters = [
            ReorderRecommendationModel.user_id == user_id,
            ReorderRecommendationModel.forecast_run_id == forecast_run_id,
        ]
        aggregate_result = await self.session.execute(
            select(
                func.count(ReorderRecommendationModel.id),
                func.coalesce(func.sum(ReorderRecommendationModel.reorder_quantity), 0),
                func.coalesce(func.sum(ReorderRecommendationModel.predicted_demand), 0),
                func.coalesce(func.sum(ReorderRecommendationModel.current_stock), 0),
                func.max(ReorderRecommendationModel.generated_at),
            ).where(*filters)
        )
        (
            total_recommendations,
            total_reorder_quantity,
            total_predicted_demand,
            total_current_stock,
            latest_generated_at,
        ) = aggregate_result.one()
        if int(total_recommendations) == 0:
            return None

        counts_result = await self.session.execute(
            select(
                ReorderRecommendationModel.risk_level,
                func.count(ReorderRecommendationModel.id),
            )
            .where(*filters)
            .group_by(ReorderRecommendationModel.risk_level)
        )
        counts = {row[0]: int(row[1]) for row in counts_result.all()}

        top_result = await self.session.execute(
            self._recommendation_select()
            .where(*filters)
            .order_by(
                desc(ReorderRecommendationModel.reorder_quantity),
                desc(ReorderRecommendationModel.predicted_demand),
            )
            .limit(5)
        )
        return {
            "forecast_run_id": forecast_run_id,
            "total_recommendations": int(total_recommendations),
            "total_reorder_quantity": Decimal(str(total_reorder_quantity)),
            "critical_count": counts.get("critical", 0),
            "high_count": counts.get("high", 0),
            "medium_count": counts.get("medium", 0),
            "low_count": counts.get("low", 0),
            "overstocked_count": counts.get("overstocked", 0),
            "total_predicted_demand": Decimal(str(total_predicted_demand)),
            "total_current_stock": Decimal(str(total_current_stock)),
            "latest_generated_at": latest_generated_at,
            "top_reorder_products": [
                self._row_to_recommendation_dict(row) for row in top_result.all()
            ],
        }

    async def update_recommendation_status(
        self,
        recommendation: ReorderRecommendationModel,
        *,
        status: str,
        acknowledged_at: datetime | None,
        dismissed_at: datetime | None,
    ) -> ReorderRecommendationModel:
        recommendation.status = status
        if acknowledged_at is not None:
            recommendation.acknowledged_at = acknowledged_at
        if dismissed_at is not None:
            recommendation.dismissed_at = dismissed_at
        recommendation.updated_at = utc_now()
        await self.session.flush()
        return recommendation

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    def _recommendation_filters(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        product_id: UUID | None,
        category_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        action: str | None,
        generated_from: datetime | None,
        generated_to: datetime | None,
        search: str | None,
    ) -> list[Any]:
        filters = [
            ReorderRecommendationModel.user_id == user_id,
            ProductModel.user_id == user_id,
        ]
        if forecast_run_id is not None:
            filters.append(
                ReorderRecommendationModel.forecast_run_id == forecast_run_id
            )
        if product_id is not None:
            filters.append(ReorderRecommendationModel.product_id == product_id)
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        if risk_level is not None:
            filters.append(ReorderRecommendationModel.risk_level == risk_level)
        if status is not None:
            filters.append(ReorderRecommendationModel.status == status)
        if action is not None:
            filters.append(ReorderRecommendationModel.recommended_action == action)
        if generated_from is not None:
            filters.append(ReorderRecommendationModel.generated_at >= generated_from)
        if generated_to is not None:
            filters.append(ReorderRecommendationModel.generated_at <= generated_to)
        if search:
            search_value = search.strip()
            if search_value:
                filters.append(
                    or_(
                        ProductModel.name.ilike(f"%{search_value}%"),
                        ProductModel.normalized_sku.ilike(
                            f"%{search_value.upper()}%"
                        ),
                        ReorderRecommendationModel.risk_level.ilike(
                            f"%{search_value}%"
                        ),
                        ReorderRecommendationModel.recommended_action.ilike(
                            f"%{search_value}%"
                        ),
                    )
                )
        return filters

    def _recommendation_select(self) -> Any:
        return (
            select(
                ReorderRecommendationModel,
                ProductModel.name.label("product_name"),
                ProductModel.sku,
                ProductModel.category_id,
                ProductCategoryModel.name.label("category_name"),
                ProductModel.unit,
                ForecastRunModel.horizon_days,
                ForecastRunModel.status.label("forecast_run_status"),
                ForecastRunModel.requested_at,
                ForecastRunModel.completed_at,
            )
            .join(
                ProductModel,
                ProductModel.id == ReorderRecommendationModel.product_id,
            )
            .join(
                ForecastRunModel,
                ForecastRunModel.id == ReorderRecommendationModel.forecast_run_id,
            )
            .outerjoin(
                ProductCategoryModel,
                ProductCategoryModel.id == ProductModel.category_id,
            )
        )

    def _row_to_recommendation_dict(self, row: Any) -> dict[str, Any]:
        recommendation = row[0]
        return {
            "id": recommendation.id,
            "forecast_run_id": recommendation.forecast_run_id,
            "product_id": recommendation.product_id,
            "product_name": row.product_name,
            "sku": row.sku,
            "category_id": row.category_id,
            "category_name": row.category_name,
            "unit": row.unit,
            "predicted_demand": recommendation.predicted_demand,
            "current_stock": recommendation.current_stock,
            "minimum_stock": recommendation.minimum_stock,
            "safety_stock": recommendation.safety_stock,
            "required_stock": recommendation.required_stock,
            "reorder_quantity": recommendation.reorder_quantity,
            "stock_gap": recommendation.stock_gap,
            "risk_level": recommendation.risk_level,
            "recommended_action": recommendation.recommended_action,
            "reason": recommendation.reason,
            "status": recommendation.status,
            "generated_at": recommendation.generated_at,
            "acknowledged_at": recommendation.acknowledged_at,
            "dismissed_at": recommendation.dismissed_at,
            "created_at": recommendation.created_at,
            "updated_at": recommendation.updated_at,
            "forecast_run": {
                "id": recommendation.forecast_run_id,
                "horizon_days": row.horizon_days,
                "status": row.forecast_run_status,
                "requested_at": row.requested_at,
                "completed_at": row.completed_at,
            },
        }
