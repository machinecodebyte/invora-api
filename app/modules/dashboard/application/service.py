from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.dashboard.domain.exceptions import (
    DashboardAggregationFailedError,
    DashboardCategoryNotFoundError,
    DashboardForecastRunNotFoundError,
    DashboardProductNotFoundError,
)
from app.modules.dashboard.domain.validators import (
    normalize_dashboard_interval,
    resolve_dashboard_date_range,
    validate_dashboard_limit,
    validate_dashboard_recommendation_status,
    validate_dashboard_risk_level,
)

FORECAST_STATUSES = ("pending", "running", "completed", "failed", "cancelled")


class DashboardAnalyticsService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def get_summary(
        self,
        *,
        user_id: UUID,
        date_from: Any | None,
        date_to: Any | None,
        forecast_run_id: UUID | None,
    ) -> dict[str, Any]:
        date_range = resolve_dashboard_date_range(date_from, date_to)
        if forecast_run_id is not None:
            await self._ensure_forecast_run(
                user_id=user_id,
                forecast_run_id=forecast_run_id,
            )
        return await self._read(
            self._summary_payload,
            user_id=user_id,
            date_range=date_range,
            forecast_run_id=forecast_run_id,
        )

    async def get_kpis(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._read(self._kpi_payload, user_id=user_id)

    async def get_demand_trends(
        self,
        *,
        user_id: UUID,
        date_from: Any | None,
        date_to: Any | None,
        interval: str,
        product_id: UUID | None,
        category_id: UUID | None,
    ) -> dict[str, Any]:
        date_range = resolve_dashboard_date_range(date_from, date_to)
        normalized_interval = normalize_dashboard_interval(interval)
        if product_id is not None:
            await self._ensure_product(user_id=user_id, product_id=product_id)
        if category_id is not None:
            await self._ensure_category(user_id=user_id, category_id=category_id)
        return await self._read(
            self._demand_trend_payload,
            user_id=user_id,
            date_range=date_range,
            interval=normalized_interval,
            product_id=product_id,
            category_id=category_id,
        )

    async def get_inventory_risk(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> dict[str, Any]:
        limit = validate_dashboard_limit(limit, max_limit=50)
        return await self._read(
            self._inventory_risk_payload,
            user_id=user_id,
            limit=limit,
        )

    async def get_forecast_overview(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._read(self._forecast_overview_payload, user_id=user_id)

    async def get_reorder_alerts(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        limit: int,
    ) -> dict[str, Any]:
        limit = validate_dashboard_limit(limit, max_limit=50)
        risk_level = validate_dashboard_risk_level(risk_level)
        status = validate_dashboard_recommendation_status(status)
        if forecast_run_id is not None:
            await self._ensure_forecast_run(
                user_id=user_id,
                forecast_run_id=forecast_run_id,
            )
        return await self._read(
            self._reorder_alert_payload,
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            risk_level=risk_level,
            status=status,
            limit=limit,
        )

    async def get_recent_activity(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> dict[str, Any]:
        limit = validate_dashboard_limit(limit, max_limit=50)
        return await self._read(
            self._recent_activity_payload,
            user_id=user_id,
            limit=limit,
        )

    async def _summary_payload(
        self,
        *,
        user_id: UUID,
        date_range: Any,
        forecast_run_id: UUID | None,
    ) -> dict[str, Any]:
        return {
            "date_from": date_range.date_from,
            "date_to": date_range.date_to,
            "forecast_run_id": forecast_run_id,
            "kpis": await self._kpi_payload(user_id=user_id),
            "demand_trends": await self._demand_trend_payload(
                user_id=user_id,
                date_range=date_range,
                interval="day",
                product_id=None,
                category_id=None,
            ),
            "inventory_risk": await self._inventory_risk_payload(
                user_id=user_id,
                limit=5,
            ),
            "forecast_overview": await self._forecast_overview_payload(
                user_id=user_id,
            ),
            "reorder_alerts": await self._reorder_alert_payload(
                user_id=user_id,
                forecast_run_id=forecast_run_id,
                risk_level=None,
                status="open",
                limit=5,
            ),
            "recent_activity": await self._recent_activity_payload(
                user_id=user_id,
                limit=8,
            ),
        }

    async def _kpi_payload(self, *, user_id: UUID) -> dict[str, Any]:
        product_counts = await self.repository.get_product_counts_for_user(
            user_id=user_id,
        )
        sales_counts = await self.repository.get_sales_counts_for_user(
            user_id=user_id,
        )
        inventory_counts = await self.repository.get_inventory_counts_for_user(
            user_id=user_id,
        )
        forecast_counts = await self.repository.get_forecast_run_counts_for_user(
            user_id=user_id,
        )
        forecast_overview = await self.repository.get_latest_forecast_overview_for_user(
            user_id=user_id,
        )
        completed_run = forecast_overview["latest_completed_forecast_run"]
        metrics = await self.repository.get_latest_forecast_metrics_for_user(
            user_id=user_id,
            forecast_run_id=completed_run["id"] if completed_run else None,
        )
        reorder_counts = await self.repository.get_reorder_alert_counts_for_user(
            user_id=user_id,
            forecast_run_id=None,
        )
        return {
            **product_counts,
            "total_sales_records": sales_counts["total_sales_records"],
            "total_inventory_items": inventory_counts["total_inventory_items"],
            "low_stock_count": inventory_counts["low_stock_count"],
            "out_of_stock_count": inventory_counts["out_of_stock_count"],
            "total_forecast_runs": sum(forecast_counts.values()),
            "completed_forecast_runs": forecast_counts.get("completed", 0),
            "latest_forecast_mape": metrics["mape"] if metrics else None,
            "open_recommendations": reorder_counts["open_count"],
            "high_risk_recommendations": reorder_counts["high_count"],
            "critical_risk_recommendations": reorder_counts["critical_count"],
            "total_reorder_quantity": reorder_counts["total_reorder_quantity"],
        }

    async def _demand_trend_payload(
        self,
        *,
        user_id: UUID,
        date_range: Any,
        interval: str,
        product_id: UUID | None,
        category_id: UUID | None,
    ) -> dict[str, Any]:
        points = await self.repository.get_demand_trends_for_user(
            user_id=user_id,
            date_from=date_range.date_from,
            date_to=date_range.date_to,
            interval=interval,
            product_id=product_id,
            category_id=category_id,
        )
        return {
            "date_from": date_range.date_from,
            "date_to": date_range.date_to,
            "interval": interval,
            "product_id": product_id,
            "category_id": category_id,
            "points": points,
        }

    async def _inventory_risk_payload(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> dict[str, Any]:
        counts = await self.repository.get_inventory_counts_for_user(user_id=user_id)
        return {
            **counts,
            "low_stock_items": await self.repository.get_low_stock_preview_for_user(
                user_id=user_id,
                limit=limit,
            ),
            "out_of_stock_items": (
                await self.repository.get_out_of_stock_preview_for_user(
                    user_id=user_id,
                    limit=limit,
                )
            ),
        }

    async def _forecast_overview_payload(self, *, user_id: UUID) -> dict[str, Any]:
        overview = await self.repository.get_latest_forecast_overview_for_user(
            user_id=user_id,
        )
        latest_completed = overview["latest_completed_forecast_run"]
        run_id = latest_completed["id"] if latest_completed else None
        metrics = await self.repository.get_latest_forecast_metrics_for_user(
            user_id=user_id,
            forecast_run_id=run_id,
        )
        prediction_summary = await self.repository.get_prediction_summary_for_run(
            user_id=user_id,
            forecast_run_id=run_id,
        )
        counts = await self.repository.get_forecast_run_counts_for_user(
            user_id=user_id,
        )
        return {
            **overview,
            "forecast_run_counts_by_status": _forecast_status_counts(counts),
            "latest_metrics": metrics,
            **prediction_summary,
        }

    async def _reorder_alert_payload(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        limit: int,
    ) -> dict[str, Any]:
        counts = await self.repository.get_reorder_alert_counts_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        )
        top_items = await self.repository.get_top_reorder_items_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            risk_level=risk_level,
            status=status,
            limit=limit,
        )
        return {
            "forecast_run_id": forecast_run_id,
            "risk_level": risk_level,
            "status": status,
            **counts,
            "top_reorder_items": top_items,
        }

    async def _recent_activity_payload(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> dict[str, Any]:
        source_limit = max(limit, 10)
        events = []
        events.extend(
            _sales_upload_event(row)
            for row in await self.repository.get_recent_sales_uploads_for_user(
                user_id=user_id,
                limit=source_limit,
            )
        )
        events.extend(
            _forecast_run_event(row)
            for row in await self.repository.get_recent_forecast_runs_for_user(
                user_id=user_id,
                limit=source_limit,
            )
        )
        events.extend(
            _stock_movement_event(row)
            for row in await self.repository.get_recent_stock_movements_for_user(
                user_id=user_id,
                limit=source_limit,
            )
        )
        events.extend(
            _recommendation_event(row)
            for row in await self.repository.get_recent_recommendations_for_user(
                user_id=user_id,
                limit=source_limit,
            )
        )
        events.sort(key=lambda event: event["occurred_at"], reverse=True)
        return {"activities": events[:limit], "limit": limit}

    async def _ensure_product(self, *, user_id: UUID, product_id: UUID) -> None:
        if not await self.repository.validate_product_for_user(
            user_id=user_id,
            product_id=product_id,
        ):
            raise DashboardProductNotFoundError()

    async def _ensure_category(self, *, user_id: UUID, category_id: UUID) -> None:
        if not await self.repository.validate_category_for_user(
            user_id=user_id,
            category_id=category_id,
        ):
            raise DashboardCategoryNotFoundError()

    async def _ensure_forecast_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> None:
        if not await self.repository.validate_forecast_run_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        ):
            raise DashboardForecastRunNotFoundError()

    async def _read(self, method: Any, **kwargs: Any) -> Any:
        try:
            return await method(**kwargs)
        except AppError:
            raise
        except Exception as exc:
            raise DashboardAggregationFailedError() from exc


def _forecast_status_counts(counts: dict[str, int]) -> dict[str, int]:
    return {status: counts.get(status, 0) for status in FORECAST_STATUSES}


def _sales_upload_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": "sales_upload",
        "event_label": f"Sales upload {row['status']}: {row['filename']}",
        "entity_id": row["id"],
        "occurred_at": row["occurred_at"],
        "metadata": {
            "status": row["status"],
            "accepted_rows": row["accepted_rows"],
            "rejected_rows": row["rejected_rows"],
        },
    }


def _forecast_run_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": "forecast_run",
        "event_label": f"Forecast run {row['status']}",
        "entity_id": row["id"],
        "occurred_at": row["occurred_at"],
        "metadata": {
            "status": row["status"],
            "horizon_days": row["horizon_days"],
        },
    }


def _stock_movement_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": "stock_movement",
        "event_label": f"Stock movement {row['movement_type']} for {row['sku']}",
        "entity_id": row["id"],
        "occurred_at": row["occurred_at"],
        "metadata": {
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "sku": row["sku"],
            "movement_type": row["movement_type"],
            "quantity_delta": row["quantity_delta"],
        },
    }


def _recommendation_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": "reorder_recommendation",
        "event_label": f"{row['risk_level'].title()} reorder alert for {row['sku']}",
        "entity_id": row["id"],
        "occurred_at": row["occurred_at"],
        "metadata": {
            "forecast_run_id": row["forecast_run_id"],
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "sku": row["sku"],
            "risk_level": row["risk_level"],
            "reorder_quantity": row["reorder_quantity"],
            "status": row["status"],
        },
    }


def empty_dashboard_decimal() -> Decimal:
    return Decimal("0.000")
