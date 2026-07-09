from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.shared.utils import utc_now

OWNER_PAYLOAD = {
    "email": "forecast-results-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Forecast Results Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "forecast-results-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Forecast Results Owner",
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


async def _seed_completed_result(
    client,
    access_token: str,
    auth_repository,
    forecast_repository,
) -> tuple[object, dict, dict]:
    first = await _create_product(
        client,
        access_token,
        sku=f"alpha-{uuid4().hex[:8]}",
        name="Alpha Milk",
    )
    second = await _create_product(
        client,
        access_token,
        sku=f"beta-{uuid4().hex[:8]}",
        name="Beta Rice",
    )
    user_id = auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id
    now = utc_now()
    run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={
            "horizon_days": 7,
            "status": "completed",
            "requested_at": now,
            "completed_at": now,
            "total_products": 2,
            "total_sales_records": 4,
            "run_metadata": {"model_name": "test_model_v1"},
        },
    )
    start = date(2026, 7, 10)
    rows = []
    for offset, demand in enumerate((10, 11, 12)):
        rows.append(
            {
                "product_id": UUID(first["id"]),
                "forecast_date": start + timedelta(days=offset),
                "predicted_demand": Decimal(demand).quantize(Decimal("0.001")),
                "model_name": "test_model_v1",
            }
        )
    for offset, demand in enumerate((5, 6, 7)):
        rows.append(
            {
                "product_id": UUID(second["id"]),
                "forecast_date": start + timedelta(days=offset),
                "predicted_demand": Decimal(demand).quantize(Decimal("0.001")),
                "model_name": "test_model_v1",
            }
        )
    await forecast_repository.bulk_create_forecast_predictions(
        user_id=user_id,
        forecast_run_id=run.id,
        rows=rows,
    )
    await forecast_repository.create_forecast_metrics(
        user_id=user_id,
        forecast_run_id=run.id,
        values={
            "model_name": "test_model_v1",
            "mae": Decimal("1.0000"),
            "rmse": Decimal("1.5000"),
            "mape": Decimal("10.0000"),
            "training_rows": 20,
            "validation_rows": 6,
            "total_products": 2,
            "fallback_products": 0,
        },
    )
    return run, first, second


@pytest.mark.asyncio
async def test_get_forecast_result_overview_requires_auth(forecast_client) -> None:
    response = await forecast_client.get(f"/api/v1/forecast-results/runs/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_result_overview_returns_summary_for_completed_run(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, _, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["run_id"] == str(run.id)
    assert data["status"] == "completed"
    assert data["total_predictions"] == 6
    assert data["forecast_start_date"] == "2026-07-10"
    assert data["forecast_end_date"] == "2026-07-12"
    assert data["total_predicted_demand"] == "51.000"
    assert data["average_predicted_demand"] == "8.500"
    assert data["metrics"]["model_name"] == "test_model_v1"


@pytest.mark.asyncio
async def test_result_overview_returns_conflict_when_results_not_ready(
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

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "forecast_results_not_ready"


@pytest.mark.asyncio
async def test_forecast_results_are_user_scoped(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    first_token = await _register(forecast_client)
    second_token = await _register(forecast_client, SECOND_OWNER_PAYLOAD)
    run, _, _ = await _seed_completed_result(
        forecast_client,
        first_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}",
        headers=_auth_headers(second_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_run_not_found"


@pytest.mark.asyncio
async def test_predictions_endpoint_returns_paginated_predictions(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, _, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/predictions",
        headers=_auth_headers(access_token),
        params={"limit": 2, "offset": 0},
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["total"] == 6
    assert data["limit"] == 2
    assert len(data["predictions"]) == 2
    assert data["predictions"][0]["product_name"] == "Alpha Milk"
    assert data["predictions"][0]["current_stock"] is None


@pytest.mark.asyncio
async def test_predictions_endpoint_filters_by_product(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, first, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/predictions",
        headers=_auth_headers(access_token),
        params={"product_id": first["id"]},
    )
    predictions = response.json()["data"]["predictions"]

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 3
    assert {prediction["product_id"] for prediction in predictions} == {first["id"]}


@pytest.mark.asyncio
async def test_predictions_endpoint_filters_by_date_range(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, _, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/predictions",
        headers=_auth_headers(access_token),
        params={"date_from": "2026-07-11", "date_to": "2026-07-11"},
    )
    predictions = response.json()["data"]["predictions"]

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 2
    assert {prediction["forecast_date"] for prediction in predictions} == {
        "2026-07-11"
    }


@pytest.mark.asyncio
async def test_predictions_endpoint_searches_product_metadata(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, first, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/predictions",
        headers=_auth_headers(access_token),
        params={"search": "alpha"},
    )
    predictions = response.json()["data"]["predictions"]

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 3
    assert {prediction["product_id"] for prediction in predictions} == {first["id"]}


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_model_metrics(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, _, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/metrics",
        headers=_auth_headers(access_token),
    )
    metrics = response.json()["data"]["metrics"]

    assert response.status_code == 200
    assert metrics["model_name"] == "test_model_v1"
    assert metrics["mae"] == "1.0000"
    assert metrics["training_rows"] == 20


@pytest.mark.asyncio
async def test_chart_endpoint_returns_date_wise_predicted_demand(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, _, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/chart",
        headers=_auth_headers(access_token),
    )
    points = response.json()["data"]["points"]

    assert response.status_code == 200
    assert response.json()["data"]["metadata"]["interval"] == "day"
    assert points[0] == {
        "period_start": "2026-07-10",
        "predicted_demand": "15.000",
        "actual_quantity": None,
    }


@pytest.mark.asyncio
async def test_chart_endpoint_includes_actual_sales_when_available(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, first, second = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )
    await _create_sales_transaction(
        forecast_client,
        access_token,
        first["id"],
        sale_date=date(2026, 7, 10),
        quantity=3,
    )
    await _create_sales_transaction(
        forecast_client,
        access_token,
        second["id"],
        sale_date=date(2026, 7, 10),
        quantity=2,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/chart",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["points"][0]["actual_quantity"] == "5.000"


@pytest.mark.asyncio
async def test_product_detail_endpoint_returns_one_products_forecast(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(forecast_client)
    run, first, _ = await _seed_completed_result(
        forecast_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/products/{first['id']}",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["product_id"] == first["id"]
    assert data["total_predicted_demand"] == "33.000"
    assert len(data["points"]) == 3
    assert data["points"][0]["forecast_date"] == "2026-07-10"


@pytest.mark.asyncio
async def test_product_detail_rejects_another_users_product(
    forecast_client,
    auth_repository,
    forecast_repository,
) -> None:
    first_token = await _register(forecast_client)
    second_token = await _register(forecast_client, SECOND_OWNER_PAYLOAD)
    run, _, _ = await _seed_completed_result(
        forecast_client,
        first_token,
        auth_repository,
        forecast_repository,
    )
    second_product = await _create_product(
        forecast_client,
        second_token,
        sku="other-product",
        name="Other Product",
    )

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{run.id}/products/{second_product['id']}",
        headers=_auth_headers(first_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_result_product_not_found"


@pytest.mark.asyncio
async def test_missing_forecast_result_run_returns_safe_404(forecast_client) -> None:
    access_token = await _register(forecast_client)

    response = await forecast_client.get(
        f"/api/v1/forecast-results/runs/{uuid4()}",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_run_not_found"
