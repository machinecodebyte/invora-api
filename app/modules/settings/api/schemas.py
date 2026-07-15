from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

ForecastHorizonLiteral = Literal[7, 15, 30]
ForecastModelLiteral = Literal["random_forest", "baseline"]
SalesDuplicatePolicyLiteral = Literal["reject", "allow", "mark_duplicate"]
SalesDateFormatLiteral = Literal["yyyy-mm-dd", "dd-mm-yyyy", "mm-dd-yyyy"]
ReportsFormatLiteral = Literal["json", "csv"]
LocaleLiteral = Literal["en", "en-IN", "hi-IN"]
SettingsCategoryLiteral = Literal[
    "forecast",
    "inventory",
    "sales_upload",
    "reports",
    "dashboard",
    "background_jobs",
    "localization",
]


class _SettingsRequest(BaseModel):
    """Accept raw values so the domain layer can return consistent 400 errors."""

    model_config = ConfigDict(extra="allow")

    def update_values(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class SystemSettingsUpdateRequest(_SettingsRequest):
    forecast_default_horizon_days: Any | None = None
    forecast_min_history_days: Any | None = None
    forecast_default_model: Any | None = None
    forecast_auto_process_enabled: Any | None = None
    inventory_default_minimum_stock: Any | None = None
    inventory_default_safety_stock: Any | None = None
    inventory_low_stock_alert_enabled: Any | None = None
    sales_upload_duplicate_policy: Any | None = None
    sales_upload_date_format: Any | None = None
    reports_default_format: Any | None = None
    reports_include_inactive_products: Any | None = None
    dashboard_default_date_range_days: Any | None = None
    background_jobs_auto_retry_enabled: Any | None = None
    timezone: Any | None = None
    locale: Any | None = None
    metadata: Any | None = None


class ForecastSettingsUpdateRequest(_SettingsRequest):
    forecast_default_horizon_days: Any | None = None
    forecast_min_history_days: Any | None = None
    forecast_default_model: Any | None = None
    forecast_auto_process_enabled: Any | None = None


class InventorySettingsUpdateRequest(_SettingsRequest):
    inventory_default_minimum_stock: Any | None = None
    inventory_default_safety_stock: Any | None = None
    inventory_low_stock_alert_enabled: Any | None = None


class SalesUploadSettingsUpdateRequest(_SettingsRequest):
    sales_upload_duplicate_policy: Any | None = None
    sales_upload_date_format: Any | None = None


class ReportsSettingsUpdateRequest(_SettingsRequest):
    reports_default_format: Any | None = None
    reports_include_inactive_products: Any | None = None


class DashboardSettingsUpdateRequest(_SettingsRequest):
    dashboard_default_date_range_days: Any | None = None


class BackgroundJobsSettingsUpdateRequest(_SettingsRequest):
    background_jobs_auto_retry_enabled: Any | None = None


class SettingsResetRequest(_SettingsRequest):
    category: Any | None = None


class SystemSettingsPublic(BaseModel):
    forecast_default_horizon_days: ForecastHorizonLiteral
    forecast_min_history_days: int
    forecast_default_model: ForecastModelLiteral
    forecast_auto_process_enabled: bool
    inventory_default_minimum_stock: Decimal
    inventory_default_safety_stock: Decimal
    inventory_low_stock_alert_enabled: bool
    sales_upload_duplicate_policy: SalesDuplicatePolicyLiteral
    sales_upload_date_format: SalesDateFormatLiteral
    reports_default_format: ReportsFormatLiteral
    reports_include_inactive_products: bool
    dashboard_default_date_range_days: int
    background_jobs_auto_retry_enabled: bool
    timezone: str
    locale: LocaleLiteral
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class SystemSettingsResponse(BaseModel):
    success: Literal[True] = True
    data: SystemSettingsPublic


class ForecastSettingsResponseData(BaseModel):
    forecast_default_horizon_days: ForecastHorizonLiteral
    forecast_min_history_days: int
    forecast_default_model: ForecastModelLiteral
    forecast_auto_process_enabled: bool


class ForecastSettingsResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastSettingsResponseData


class InventorySettingsResponseData(BaseModel):
    inventory_default_minimum_stock: Decimal
    inventory_default_safety_stock: Decimal
    inventory_low_stock_alert_enabled: bool


class InventorySettingsResponse(BaseModel):
    success: Literal[True] = True
    data: InventorySettingsResponseData


class SalesUploadSettingsResponseData(BaseModel):
    sales_upload_duplicate_policy: SalesDuplicatePolicyLiteral
    sales_upload_date_format: SalesDateFormatLiteral


class SalesUploadSettingsResponse(BaseModel):
    success: Literal[True] = True
    data: SalesUploadSettingsResponseData


class ReportsSettingsResponseData(BaseModel):
    reports_default_format: ReportsFormatLiteral
    reports_include_inactive_products: bool


class ReportsSettingsResponse(BaseModel):
    success: Literal[True] = True
    data: ReportsSettingsResponseData


class DashboardSettingsResponseData(BaseModel):
    dashboard_default_date_range_days: int


class DashboardSettingsResponse(BaseModel):
    success: Literal[True] = True
    data: DashboardSettingsResponseData


class BackgroundJobsSettingsResponseData(BaseModel):
    background_jobs_auto_retry_enabled: bool


class BackgroundJobsSettingsResponse(BaseModel):
    success: Literal[True] = True
    data: BackgroundJobsSettingsResponseData


class SettingsDefaultsResponse(BaseModel):
    forecast_default_horizon_days: ForecastHorizonLiteral
    forecast_min_history_days: int
    forecast_default_model: ForecastModelLiteral
    forecast_auto_process_enabled: bool
    inventory_default_minimum_stock: Decimal
    inventory_default_safety_stock: Decimal
    inventory_low_stock_alert_enabled: bool
    sales_upload_duplicate_policy: SalesDuplicatePolicyLiteral
    sales_upload_date_format: SalesDateFormatLiteral
    reports_default_format: ReportsFormatLiteral
    reports_include_inactive_products: bool
    dashboard_default_date_range_days: int
    background_jobs_auto_retry_enabled: bool
    timezone: str
    locale: LocaleLiteral
    metadata: dict[str, Any] | None


class SettingsRangeResponse(BaseModel):
    minimum: int
    maximum: int


class SettingsOptionsData(BaseModel):
    forecast_horizons: tuple[ForecastHorizonLiteral, ...]
    forecast_models: tuple[ForecastModelLiteral, ...]
    forecast_min_history_days: SettingsRangeResponse
    inventory_stock_minimum: Decimal
    sales_upload_duplicate_policies: tuple[SalesDuplicatePolicyLiteral, ...]
    sales_upload_date_formats: tuple[SalesDateFormatLiteral, ...]
    reports_default_formats: tuple[ReportsFormatLiteral, ...]
    dashboard_date_range_days: SettingsRangeResponse
    locales: tuple[LocaleLiteral, ...]
    reset_categories: tuple[SettingsCategoryLiteral, ...]
    defaults: SettingsDefaultsResponse


class SettingsOptionsResponse(BaseModel):
    success: Literal[True] = True
    data: SettingsOptionsData


class SettingsResetData(BaseModel):
    settings: SystemSettingsPublic
    reset_category: SettingsCategoryLiteral | None


class SettingsResetResponse(BaseModel):
    success: Literal[True] = True
    data: SettingsResetData
