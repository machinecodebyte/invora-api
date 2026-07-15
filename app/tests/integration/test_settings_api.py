from __future__ import annotations

import asyncio
from copy import deepcopy
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.modules.settings.domain.defaults import default_settings_values
from app.modules.settings.domain.enums import SettingsCategory
from app.shared.utils import utc_now

OWNER_PAYLOAD = {
    "email": "settings-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Settings Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "settings-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Settings Owner",
}


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
        self.create_counts: dict[UUID, int] = {}

    async def get_or_create_settings_for_user(
        self,
        *,
        user_id: UUID,
    ) -> FakeSettingsRecord:
        record = self.records.get(user_id)
        if record is None:
            record = FakeSettingsRecord(user_id)
            self.records[user_id] = record
            self.create_counts[user_id] = self.create_counts.get(user_id, 0) + 1
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
        return await self.update_settings_for_user(
            settings,
            {field: defaults[field] for field in fields[category]},
        )

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
def settings_repository() -> FakeSettingsRepository:
    return FakeSettingsRepository()


@pytest.fixture
async def settings_client(
    app,
    auth_repository,
    settings_repository,
):
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.settings.api.dependencies import get_system_settings_service
    from app.modules.settings.application.service import SystemSettingsService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_settings_service() -> SystemSettingsService:
        return SystemSettingsService(repository=settings_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_system_settings_service] = override_settings_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


async def _register(client: AsyncClient, payload: dict = OWNER_PAYLOAD) -> str:
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()["data"]["tokens"]["access_token"]


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_settings_requires_authentication(settings_client: AsyncClient) -> None:
    response = await settings_client.get("/api/v1/settings")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_get_settings_creates_defaults_without_exposing_secrets(
    settings_client: AsyncClient,
    settings_repository: FakeSettingsRepository,
    auth_repository,
) -> None:
    access_token = await _register(settings_client)
    response = await settings_client.get(
        "/api/v1/settings",
        headers=_auth_headers(access_token),
    )
    user = auth_repository.users_by_email[OWNER_PAYLOAD["email"]]
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["forecast_default_horizon_days"] == 30
    assert data["inventory_default_minimum_stock"] == "0.000"
    assert "database_url" not in data
    assert "jwt_secret_key" not in data
    assert settings_repository.create_counts[user.id] == 1


@pytest.mark.asyncio
async def test_patch_settings_updates_only_safe_fields(
    settings_client: AsyncClient,
) -> None:
    access_token = await _register(settings_client)
    response = await settings_client.patch(
        "/api/v1/settings",
        headers=_auth_headers(access_token),
        json={
            "forecast_default_horizon_days": 15,
            "inventory_default_safety_stock": "4.500",
            "timezone": "Asia/Kolkata",
            "metadata": {"layout": "compact"},
        },
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["forecast_default_horizon_days"] == 15
    assert data["inventory_default_safety_stock"] == "4.500"
    assert data["timezone"] == "Asia/Kolkata"
    assert data["metadata"] == {"layout": "compact"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,error_code",
    [
        ({"DATABASE_URL": "postgresql://unsafe"}, "protected_settings_field"),
        ({"unknown_preference": True}, "unknown_settings_field"),
        ({"metadata": {"api_key": "unsafe"}}, "protected_settings_field"),
    ],
)
async def test_patch_settings_rejects_protected_and_unknown_fields(
    settings_client: AsyncClient,
    payload: dict,
    error_code: str,
) -> None:
    access_token = await _register(settings_client)
    response = await settings_client.patch(
        "/api/v1/settings",
        headers=_auth_headers(access_token),
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == error_code


@pytest.mark.asyncio
async def test_reset_all_and_one_category(settings_client: AsyncClient) -> None:
    access_token = await _register(settings_client)
    headers = _auth_headers(access_token)
    update = await settings_client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "forecast_default_horizon_days": 7,
            "dashboard_default_date_range_days": 90,
            "metadata": {"layout": "dense"},
        },
    )
    assert update.status_code == 200

    category_reset = await settings_client.post(
        "/api/v1/settings/reset",
        headers=headers,
        json={"category": "forecast"},
    )
    category_data = category_reset.json()["data"]
    assert category_reset.status_code == 200
    assert category_data["reset_category"] == "forecast"
    assert category_data["settings"]["forecast_default_horizon_days"] == 30
    assert category_data["settings"]["dashboard_default_date_range_days"] == 90
    assert category_data["settings"]["metadata"] == {"layout": "dense"}

    all_reset = await settings_client.post("/api/v1/settings/reset", headers=headers)
    all_data = all_reset.json()["data"]
    assert all_reset.status_code == 200
    assert all_data["reset_category"] is None
    assert all_data["settings"]["dashboard_default_date_range_days"] == 30
    assert all_data["settings"]["metadata"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,payload,expected_key,expected_value",
    [
        (
            "/forecast",
            {"forecast_default_model": "baseline"},
            "forecast_default_model",
            "baseline",
        ),
        (
            "/inventory",
            {"inventory_default_minimum_stock": "2.000"},
            "inventory_default_minimum_stock",
            "2.000",
        ),
        (
            "/sales-upload",
            {"sales_upload_duplicate_policy": "allow"},
            "sales_upload_duplicate_policy",
            "allow",
        ),
        (
            "/reports",
            {"reports_default_format": "csv"},
            "reports_default_format",
            "csv",
        ),
        (
            "/dashboard",
            {"dashboard_default_date_range_days": 60},
            "dashboard_default_date_range_days",
            60,
        ),
        (
            "/background-jobs",
            {"background_jobs_auto_retry_enabled": False},
            "background_jobs_auto_retry_enabled",
            False,
        ),
    ],
)
async def test_category_get_and_patch_endpoints(
    settings_client: AsyncClient,
    path: str,
    payload: dict,
    expected_key: str,
    expected_value,
) -> None:
    access_token = await _register(settings_client)
    headers = _auth_headers(access_token)
    patch = await settings_client.patch(
        f"/api/v1/settings{path}",
        headers=headers,
        json=payload,
    )
    get = await settings_client.get(f"/api/v1/settings{path}", headers=headers)

    assert patch.status_code == 200
    assert patch.json()["data"][expected_key] == expected_value
    assert get.status_code == 200
    assert get.json()["data"][expected_key] == expected_value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,payload",
    [
        ("/forecast", {"forecast_default_horizon_days": 8}),
        ("/inventory", {"inventory_default_minimum_stock": "-1"}),
        ("/sales-upload", {"sales_upload_date_format": "invalid"}),
        ("/reports", {"reports_default_format": "pdf"}),
        ("/dashboard", {"dashboard_default_date_range_days": 2}),
        ("/background-jobs", {"background_jobs_auto_retry_enabled": "yes"}),
    ],
)
async def test_category_updates_validate_values(
    settings_client: AsyncClient,
    path: str,
    payload: dict,
) -> None:
    access_token = await _register(settings_client)
    response = await settings_client.patch(
        f"/api/v1/settings{path}",
        headers=_auth_headers(access_token),
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_settings_value"


@pytest.mark.asyncio
async def test_options_and_user_scoping(
    settings_client: AsyncClient,
) -> None:
    first_token = await _register(settings_client)
    second_token = await _register(settings_client, SECOND_OWNER_PAYLOAD)
    first_headers = _auth_headers(first_token)
    second_headers = _auth_headers(second_token)
    update = await settings_client.patch(
        "/api/v1/settings/forecast",
        headers=first_headers,
        json={"forecast_default_horizon_days": 7},
    )
    options = await settings_client.get(
        "/api/v1/settings/options", headers=first_headers
    )
    second_settings = await settings_client.get(
        "/api/v1/settings",
        headers=second_headers,
    )

    assert update.status_code == 200
    assert options.status_code == 200
    assert options.json()["data"]["forecast_horizons"] == [7, 15, 30]
    assert "sales_upload" in options.json()["data"]["reset_categories"]
    assert second_settings.status_code == 200
    assert second_settings.json()["data"]["forecast_default_horizon_days"] == 30


@pytest.mark.asyncio
async def test_concurrent_settings_reads_create_one_record(
    settings_client: AsyncClient,
    settings_repository: FakeSettingsRepository,
    auth_repository,
) -> None:
    access_token = await _register(settings_client)
    headers = _auth_headers(access_token)
    responses = await asyncio.gather(
        *(settings_client.get("/api/v1/settings", headers=headers) for _ in range(10))
    )
    user = auth_repository.users_by_email[OWNER_PAYLOAD["email"]]

    assert all(response.status_code == 200 for response in responses)
    assert settings_repository.create_counts[user.id] == 1
