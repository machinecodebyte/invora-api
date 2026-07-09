from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.recommendations.domain.exceptions import (
    RecommendationForecastPredictionsNotFoundError,
    RecommendationForecastRunNotFoundError,
    RecommendationInventoryMissingError,
    RecommendationNotFoundError,
    RecommendationProductNotFoundError,
    RecommendationsNotGeneratedError,
)
from app.modules.recommendations.domain.reorder_policy import (
    calculate_reorder_quantity,
    calculate_required_stock,
    calculate_stock_gap,
    quantize_stock,
)
from app.modules.recommendations.domain.risk_engine import (
    calculate_risk_level,
    recommendation_reason,
    recommended_action_for_risk,
)
from app.modules.recommendations.domain.validators import (
    ensure_status_transition,
    normalize_recommendation_sort_field,
    normalize_recommendation_sort_order,
    validate_action,
    validate_completed_forecast_run,
    validate_recommendation_date_range,
    validate_regeneration_policy,
    validate_risk_level,
    validate_status,
)
from app.shared.utils import utc_now


class ReorderRecommendationService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def generate_for_forecast_run(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
        refresh: bool,
    ) -> dict[str, Any]:
        run = await self._get_forecast_run(user_id=user_id, run_id=run_id)
        validate_completed_forecast_run(run)

        prediction_count = await self.repository.count_predictions_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
        )
        if prediction_count == 0:
            raise RecommendationForecastPredictionsNotFoundError()

        existing_count = await self.repository.count_existing_recommendations_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
        )
        validate_regeneration_policy(
            existing_count=existing_count,
            refresh=refresh,
        )

        prediction_rows = (
            await self.repository.get_predictions_grouped_by_product_for_run(
                user_id=user_id,
                forecast_run_id=run.id,
            )
        )
        product_ids = {row["product_id"] for row in prediction_rows}
        inventory_by_product = await self.repository.get_inventory_items_for_products(
            user_id=user_id,
            product_ids=product_ids,
        )
        missing_inventory = product_ids - set(inventory_by_product)
        if missing_inventory:
            raise RecommendationInventoryMissingError()

        products_by_id = await self.repository.get_products_for_user_by_ids(
            user_id=user_id,
            product_ids=product_ids,
        )
        if product_ids - set(products_by_id):
            raise RecommendationProductNotFoundError()

        generated_at = utc_now()
        rows = [
            self._build_recommendation_row(
                forecast_run_id=run.id,
                prediction=row,
                inventory_item=inventory_by_product[row["product_id"]],
                generated_at=generated_at,
            )
            for row in prediction_rows
        ]

        try:
            if existing_count > 0:
                await self.repository.delete_recommendations_for_run(
                    user_id=user_id,
                    forecast_run_id=run.id,
                )
            recommendations = await self.repository.bulk_create_recommendations(
                user_id=user_id,
                rows=rows,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        except Exception:
            await self.repository.rollback()
            raise

        counts = self._risk_counts(rows)
        return {
            "forecast_run_id": run.id,
            "total_products": len(product_ids),
            "recommendations_created": len(recommendations),
            "refreshed": existing_count > 0,
            **counts,
        }

    async def list_recommendations(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        product_id: UUID | None,
        category_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        action: str | None,
        generated_from: Any | None,
        generated_to: Any | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        validate_recommendation_date_range(generated_from, generated_to)
        rows, total = await self.repository.list_recommendations_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=category_id,
            risk_level=validate_risk_level(risk_level),
            status=validate_status(status),
            action=validate_action(action),
            generated_from=generated_from,
            generated_to=generated_to,
            search=search,
            limit=limit,
            offset=offset,
            sort_by=normalize_recommendation_sort_field(sort_by),
            sort_order=normalize_recommendation_sort_order(sort_order),
        )
        return {
            "recommendations": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def list_for_forecast_run(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
        product_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> dict[str, Any]:
        run = await self._get_forecast_run(user_id=user_id, run_id=run_id)
        rows, total = await self.repository.list_recommendations_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
            product_id=product_id,
            risk_level=validate_risk_level(risk_level),
            status=validate_status(status),
            limit=limit,
            offset=offset,
            sort_by=normalize_recommendation_sort_field(sort_by),
            sort_order=normalize_recommendation_sort_order(sort_order),
        )
        if total == 0:
            raise RecommendationsNotGeneratedError()
        return {
            "forecast_run_id": run.id,
            "recommendations": rows,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def get_recommendation(
        self,
        *,
        user_id: UUID,
        recommendation_id: UUID,
    ) -> dict[str, Any]:
        recommendation = await self.repository.get_recommendation_for_user(
            user_id=user_id,
            recommendation_id=recommendation_id,
        )
        if recommendation is None:
            raise RecommendationNotFoundError()
        return recommendation

    async def get_summary_for_forecast_run(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> dict[str, Any]:
        run = await self._get_forecast_run(user_id=user_id, run_id=run_id)
        summary = await self.repository.get_summary_for_run(
            user_id=user_id,
            forecast_run_id=run.id,
        )
        if summary is None:
            raise RecommendationsNotGeneratedError()
        return summary

    async def update_status(
        self,
        *,
        user_id: UUID,
        recommendation_id: UUID,
        status: str,
    ) -> dict[str, Any]:
        recommendation = await self.repository.get_recommendation_model_for_user(
            user_id=user_id,
            recommendation_id=recommendation_id,
        )
        if recommendation is None:
            raise RecommendationNotFoundError()

        target_status = ensure_status_transition(recommendation.status, status)
        now = utc_now()
        acknowledged_at = (
            recommendation.acknowledged_at
            if recommendation.acknowledged_at is not None
            else now if target_status == "acknowledged" else None
        )
        dismissed_at = (
            recommendation.dismissed_at
            if recommendation.dismissed_at is not None
            else now if target_status == "dismissed" else None
        )

        try:
            await self.repository.update_recommendation_status(
                recommendation,
                status=target_status,
                acknowledged_at=acknowledged_at,
                dismissed_at=dismissed_at,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        except Exception:
            await self.repository.rollback()
            raise

        updated = await self.repository.get_recommendation_for_user(
            user_id=user_id,
            recommendation_id=recommendation_id,
        )
        if updated is None:
            raise RecommendationNotFoundError()
        return updated

    async def _get_forecast_run(self, *, user_id: UUID, run_id: UUID) -> Any:
        run = await self.repository.get_forecast_run_for_user(
            user_id=user_id,
            run_id=run_id,
        )
        if run is None:
            raise RecommendationForecastRunNotFoundError()
        return run

    def _build_recommendation_row(
        self,
        *,
        forecast_run_id: UUID,
        prediction: dict[str, Any],
        inventory_item: Any,
        generated_at: Any,
    ) -> dict[str, Any]:
        predicted_demand = quantize_stock(_to_decimal(prediction["predicted_demand"]))
        current_stock = quantize_stock(_to_decimal(inventory_item.current_stock))
        minimum_stock = quantize_stock(_to_decimal(inventory_item.minimum_stock))
        safety_stock = quantize_stock(_to_decimal(inventory_item.safety_stock))
        required_stock = calculate_required_stock(
            predicted_demand=predicted_demand,
            safety_stock=safety_stock,
        )
        stock_gap = calculate_stock_gap(
            required_stock=required_stock,
            current_stock=current_stock,
        )
        reorder_quantity = calculate_reorder_quantity(stock_gap=stock_gap)
        risk_level = calculate_risk_level(
            predicted_demand=predicted_demand,
            current_stock=current_stock,
            required_stock=required_stock,
            reorder_quantity=reorder_quantity,
        )
        action = recommended_action_for_risk(risk_level)
        return {
            "forecast_run_id": forecast_run_id,
            "product_id": prediction["product_id"],
            "predicted_demand": predicted_demand,
            "current_stock": current_stock,
            "minimum_stock": minimum_stock,
            "safety_stock": safety_stock,
            "required_stock": required_stock,
            "reorder_quantity": reorder_quantity,
            "stock_gap": stock_gap,
            "risk_level": risk_level,
            "recommended_action": action,
            "reason": recommendation_reason(
                risk_level=risk_level,
                predicted_demand=predicted_demand,
                current_stock=current_stock,
                required_stock=required_stock,
                reorder_quantity=reorder_quantity,
            ),
            "status": "open",
            "generated_at": generated_at,
        }

    def _risk_counts(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        return {
            "critical_count": sum(1 for row in rows if row["risk_level"] == "critical"),
            "high_count": sum(1 for row in rows if row["risk_level"] == "high"),
            "medium_count": sum(1 for row in rows if row["risk_level"] == "medium"),
            "low_count": sum(1 for row in rows if row["risk_level"] == "low"),
            "overstocked_count": sum(
                1 for row in rows if row["risk_level"] == "overstocked"
            ),
        }


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
