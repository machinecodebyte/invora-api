from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.modules.settings.domain.defaults import (
    ALL_SAFE_SETTINGS_FIELDS,
    CATEGORY_FIELDS,
)
from app.modules.settings.domain.enums import (
    ForecastHorizon,
    ForecastModel,
    LocaleOption,
    ReportDefaultFormat,
    SalesUploadDateFormat,
    SalesUploadDuplicatePolicy,
    SettingsCategory,
)
from app.modules.settings.domain.exceptions import (
    InvalidSettingsCategoryError,
    InvalidSettingsValueError,
    LocaleInvalidError,
    ProtectedSettingsFieldError,
    TimezoneInvalidError,
    UnknownSettingsFieldError,
)

PROTECTED_FIELDS = frozenset(
    {
        "id",
        "user_id",
        "created_at",
        "updated_at",
        "jwt_secret_key",
        "database_url",
        "redis_url",
        "smtp_credentials",
        "smtp_password",
        "api_key",
        "api_keys",
        "docker_ports",
        "cors_origins",
        "log_level",
        "debug",
        "database_pool_settings",
        "worker_internals",
    }
)
PROTECTED_METADATA_TERMS = frozenset(
    {
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "database",
        "password",
        "redis",
        "secret",
        "smtp",
        "token",
    }
)
MAX_STOCK_DEFAULT = Decimal("99999999999.999")
STOCK_QUANTUM = Decimal("0.001")


def normalize_system_settings_update(values: dict[str, Any]) -> dict[str, Any]:
    _validate_fields(values, allowed_fields=ALL_SAFE_SETTINGS_FIELDS)
    if not values:
        raise InvalidSettingsValueError("settings")
    return _normalize_values(values)


def normalize_category_settings_update(
    category: SettingsCategory,
    values: dict[str, Any],
) -> dict[str, Any]:
    _validate_fields(values, allowed_fields=frozenset(CATEGORY_FIELDS[category.value]))
    if not values:
        raise InvalidSettingsValueError(category.value)
    return _normalize_values(values)


def validate_reset_category(value: Any) -> SettingsCategory | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidSettingsCategoryError()
    try:
        return SettingsCategory(value.strip().lower())
    except ValueError as exc:
        raise InvalidSettingsCategoryError() from exc


def validate_reset_request_fields(values: dict[str, Any]) -> None:
    _validate_fields(values, allowed_fields=frozenset({"category"}))


def _validate_fields(values: dict[str, Any], *, allowed_fields: frozenset[str]) -> None:
    for field in values:
        normalized_field = field.lower()
        if normalized_field in PROTECTED_FIELDS:
            raise ProtectedSettingsFieldError(field)
        if field not in allowed_fields:
            raise UnknownSettingsFieldError(field)


def _normalize_values(values: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field, value in values.items():
        if field == "forecast_default_horizon_days":
            normalized[field] = _validate_forecast_horizon(value)
        elif field == "forecast_min_history_days":
            normalized[field] = _validate_int_range(
                field,
                value,
                minimum=1,
                maximum=365,
            )
        elif field == "forecast_default_model":
            normalized[field] = _validate_enum_value(field, value, ForecastModel)
        elif field == "forecast_auto_process_enabled":
            normalized[field] = _validate_boolean(field, value)
        elif field in {
            "inventory_default_minimum_stock",
            "inventory_default_safety_stock",
        }:
            normalized[field] = _validate_stock_default(field, value)
        elif field == "inventory_low_stock_alert_enabled":
            normalized[field] = _validate_boolean(field, value)
        elif field == "sales_upload_duplicate_policy":
            normalized[field] = _validate_enum_value(
                field,
                value,
                SalesUploadDuplicatePolicy,
            )
        elif field == "sales_upload_date_format":
            normalized[field] = _validate_enum_value(
                field,
                value,
                SalesUploadDateFormat,
            )
        elif field == "reports_default_format":
            normalized[field] = _validate_enum_value(
                field,
                value,
                ReportDefaultFormat,
            )
        elif field == "reports_include_inactive_products":
            normalized[field] = _validate_boolean(field, value)
        elif field == "dashboard_default_date_range_days":
            normalized[field] = _validate_int_range(
                field,
                value,
                minimum=7,
                maximum=365,
            )
        elif field == "background_jobs_auto_retry_enabled":
            normalized[field] = _validate_boolean(field, value)
        elif field == "timezone":
            normalized[field] = _validate_timezone(value)
        elif field == "locale":
            normalized[field] = _validate_locale(value)
        elif field == "metadata":
            normalized["metadata_"] = _validate_metadata(value)
        else:
            raise UnknownSettingsFieldError(field)
    return normalized


def _validate_forecast_horizon(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidSettingsValueError("forecast_default_horizon_days")
    if value not in {int(option) for option in ForecastHorizon}:
        raise InvalidSettingsValueError("forecast_default_horizon_days")
    return value


def _validate_int_range(
    field: str,
    value: Any,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidSettingsValueError(field)
    if not minimum <= value <= maximum:
        raise InvalidSettingsValueError(field)
    return value


def _validate_enum_value(field: str, value: Any, enum_type: type) -> str:
    if not isinstance(value, str):
        raise InvalidSettingsValueError(field)
    normalized = value.strip()
    if normalized not in {option.value for option in enum_type}:
        raise InvalidSettingsValueError(field)
    return normalized


def _validate_boolean(field: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise InvalidSettingsValueError(field)
    return value


def _validate_stock_default(field: str, value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise InvalidSettingsValueError(field)
    try:
        numeric_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidSettingsValueError(field) from exc
    if (
        not numeric_value.is_finite()
        or not Decimal("0") <= numeric_value <= MAX_STOCK_DEFAULT
    ):
        raise InvalidSettingsValueError(field)
    if numeric_value.as_tuple().exponent < -3:
        raise InvalidSettingsValueError(field)
    return numeric_value.quantize(STOCK_QUANTUM)


def _validate_timezone(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 64:
        raise TimezoneInvalidError()
    normalized = value.strip()
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as exc:
        raise TimezoneInvalidError() from exc
    return normalized


def _validate_locale(value: Any) -> str:
    if not isinstance(value, str):
        raise LocaleInvalidError()
    normalized = value.strip()
    if normalized not in {option.value for option in LocaleOption}:
        raise LocaleInvalidError()
    return normalized


def _validate_metadata(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or len(value) > 50:
        raise InvalidSettingsValueError("metadata")
    normalized = _validate_metadata_value(value, depth=0)
    try:
        encoded = json.dumps(normalized, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise InvalidSettingsValueError("metadata") from exc
    if len(encoded) > 10_000:
        raise InvalidSettingsValueError("metadata")
    return normalized


def _validate_metadata_value(value: Any, *, depth: int) -> Any:
    if depth > 4:
        raise InvalidSettingsValueError("metadata")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidSettingsValueError("metadata")
        return value
    if isinstance(value, list):
        if len(value) > 50:
            raise InvalidSettingsValueError("metadata")
        return [_validate_metadata_value(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > 50:
            raise InvalidSettingsValueError("metadata")
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key.strip() or len(key) > 64:
                raise InvalidSettingsValueError("metadata")
            if _metadata_key_is_protected(key):
                raise ProtectedSettingsFieldError("metadata")
            normalized[key.strip()] = _validate_metadata_value(item, depth=depth + 1)
        return normalized
    raise InvalidSettingsValueError("metadata")


def _metadata_key_is_protected(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    if normalized in PROTECTED_FIELDS or normalized in PROTECTED_METADATA_TERMS:
        return True
    return any(term in normalized.split("_") for term in PROTECTED_METADATA_TERMS)
