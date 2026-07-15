from __future__ import annotations

import asyncio
from copy import deepcopy
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.modules.settings.application.service import SystemSettingsService
from app.modules.settings.domain.defaults import default_settings_values
from app.modules.settings.domain.enums import SettingsCategory
from app.modules.settings.domain.exceptions import (
    InvalidSettingsCategoryError,
    InvalidSettingsValueError,
    LocaleInvalidError,
    ProtectedSettingsFieldError,
    TimezoneInvalidError,
    UnknownSettingsFieldError,
)
from app.modules.settings.domain.rules import (
    normalize_category_settings_update,
    normalize_system_settings_update,
    validate_reset_category,
)
from app.shared.utils import utc_now


class FakeSettingsRecord:
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        for field, value in default_settings_values().items():
            setattr(self, field, deepcopy(value))
        self.created_at = utc_now()
        self.updated_at = utc_now()


class FakeSettingsRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, FakeSettingsRecord] = {}
        self.created_count = 0

    async def get_or_create_settings_for_user(
        self,
        *,
        user_id: UUID,
    ) -> FakeSettingsRecord:
        record = self.records.get(user_id)
        if record is None:
            record = FakeSettingsRecord(user_id)
            self.records[user_id] = record
            self.created_count += 1
        return record

    async def update_settings_for_user(
        self,
        settings: FakeSettingsRecord,
        values: dict,
    ) -> FakeSettingsRecord:
        for field, value in values.items():
            setattr(settings, field, value)
        settings.updated_at = utc_now()
        return settings

    async def reset_settings_for_user(
        self,
        settings: FakeSettingsRecord,
    ) -> FakeSettingsRecord:
        return await self.update_settings_for_user(settings, default_settings_values())

    async def reset_settings_category_for_user(
        self,
        settings: FakeSettingsRecord,
        category: SettingsCategory,
    ) -> FakeSettingsRecord:
        defaults = default_settings_values()
        category_fields = {
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
        return await self.update_settings_for_user(
            settings,
            {field: defaults[field] for field in category_fields[category]},
        )

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def test_default_settings_are_complete_and_isolated() -> None:
    first = default_settings_values()
    second = default_settings_values()

    first["metadata_"] = {"view": "compact"}

    assert first["forecast_default_horizon_days"] == 30
    assert first["inventory_default_minimum_stock"] == Decimal("0.000")
    assert second["metadata_"] is None


@pytest.mark.parametrize("value", [7, 15, 30])
def test_forecast_horizon_validation_accepts_supported_values(value: int) -> None:
    assert normalize_system_settings_update(
        {"forecast_default_horizon_days": value}
    ) == {"forecast_default_horizon_days": value}


@pytest.mark.parametrize("value", [0, 14, 31, True, "30"])
def test_forecast_horizon_validation_rejects_unsupported_values(value) -> None:
    with pytest.raises(InvalidSettingsValueError):
        normalize_system_settings_update({"forecast_default_horizon_days": value})


@pytest.mark.parametrize("value", ["random_forest", "baseline"])
def test_forecast_model_validation(value: str) -> None:
    assert normalize_system_settings_update({"forecast_default_model": value}) == {
        "forecast_default_model": value
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("forecast_min_history_days", 0),
        ("forecast_min_history_days", 366),
        ("dashboard_default_date_range_days", 6),
        ("dashboard_default_date_range_days", 366),
    ],
)
def test_integer_setting_ranges_are_enforced(field: str, value: int) -> None:
    with pytest.raises(InvalidSettingsValueError):
        normalize_system_settings_update({field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("inventory_default_minimum_stock", "12.345"),
        ("inventory_default_safety_stock", 5),
    ],
)
def test_inventory_stock_defaults_are_normalized(field: str, value) -> None:
    normalized = normalize_system_settings_update({field: value})
    assert normalized[field] in {Decimal("12.345"), Decimal("5.000")}


@pytest.mark.parametrize(
    "field,value",
    [
        ("inventory_default_minimum_stock", "-0.001"),
        ("inventory_default_safety_stock", "1.0001"),
    ],
)
def test_inventory_stock_defaults_reject_negative_or_over_precise_values(
    field: str,
    value: str,
) -> None:
    with pytest.raises(InvalidSettingsValueError):
        normalize_system_settings_update({field: value})


@pytest.mark.parametrize(
    "field,value",
    [
        ("sales_upload_duplicate_policy", "mark_duplicate"),
        ("sales_upload_date_format", "dd-mm-yyyy"),
        ("reports_default_format", "csv"),
    ],
)
def test_enumerated_setting_values_are_accepted(field: str, value: str) -> None:
    assert normalize_system_settings_update({field: value}) == {field: value}


@pytest.mark.parametrize(
    "field,value",
    [
        ("sales_upload_duplicate_policy", "replace"),
        ("sales_upload_date_format", "yyyy/dd/mm"),
        ("reports_default_format", "pdf"),
    ],
)
def test_enumerated_setting_values_are_rejected(field: str, value: str) -> None:
    with pytest.raises(InvalidSettingsValueError):
        normalize_system_settings_update({field: value})


def test_locale_and_timezone_validation() -> None:
    normalized = normalize_system_settings_update(
        {"locale": "en-IN", "timezone": "Asia/Kolkata"}
    )

    assert normalized == {"locale": "en-IN", "timezone": "Asia/Kolkata"}
    with pytest.raises(LocaleInvalidError):
        normalize_system_settings_update({"locale": "fr"})
    with pytest.raises(TimezoneInvalidError):
        normalize_system_settings_update({"timezone": "Mars/Olympus"})


def test_protected_unknown_and_category_fields_are_rejected() -> None:
    with pytest.raises(ProtectedSettingsFieldError):
        normalize_system_settings_update({"DATABASE_URL": "postgresql://unsafe"})
    with pytest.raises(UnknownSettingsFieldError):
        normalize_system_settings_update({"theme": "dark"})
    with pytest.raises(UnknownSettingsFieldError):
        normalize_category_settings_update(
            SettingsCategory.FORECAST,
            {"dashboard_default_date_range_days": 30},
        )
    with pytest.raises(ProtectedSettingsFieldError):
        normalize_system_settings_update({"metadata": {"api_key": "unsafe"}})


def test_reset_category_validation() -> None:
    assert validate_reset_category("sales_upload") == SettingsCategory.SALES_UPLOAD
    assert validate_reset_category(None) is None
    with pytest.raises(InvalidSettingsCategoryError):
        validate_reset_category("all")


@pytest.mark.asyncio
async def test_reset_category_and_all_settings() -> None:
    repository = FakeSettingsRepository()
    service = SystemSettingsService(repository=repository)
    user_id = uuid4()

    await service.update_settings(
        user_id=user_id,
        values={
            "forecast_default_horizon_days": 7,
            "dashboard_default_date_range_days": 90,
            "metadata": {"layout": "compact"},
        },
    )
    category_reset, category = await service.reset_settings(
        user_id=user_id,
        category="forecast",
    )

    assert category == "forecast"
    assert category_reset.forecast_default_horizon_days == 30
    assert category_reset.dashboard_default_date_range_days == 90
    assert category_reset.metadata_ == {"layout": "compact"}

    all_reset, category = await service.reset_settings(user_id=user_id, category=None)
    assert category is None
    assert all_reset.dashboard_default_date_range_days == 30
    assert all_reset.metadata_ is None


@pytest.mark.asyncio
async def test_get_or_create_is_stable_for_concurrent_first_reads() -> None:
    repository = FakeSettingsRepository()
    service = SystemSettingsService(repository=repository)
    user_id = uuid4()

    records = await asyncio.gather(
        *(service.get_settings(user_id=user_id) for _ in range(10))
    )

    assert repository.created_count == 1
    assert len({id(record) for record in records}) == 1
