from uuid import UUID

import pytest

OWNER_PAYLOAD = {
    "email": "forecast-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Forecast Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "forecast-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Forecast Owner",
}


async def _register(client, payload: dict = OWNER_PAYLOAD) -> str:
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()["data"]["tokens"]["access_token"]


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _create_product(
    client,
    access_token: str,
    *,
    sku: str = "milk-1",
    name: str = "Milk",
) -> dict:
    response = await client.post(
        "/api/v1/products",
        headers=_auth_headers(access_token),
        json={
            "name": name,
            "sku": sku,
            "unit": "liter",
            "selling_price": "12.50",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["product"]


async def _create_sales_transaction(
    client,
    access_token: str,
    product_id: str,
    *,
    sale_date: str = "2026-07-01",
) -> dict:
    response = await client.post(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "sale_date": sale_date,
            "quantity": "2.000",
            "unit_price": "12.50",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["transaction"]


async def _seed_forecast_ready_user(client, access_token: str) -> dict:
    product = await _create_product(client, access_token)
    await _create_sales_transaction(client, access_token, product["id"])
    return product


async def _create_forecast_run(
    client,
    access_token: str,
    *,
    horizon_days: int = 7,
) -> dict:
    response = await client.post(
        "/api/v1/forecast-runs",
        headers=_auth_headers(access_token),
        json={"horizon_days": horizon_days},
    )
    assert response.status_code == 201
    return response.json()["data"]["run"]


@pytest.mark.asyncio
async def test_post_forecast_run_requires_auth(forecast_client) -> None:
    response = await forecast_client.post(
        "/api/v1/forecast-runs",
        json={"horizon_days": 7},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_create_forecast_run_succeeds_with_product_and_sales_data(
    forecast_client,
) -> None:
    access_token = await _register(forecast_client)
    await _seed_forecast_ready_user(forecast_client, access_token)

    response = await forecast_client.post(
        "/api/v1/forecast-runs",
        headers=_auth_headers(access_token),
        json={"horizon_days": 15},
    )
    run = response.json()["data"]["run"]

    assert response.status_code == 201
    assert run["status"] == "pending"
    assert run["horizon_days"] == 15
    assert run["total_products"] == 1
    assert run["total_sales_records"] == 1
    assert run["metadata"]["sales_date_from"] == "2026-07-01"


@pytest.mark.asyncio
async def test_create_forecast_run_fails_with_invalid_horizon(
    forecast_client,
) -> None:
    access_token = await _register(forecast_client)

    response = await forecast_client.post(
        "/api/v1/forecast-runs",
        headers=_auth_headers(access_token),
        json={"horizon_days": 14},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_forecast_horizon"


@pytest.mark.asyncio
async def test_create_forecast_run_fails_with_no_sales_data(forecast_client) -> None:
    access_token = await _register(forecast_client)
    await _create_product(forecast_client, access_token)

    response = await forecast_client.post(
        "/api/v1/forecast-runs",
        headers=_auth_headers(access_token),
        json={"horizon_days": 7},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_forecast_sales_data"


@pytest.mark.asyncio
async def test_create_forecast_run_fails_with_no_active_products(
    forecast_client,
) -> None:
    access_token = await _register(forecast_client)
    product = await _create_product(forecast_client, access_token)
    await _create_sales_transaction(forecast_client, access_token, product["id"])
    archive_response = await forecast_client.delete(
        f"/api/v1/products/{product['id']}",
        headers=_auth_headers(access_token),
    )

    response = await forecast_client.post(
        "/api/v1/forecast-runs",
        headers=_auth_headers(access_token),
        json={"horizon_days": 7},
    )

    assert archive_response.status_code == 200
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_active_forecast_products"


@pytest.mark.asyncio
async def test_list_forecast_runs_returns_only_current_user(forecast_client) -> None:
    first_token = await _register(forecast_client)
    second_token = await _register(forecast_client, SECOND_OWNER_PAYLOAD)
    await _seed_forecast_ready_user(forecast_client, first_token)
    await _seed_forecast_ready_user(forecast_client, second_token)
    await _create_forecast_run(forecast_client, first_token, horizon_days=7)
    await _create_forecast_run(forecast_client, second_token, horizon_days=30)

    response = await forecast_client.get(
        "/api/v1/forecast-runs",
        headers=_auth_headers(first_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["runs"][0]["horizon_days"] == 7


@pytest.mark.asyncio
async def test_get_forecast_run_detail_and_cross_user_access(forecast_client) -> None:
    first_token = await _register(forecast_client)
    second_token = await _register(forecast_client, SECOND_OWNER_PAYLOAD)
    await _seed_forecast_ready_user(forecast_client, first_token)
    run = await _create_forecast_run(forecast_client, first_token)

    own_response = await forecast_client.get(
        f"/api/v1/forecast-runs/{run['id']}",
        headers=_auth_headers(first_token),
    )
    other_response = await forecast_client.get(
        f"/api/v1/forecast-runs/{run['id']}",
        headers=_auth_headers(second_token),
    )

    assert own_response.status_code == 200
    assert other_response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_pending_forecast_run_succeeds(forecast_client) -> None:
    access_token = await _register(forecast_client)
    await _seed_forecast_ready_user(forecast_client, access_token)
    run = await _create_forecast_run(forecast_client, access_token)

    response = await forecast_client.post(
        f"/api/v1/forecast-runs/{run['id']}/cancel",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["run"]["status"] == "cancelled"
    assert response.json()["data"]["run"]["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_cancel_completed_or_cancelled_forecast_run_returns_conflict(
    forecast_client,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    await _seed_forecast_ready_user(forecast_client, access_token)
    completed = await _create_forecast_run(forecast_client, access_token)
    cancelled = await _create_forecast_run(
        forecast_client,
        access_token,
        horizon_days=30,
    )
    forecast_repository.runs_by_id[UUID(completed["id"])].status = "completed"
    await forecast_client.post(
        f"/api/v1/forecast-runs/{cancelled['id']}/cancel",
        headers=_auth_headers(access_token),
    )

    completed_response = await forecast_client.post(
        f"/api/v1/forecast-runs/{completed['id']}/cancel",
        headers=_auth_headers(access_token),
    )
    cancelled_response = await forecast_client.post(
        f"/api/v1/forecast-runs/{cancelled['id']}/cancel",
        headers=_auth_headers(access_token),
    )

    assert completed_response.status_code == 409
    assert completed_response.json()["error"]["code"] == (
        "forecast_run_already_completed"
    )
    assert cancelled_response.status_code == 409
    assert cancelled_response.json()["error"]["code"] == (
        "forecast_run_already_cancelled"
    )


@pytest.mark.asyncio
async def test_forecast_run_options_returns_horizons_and_statuses(
    forecast_client,
) -> None:
    access_token = await _register(forecast_client)

    response = await forecast_client.get(
        "/api/v1/forecast-runs/options",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["horizons"] == [7, 15, 30]
    assert response.json()["data"]["statuses"] == [
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
    ]
