from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.reports.domain.exceptions import (
    ReportCategoryNotFoundError,
    ReportForecastRunNotFoundError,
    ReportGenerationFailedError,
    ReportProductNotFoundError,
)
from app.modules.reports.domain.validators import (
    ReportDateRange,
    report_options,
    resolve_default_report_date_range,
    validate_report_date_range,
    validate_report_recommendation_status,
    validate_report_risk_level,
    validate_report_stock_status,
)
from app.shared.utils import utc_now

REPORT_MODEL_PERFORMANCE = "Model Performance Report"
REPORT_INVENTORY_RISK = "Inventory Risk Report"
REPORT_REORDER_SUMMARY = "Reorder Summary Report"
REPORT_DEMAND_FORECAST = "Demand Forecast Report"
REPORT_SALES_SUMMARY = "Sales Summary Report"


class ReportsService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def get_model_performance_report(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        date_from: Any | None,
        date_to: Any | None,
    ) -> dict[str, Any]:
        date_range = validate_report_date_range(date_from, date_to)
        if forecast_run_id is not None:
            await self._ensure_forecast_run(
                user_id=user_id,
                forecast_run_id=forecast_run_id,
            )
        return await self._read(
            self._model_performance_payload,
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            date_range=date_range,
        )

    async def get_inventory_risk_report(
        self,
        *,
        user_id: UUID,
        category_id: UUID | None,
        stock_status: str | None,
    ) -> dict[str, Any]:
        normalized_status = validate_report_stock_status(stock_status)
        if category_id is not None:
            await self._ensure_category(user_id=user_id, category_id=category_id)
        return await self._read(
            self._inventory_risk_payload,
            user_id=user_id,
            category_id=category_id,
            stock_status=normalized_status,
        )

    async def get_reorder_summary_report(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
    ) -> dict[str, Any]:
        normalized_risk = validate_report_risk_level(risk_level)
        normalized_status = validate_report_recommendation_status(status)
        if forecast_run_id is not None:
            await self._ensure_forecast_run(
                user_id=user_id,
                forecast_run_id=forecast_run_id,
            )
        return await self._read(
            self._reorder_summary_payload,
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            risk_level=normalized_risk,
            status=normalized_status,
        )

    async def get_demand_forecast_report(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: Any | None,
        date_to: Any | None,
    ) -> dict[str, Any]:
        date_range = validate_report_date_range(date_from, date_to)
        run = await self._get_forecast_run(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        )
        if product_id is not None:
            await self._ensure_product(user_id=user_id, product_id=product_id)
        if category_id is not None:
            await self._ensure_category(user_id=user_id, category_id=category_id)
        return await self._read(
            self._demand_forecast_payload,
            user_id=user_id,
            forecast_run=run,
            product_id=product_id,
            category_id=category_id,
            date_range=date_range,
        )

    async def get_sales_summary_report(
        self,
        *,
        user_id: UUID,
        date_from: Any | None,
        date_to: Any | None,
        product_id: UUID | None,
        category_id: UUID | None,
        channel: str | None,
    ) -> dict[str, Any]:
        date_range = resolve_default_report_date_range(date_from, date_to)
        if product_id is not None:
            await self._ensure_product(user_id=user_id, product_id=product_id)
        if category_id is not None:
            await self._ensure_category(user_id=user_id, category_id=category_id)
        return await self._read(
            self._sales_summary_payload,
            user_id=user_id,
            date_range=date_range,
            product_id=product_id,
            category_id=category_id,
            channel=_normalize_channel(channel),
        )

    async def get_report_options(self) -> dict[str, Any]:
        return report_options()

    async def _model_performance_payload(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        date_range: ReportDateRange,
    ) -> dict[str, Any]:
        summary = await self.repository.get_model_performance_summary_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            date_from=date_range.date_from,
            date_to=date_range.date_to,
        )
        rows = await self.repository.get_model_performance_rows_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            date_from=date_range.date_from,
            date_to=date_range.date_to,
        )
        return {
            "report_name": REPORT_MODEL_PERFORMANCE,
            "generated_at": utc_now(),
            "date_range": _date_range_dict(date_range),
            **summary,
            "best_run_by_mape": _best_metric_row(rows),
            "latest_run_metrics": rows[0] if rows else None,
            "rows": rows,
        }

    async def _inventory_risk_payload(
        self,
        *,
        user_id: UUID,
        category_id: UUID | None,
        stock_status: str | None,
    ) -> dict[str, Any]:
        summary = await self.repository.get_inventory_risk_summary_for_user(
            user_id=user_id,
            category_id=category_id,
            stock_status=stock_status,
        )
        rows = await self.repository.get_inventory_risk_rows_for_user(
            user_id=user_id,
            category_id=category_id,
            stock_status=stock_status,
        )
        return {
            "report_name": REPORT_INVENTORY_RISK,
            "generated_at": utc_now(),
            "category_id": category_id,
            "stock_status": stock_status,
            **summary,
            "rows": rows,
        }

    async def _reorder_summary_payload(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
    ) -> dict[str, Any]:
        counts = await self.repository.get_reorder_summary_counts_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            risk_level=risk_level,
            status=status,
        )
        rows = await self.repository.get_reorder_summary_rows_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            risk_level=risk_level,
            status=status,
        )
        top_items = sorted(
            rows,
            key=lambda row: (row["reorder_quantity"], row["predicted_demand"]),
            reverse=True,
        )[:5]
        return {
            "report_name": REPORT_REORDER_SUMMARY,
            "generated_at": utc_now(),
            "forecast_run_id": forecast_run_id,
            "risk_level": risk_level,
            "status": status,
            **counts,
            "top_reorder_items": top_items,
            "rows": rows,
        }

    async def _demand_forecast_payload(
        self,
        *,
        user_id: UUID,
        forecast_run: Any,
        product_id: UUID | None,
        category_id: UUID | None,
        date_range: ReportDateRange,
    ) -> dict[str, Any]:
        rows = await self.repository.get_demand_forecast_rows_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run.id,
            product_id=product_id,
            category_id=category_id,
            date_from=date_range.date_from,
            date_to=date_range.date_to,
        )
        summary = await self.repository.get_demand_forecast_summary_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run.id,
            product_id=product_id,
            category_id=category_id,
            date_from=date_range.date_from,
            date_to=date_range.date_to,
        )
        return {
            "report_name": REPORT_DEMAND_FORECAST,
            "generated_at": utc_now(),
            "forecast_run_id": forecast_run.id,
            "horizon_days": forecast_run.horizon_days,
            **summary,
            "rows": rows,
        }

    async def _sales_summary_payload(
        self,
        *,
        user_id: UUID,
        date_range: ReportDateRange,
        product_id: UUID | None,
        category_id: UUID | None,
        channel: str | None,
    ) -> dict[str, Any]:
        totals = await self.repository.get_sales_summary_totals_for_user(
            user_id=user_id,
            date_from=date_range.date_from,
            date_to=date_range.date_to,
            product_id=product_id,
            category_id=category_id,
            channel=channel,
        )
        rows = await self.repository.get_sales_summary_rows_for_user(
            user_id=user_id,
            date_from=date_range.date_from,
            date_to=date_range.date_to,
            product_id=product_id,
            category_id=category_id,
            channel=channel,
        )
        return {
            "report_name": REPORT_SALES_SUMMARY,
            "generated_at": utc_now(),
            "date_range": _date_range_dict(date_range),
            "product_id": product_id,
            "category_id": category_id,
            "channel": channel,
            **totals,
            "rows": rows,
        }

    async def _ensure_product(self, *, user_id: UUID, product_id: UUID) -> None:
        if not await self.repository.validate_product_for_user(
            user_id=user_id,
            product_id=product_id,
        ):
            raise ReportProductNotFoundError()

    async def _ensure_category(self, *, user_id: UUID, category_id: UUID) -> None:
        if not await self.repository.validate_category_for_user(
            user_id=user_id,
            category_id=category_id,
        ):
            raise ReportCategoryNotFoundError()

    async def _ensure_forecast_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> None:
        await self._get_forecast_run(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        )

    async def _get_forecast_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> Any:
        run = await self.repository.validate_forecast_run_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        )
        if run is None:
            raise ReportForecastRunNotFoundError()
        return run

    async def _read(self, method: Any, **kwargs: Any) -> Any:
        try:
            return await method(**kwargs)
        except AppError:
            raise
        except Exception as exc:
            raise ReportGenerationFailedError() from exc


def _date_range_dict(date_range: ReportDateRange) -> dict[str, Any]:
    return {"date_from": date_range.date_from, "date_to": date_range.date_to}


def _best_metric_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    rows_with_mape = [row for row in rows if row["mape"] is not None]
    if not rows_with_mape:
        return None
    return min(rows_with_mape, key=lambda row: row["mape"])


def _normalize_channel(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


def average_decimal(total: Decimal, count: int, *, places: str = "0.001") -> Decimal:
    if count <= 0:
        return Decimal(places)
    return (total / Decimal(count)).quantize(Decimal(places))
