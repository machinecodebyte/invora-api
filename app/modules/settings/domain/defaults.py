from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

from app.modules.settings.domain.entities import SettingsCategoryDefinition
from app.modules.settings.domain.enums import (
    ForecastHorizon,
    ForecastModel,
    LocaleOption,
    ReportDefaultFormat,
    SalesUploadDateFormat,
    SalesUploadDuplicatePolicy,
    SettingsCategory,
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "forecast_default_horizon_days": 30,
    "forecast_min_history_days": 7,
    "forecast_default_model": ForecastModel.RANDOM_FOREST.value,
    "forecast_auto_process_enabled": False,
    "inventory_default_minimum_stock": Decimal("0.000"),
    "inventory_default_safety_stock": Decimal("0.000"),
    "inventory_low_stock_alert_enabled": True,
    "sales_upload_duplicate_policy": SalesUploadDuplicatePolicy.REJECT.value,
    "sales_upload_date_format": SalesUploadDateFormat.YYYY_MM_DD.value,
    "reports_default_format": ReportDefaultFormat.JSON.value,
    "reports_include_inactive_products": False,
    "dashboard_default_date_range_days": 30,
    "background_jobs_auto_retry_enabled": True,
    "timezone": "UTC",
    "locale": LocaleOption.EN.value,
    "metadata_": None,
}

SETTINGS_CATEGORY_DEFINITIONS = (
    SettingsCategoryDefinition(
        category=SettingsCategory.FORECAST,
        fields=(
            "forecast_default_horizon_days",
            "forecast_min_history_days",
            "forecast_default_model",
            "forecast_auto_process_enabled",
        ),
    ),
    SettingsCategoryDefinition(
        category=SettingsCategory.INVENTORY,
        fields=(
            "inventory_default_minimum_stock",
            "inventory_default_safety_stock",
            "inventory_low_stock_alert_enabled",
        ),
    ),
    SettingsCategoryDefinition(
        category=SettingsCategory.SALES_UPLOAD,
        fields=(
            "sales_upload_duplicate_policy",
            "sales_upload_date_format",
        ),
    ),
    SettingsCategoryDefinition(
        category=SettingsCategory.REPORTS,
        fields=(
            "reports_default_format",
            "reports_include_inactive_products",
        ),
    ),
    SettingsCategoryDefinition(
        category=SettingsCategory.DASHBOARD,
        fields=("dashboard_default_date_range_days",),
    ),
    SettingsCategoryDefinition(
        category=SettingsCategory.BACKGROUND_JOBS,
        fields=("background_jobs_auto_retry_enabled",),
    ),
    SettingsCategoryDefinition(
        category=SettingsCategory.LOCALIZATION,
        fields=("timezone", "locale"),
    ),
)

CATEGORY_FIELDS = {
    definition.category.value: definition.fields
    for definition in SETTINGS_CATEGORY_DEFINITIONS
}
ALL_SAFE_SETTINGS_FIELDS = frozenset(
    field for fields in CATEGORY_FIELDS.values() for field in fields
) | {"metadata"}


def default_settings_values() -> dict[str, Any]:
    return deepcopy(DEFAULT_SETTINGS)


def settings_options() -> dict[str, Any]:
    return {
        "forecast_horizons": tuple(int(value) for value in ForecastHorizon),
        "forecast_models": tuple(value.value for value in ForecastModel),
        "forecast_min_history_days": {"minimum": 1, "maximum": 365},
        "inventory_stock_minimum": Decimal("0.000"),
        "sales_upload_duplicate_policies": tuple(
            value.value for value in SalesUploadDuplicatePolicy
        ),
        "sales_upload_date_formats": tuple(
            value.value for value in SalesUploadDateFormat
        ),
        "reports_default_formats": tuple(value.value for value in ReportDefaultFormat),
        "dashboard_date_range_days": {"minimum": 7, "maximum": 365},
        "locales": tuple(value.value for value in LocaleOption),
        "reset_categories": tuple(value.value for value in SettingsCategory),
        "defaults": public_default_settings_values(),
    }


def public_default_settings_values() -> dict[str, Any]:
    values = default_settings_values()
    values["metadata"] = values.pop("metadata_")
    return values
