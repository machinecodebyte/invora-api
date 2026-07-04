import pytest


@pytest.mark.asyncio
async def test_health_returns_200(async_client) -> None:
    response = await async_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "ok"}}


@pytest.mark.asyncio
async def test_readiness_returns_consistent_shape(async_client) -> None:
    response = await async_client.get("/api/v1/health/ready")
    body = response.json()

    assert response.status_code in {200, 503}
    assert "success" in body

    if response.status_code == 200:
        assert body == {"success": True, "data": {"status": "ready"}}
    else:
        assert body["success"] is False
        assert body["error"]["code"] == "database_unavailable"
        assert body["error"]["message"] == "Database is not ready."
