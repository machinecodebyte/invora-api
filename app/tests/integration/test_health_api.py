import pytest


@pytest.mark.asyncio
async def test_health_returns_200(async_client) -> None:
    response = await async_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "ok"}}


@pytest.mark.asyncio
async def test_readiness_returns_database_unavailable_when_database_is_down(
    async_client,
    monkeypatch,
) -> None:
    async def database_is_not_ready() -> bool:
        return False

    monkeypatch.setattr(
        "app.api.v1.health.check_database_ready",
        database_is_not_ready,
    )

    response = await async_client.get("/api/v1/health/ready")
    body = response.json()

    assert response.status_code == 503
    assert body["success"] is False
    assert body["error"]["code"] == "database_unavailable"
    assert body["error"]["message"] == "Database is not ready."


@pytest.mark.asyncio
async def test_readiness_returns_background_jobs_unavailable_when_workers_are_down(
    async_client,
    monkeypatch,
) -> None:
    async def database_is_ready() -> bool:
        return True

    async def background_jobs_are_not_ready() -> bool:
        return False

    monkeypatch.setattr("app.api.v1.health.check_database_ready", database_is_ready)
    monkeypatch.setattr(
        "app.api.v1.health.check_background_jobs_ready",
        background_jobs_are_not_ready,
    )

    response = await async_client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "success": False,
        "error": {
            "code": "background_jobs_unavailable",
            "message": "Background job processing is not ready.",
        },
    }


@pytest.mark.asyncio
async def test_readiness_returns_ready_when_database_and_jobs_are_ready(
    async_client,
    monkeypatch,
) -> None:
    async def ready() -> bool:
        return True

    monkeypatch.setattr("app.api.v1.health.check_database_ready", ready)
    monkeypatch.setattr("app.api.v1.health.check_background_jobs_ready", ready)

    response = await async_client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "ready"}}
