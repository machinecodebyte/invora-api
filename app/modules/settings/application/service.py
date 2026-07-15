from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.settings.domain.defaults import CATEGORY_FIELDS, settings_options
from app.modules.settings.domain.enums import SettingsCategory
from app.modules.settings.domain.rules import (
    normalize_category_settings_update,
    normalize_system_settings_update,
    validate_reset_category,
)


class SystemSettingsService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def get_settings(self, *, user_id: UUID) -> Any:
        return await self.get_or_create_settings_for_user(user_id=user_id)

    async def update_settings(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        return await self._update(
            user_id=user_id,
            values=normalize_system_settings_update(values),
        )

    async def reset_settings(
        self,
        *,
        user_id: UUID,
        category: Any | None,
    ) -> tuple[Any, str | None]:
        normalized_category = validate_reset_category(category)
        settings = await self.get_or_create_settings_for_user(user_id=user_id)
        try:
            if normalized_category is None:
                settings = await self.repository.reset_settings_for_user(settings)
            else:
                settings = await self.repository.reset_settings_category_for_user(
                    settings,
                    normalized_category,
                )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return settings, (
            normalized_category.value if normalized_category is not None else None
        )

    async def get_forecast_settings(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._get_category(
            user_id=user_id,
            category=SettingsCategory.FORECAST,
        )

    async def update_forecast_settings(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._update_category(
            user_id=user_id,
            category=SettingsCategory.FORECAST,
            values=values,
        )

    async def get_inventory_settings(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._get_category(
            user_id=user_id,
            category=SettingsCategory.INVENTORY,
        )

    async def update_inventory_settings(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._update_category(
            user_id=user_id,
            category=SettingsCategory.INVENTORY,
            values=values,
        )

    async def get_sales_upload_settings(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._get_category(
            user_id=user_id,
            category=SettingsCategory.SALES_UPLOAD,
        )

    async def update_sales_upload_settings(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._update_category(
            user_id=user_id,
            category=SettingsCategory.SALES_UPLOAD,
            values=values,
        )

    async def get_reports_settings(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._get_category(
            user_id=user_id,
            category=SettingsCategory.REPORTS,
        )

    async def update_reports_settings(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._update_category(
            user_id=user_id,
            category=SettingsCategory.REPORTS,
            values=values,
        )

    async def get_dashboard_settings(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._get_category(
            user_id=user_id,
            category=SettingsCategory.DASHBOARD,
        )

    async def update_dashboard_settings(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._update_category(
            user_id=user_id,
            category=SettingsCategory.DASHBOARD,
            values=values,
        )

    async def get_background_jobs_settings(self, *, user_id: UUID) -> dict[str, Any]:
        return await self._get_category(
            user_id=user_id,
            category=SettingsCategory.BACKGROUND_JOBS,
        )

    async def update_background_jobs_settings(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._update_category(
            user_id=user_id,
            category=SettingsCategory.BACKGROUND_JOBS,
            values=values,
        )

    async def get_options(self) -> dict[str, Any]:
        return settings_options()

    async def get_or_create_settings_for_user(self, *, user_id: UUID) -> Any:
        return await self.repository.get_or_create_settings_for_user(user_id=user_id)

    async def _update(self, *, user_id: UUID, values: dict[str, Any]) -> Any:
        settings = await self.get_or_create_settings_for_user(user_id=user_id)
        try:
            settings = await self.repository.update_settings_for_user(settings, values)
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return settings

    async def _get_category(
        self,
        *,
        user_id: UUID,
        category: SettingsCategory,
    ) -> dict[str, Any]:
        settings = await self.get_or_create_settings_for_user(user_id=user_id)
        return _category_payload(settings, category)

    async def _update_category(
        self,
        *,
        user_id: UUID,
        category: SettingsCategory,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        settings = await self._update(
            user_id=user_id,
            values=normalize_category_settings_update(category, values),
        )
        return _category_payload(settings, category)


def settings_payload(settings: Any) -> dict[str, Any]:
    return {
        "forecast_default_horizon_days": settings.forecast_default_horizon_days,
        "forecast_min_history_days": settings.forecast_min_history_days,
        "forecast_default_model": settings.forecast_default_model,
        "forecast_auto_process_enabled": settings.forecast_auto_process_enabled,
        "inventory_default_minimum_stock": settings.inventory_default_minimum_stock,
        "inventory_default_safety_stock": settings.inventory_default_safety_stock,
        "inventory_low_stock_alert_enabled": settings.inventory_low_stock_alert_enabled,
        "sales_upload_duplicate_policy": settings.sales_upload_duplicate_policy,
        "sales_upload_date_format": settings.sales_upload_date_format,
        "reports_default_format": settings.reports_default_format,
        "reports_include_inactive_products": settings.reports_include_inactive_products,
        "dashboard_default_date_range_days": settings.dashboard_default_date_range_days,
        "background_jobs_auto_retry_enabled": (
            settings.background_jobs_auto_retry_enabled
        ),
        "timezone": settings.timezone,
        "locale": settings.locale,
        "metadata": settings.metadata_,
        "created_at": settings.created_at,
        "updated_at": settings.updated_at,
    }


def _category_payload(settings: Any, category: SettingsCategory) -> dict[str, Any]:
    return {
        field: getattr(settings, field) for field in CATEGORY_FIELDS[category.value]
    }
