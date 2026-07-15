from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.domain.defaults import default_settings_values
from app.modules.settings.domain.enums import SettingsCategory
from app.modules.settings.domain.exceptions import SettingsUpdateConflictError
from app.modules.settings.infrastructure.models import UserSystemSettingsModel
from app.shared.utils import utc_now


class SystemSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_settings_for_user(
        self,
        *,
        user_id: UUID,
    ) -> UserSystemSettingsModel | None:
        result = await self.session.execute(
            select(UserSystemSettingsModel).where(
                UserSystemSettingsModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_default_settings_for_user(
        self,
        *,
        user_id: UUID,
    ) -> UserSystemSettingsModel:
        settings = UserSystemSettingsModel(
            id=uuid4(),
            user_id=user_id,
            **default_settings_values(),
        )
        self.session.add(settings)
        await self.session.flush()
        return settings

    async def get_or_create_settings_for_user(
        self,
        *,
        user_id: UUID,
    ) -> UserSystemSettingsModel:
        existing = await self.get_settings_for_user(user_id=user_id)
        if existing is not None:
            return existing

        values = {
            "id": uuid4(),
            "user_id": user_id,
            **default_settings_values(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        statement = (
            insert(UserSystemSettingsModel)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["user_id"])
            .returning(UserSystemSettingsModel)
        )
        try:
            result = await self.session.execute(statement)
            created = result.scalar_one_or_none()
            if created is not None:
                await self.session.commit()
                return created
        except IntegrityError as exc:
            await self.session.rollback()
            existing = await self.get_settings_for_user(user_id=user_id)
            if existing is not None:
                return existing
            raise SettingsUpdateConflictError() from exc

        existing = await self.get_settings_for_user(user_id=user_id)
        if existing is not None:
            return existing
        raise SettingsUpdateConflictError()

    async def update_settings_for_user(
        self,
        settings: UserSystemSettingsModel,
        values: dict[str, Any],
    ) -> UserSystemSettingsModel:
        for field, value in values.items():
            setattr(settings, field, value)
        settings.updated_at = utc_now()
        await self.session.flush()
        return settings

    async def reset_settings_for_user(
        self,
        settings: UserSystemSettingsModel,
    ) -> UserSystemSettingsModel:
        return await self.update_settings_for_user(settings, default_settings_values())

    async def reset_settings_category_for_user(
        self,
        settings: UserSystemSettingsModel,
        category: SettingsCategory,
    ) -> UserSystemSettingsModel:
        defaults = default_settings_values()
        values = {field: defaults[field] for field in _category_model_fields(category)}
        return await self.update_settings_for_user(settings, values)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


def _category_model_fields(category: SettingsCategory) -> tuple[str, ...]:
    fields = {
        SettingsCategory.FORECAST: (
            "forecast_default_horizon_days",
            "forecast_min_history_days",
            "forecast_default_model",
            "forecast_auto_process_enabled",
        ),
        SettingsCategory.INVENTORY: (
            "inventory_default_minimum_stock",
            "inventory_default_safety_stock",
            "inventory_low_stock_alert_enabled",
        ),
        SettingsCategory.SALES_UPLOAD: (
            "sales_upload_duplicate_policy",
            "sales_upload_date_format",
        ),
        SettingsCategory.REPORTS: (
            "reports_default_format",
            "reports_include_inactive_products",
        ),
        SettingsCategory.DASHBOARD: ("dashboard_default_date_range_days",),
        SettingsCategory.BACKGROUND_JOBS: ("background_jobs_auto_retry_enabled",),
        SettingsCategory.LOCALIZATION: ("timezone", "locale"),
    }
    return fields[category]
