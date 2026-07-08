from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

OWNER_PAYLOAD = {
    "email": "ml-forecast-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "ML Forecast Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "ml-forecast-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second ML Forecast Owner",
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
    sku: str,
    name: str,
) -> dict:
    response = await client.post(
        "/api/v1/products",
        headers=_auth_headers(access_token),
        json={
            "name": name,
            "sku": sku,
            "unit": "pcs",
            "selling_price": "10.00",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["product"]


async def _create_sales_transaction(
    client,
    access_token: str,
    product_id: str,
    *,
    sale_date: date,
    quantity: Decimal | int,
) -> dict:
    response = await client.post(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "sale_date": sale_date.isoformat(),
            "quantity": str(Decimal(str(quantity)).quantize(Decimal("0.001"))),
            "unit_price": "10.00",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["transaction"]


async def _seed_forecast_ready_user(client, access_token: str) -> tuple[dict, dict]:
    first = await _create_product(
        client,
        access_token,
        sku=f"strong-{uuid4().hex[:8]}",
        name="Strong Product",
    )
    second = await _create_product(
        client,
        access_token,
        sku=f"sparse-{uuid4().hex[:8]}",
        name="Sparse Product",
    )
    start = date(2026, 6, 1)
    for offset in range(14):
        await _create_sales_transaction(
            client,
            access_token,
            first["id"],
            sale_date=start + timedelta(days=offset),
            quantity=4 + (offset % 3),
        )
    await _create_sales_transaction(
        client,
        access_token,
        second["id"],
        sale_date=start,
        quantity=2,
    )
    return first, second


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
async def test_process_forecast_run_requires_auth(forecast_client) -> None:
    response = await forecast_client.post(
        f"/api/v1/forecast-runs/{uuid4()}/process",
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_process_forecast_run_succeeds_and_persists_predictions(
    forecast_client,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    await _seed_forecast_ready_user(forecast_client, access_token)
    run = await _create_forecast_run(forecast_client, access_token)

    response = await forecast_client.post(
        f"/api/v1/forecast-runs/{run['id']}/process",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]
    persisted_run = forecast_repository.runs_by_id[UUID(run["id"])]
    persisted_predictions = [
        prediction
        for prediction in forecast_repository.predictions_by_id.values()
        if prediction.forecast_run_id == persisted_run.id
    ]
    persisted_metrics = [
        metric
        for metric in forecast_repository.metrics_by_id.values()
        if metric.forecast_run_id == persisted_run.id
    ]

    assert response.status_code == 200
    assert data["status"] == "completed"
    assert data["horizon_days"] == 7
    assert data["total_products"] == 2
    assert data["total_sales_records"] == 15
    assert data["predictions_created"] == 14
    assert data["metrics"]["training_rows"] > 0
    assert persisted_run.status == "completed"
    assert persisted_run.completed_at is not None
    assert persisted_run.run_metadata["predictions_created"] == 14
    assert len(persisted_predictions) == 14
    assert len(persisted_metrics) == 1
    assert persisted_metrics[0].total_products == 2
    assert persisted_metrics[0].fallback_products == 1
    assert {prediction.forecast_date for prediction in persisted_predictions} == {
        date(2026, 6, 15) + timedelta(days=offset) for offset in range(7)
    }
    assert min(
        prediction.predicted_demand for prediction in persisted_predictions
    ) >= Decimal("0.000")


@pytest.mark.asyncio
async def test_process_forecast_run_fails_cleanly_with_no_sales_data(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    await _create_product(
        forecast_client,
        access_token,
        sku="nosales-1",
        name="No Sales Product",
    )
    user_id = auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id
    run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={"horizon_days": 7, "status": "pending"},
    )

    response = await forecast_client.post(
        f"/api/v1/forecast-runs/{run.id}/process",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_forecast_sales_data"
    assert run.status == "failed"
    assert run.failed_at is not None
    assert len(forecast_repository.predictions_by_id) == 0


@pytest.mark.asyncio
async def test_process_forecast_run_fails_cleanly_with_no_active_products(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    user_id = auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id
    run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={"horizon_days": 7, "status": "pending"},
    )

    response = await forecast_client.post(
        f"/api/v1/forecast-runs/{run.id}/process",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_active_forecast_products"
    assert run.status == "failed"
    assert run.failed_at is not None


@pytest.mark.asyncio
async def test_process_forecast_run_cannot_access_another_users_run(
    forecast_client,
) -> None:
    first_token = await _register(forecast_client)
    second_token = await _register(forecast_client, SECOND_OWNER_PAYLOAD)
    await _seed_forecast_ready_user(forecast_client, first_token)
    run = await _create_forecast_run(forecast_client, first_token)

    response = await forecast_client.post(
        f"/api/v1/forecast-runs/{run['id']}/process",
        headers=_auth_headers(second_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_run_not_found"


@pytest.mark.asyncio
async def test_process_forecast_run_rejects_non_processable_statuses(
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
    forecast_repository.runs_by_id[UUID(cancelled["id"])].status = "cancelled"

    completed_response = await forecast_client.post(
        f"/api/v1/forecast-runs/{completed['id']}/process",
        headers=_auth_headers(access_token),
    )
    cancelled_response = await forecast_client.post(
        f"/api/v1/forecast-runs/{cancelled['id']}/process",
        headers=_auth_headers(access_token),
    )

    assert completed_response.status_code == 409
    assert completed_response.json()["error"]["code"] == (
        "invalid_ml_forecast_run_status"
    )
    assert cancelled_response.status_code == 409
    assert cancelled_response.json()["error"]["code"] == (
        "invalid_ml_forecast_run_status"
    )


@pytest.mark.asyncio
async def test_ml_forecasting_options_returns_supported_settings(
    forecast_client,
) -> None:
    access_token = await _register(forecast_client)

    response = await forecast_client.get(
        "/api/v1/ml/forecasting/options",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["supported_horizons"] == [7, 15, 30]
    assert response.json()["data"]["default_model"] == "random_forest_regressor_v1"
    assert response.json()["data"]["fallback_strategy"] == (
        "recent_average_baseline_v1"
    )


@pytest.mark.asyncio
async def test_ml_forecasting_health_reports_pipeline_ready(
    forecast_client,
) -> None:
    access_token = await _register(forecast_client)

    response = await forecast_client.get(
        "/api/v1/ml/forecasting/health",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "pandas_available": True,
        "numpy_available": True,
        "scikit_learn_available": True,
        "pipeline_ready": True,
    }
