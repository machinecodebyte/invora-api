from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.shared.utils import utc_now

OWNER_PAYLOAD = {
    "email": "recommendations-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Recommendation Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "recommendations-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Recommendation Owner",
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
            "selling_price": "12.50",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["product"]


async def _create_inventory_item(
    client,
    access_token: str,
    *,
    product_id: str,
    current_stock: Decimal,
    minimum_stock: Decimal = Decimal("0.000"),
    safety_stock: Decimal = Decimal("0.000"),
) -> dict:
    response = await client.post(
        "/api/v1/inventory/items",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "opening_stock": str(current_stock),
            "minimum_stock": str(minimum_stock),
            "safety_stock": str(safety_stock),
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["item"]


async def _create_completed_run(
    auth_repository,
    forecast_repository,
    *,
    owner_email: str,
    total_products: int,
) -> object:
    user_id = auth_repository.users_by_email[owner_email].id
    now = utc_now()
    return await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={
            "horizon_days": 7,
            "status": "completed",
            "requested_at": now,
            "completed_at": now,
            "total_products": total_products,
            "total_sales_records": 20,
            "run_metadata": {"model_name": "recommendation_test_model"},
        },
    )


async def _seed_recommendation_fixture(
    client,
    access_token: str,
    auth_repository,
    forecast_repository,
) -> tuple[object, list[dict]]:
    specs = [
        {
            "sku": f"critical-{uuid4().hex[:8]}",
            "name": "Critical Flour",
            "current": Decimal("0.000"),
            "safety": Decimal("0.000"),
            "demand": (Decimal("2.000"), Decimal("3.000")),
        },
        {
            "sku": f"high-{uuid4().hex[:8]}",
            "name": "High Rice",
            "current": Decimal("3.000"),
            "safety": Decimal("2.000"),
            "demand": (Decimal("4.000"), Decimal("6.000")),
        },
        {
            "sku": f"medium-{uuid4().hex[:8]}",
            "name": "Medium Oil",
            "current": Decimal("11.000"),
            "safety": Decimal("3.000"),
            "demand": (Decimal("5.000"), Decimal("5.000")),
        },
        {
            "sku": f"low-{uuid4().hex[:8]}",
            "name": "Low Sugar",
            "current": Decimal("12.000"),
            "safety": Decimal("2.000"),
            "demand": (Decimal("5.000"), Decimal("5.000")),
        },
        {
            "sku": f"overstock-{uuid4().hex[:8]}",
            "name": "Overstock Tea",
            "current": Decimal("24.000"),
            "safety": Decimal("2.000"),
            "demand": (Decimal("5.000"), Decimal("5.000")),
        },
    ]
    products: list[dict] = []
    for spec in specs:
        product = await _create_product(
            client,
            access_token,
            sku=spec["sku"],
            name=spec["name"],
        )
        await _create_inventory_item(
            client,
            access_token,
            product_id=product["id"],
            current_stock=spec["current"],
            safety_stock=spec["safety"],
        )
        products.append(product)

    run = await _create_completed_run(
        auth_repository,
        forecast_repository,
        owner_email=OWNER_PAYLOAD["email"],
        total_products=len(products),
    )
    start_date = date(2026, 7, 10)
    rows = []
    for product, spec in zip(products, specs, strict=True):
        for offset, demand in enumerate(spec["demand"]):
            rows.append(
                {
                    "product_id": UUID(product["id"]),
                    "forecast_date": start_date + timedelta(days=offset),
                    "predicted_demand": demand,
                    "model_name": "recommendation_test_model",
                }
            )
    await forecast_repository.bulk_create_forecast_predictions(
        user_id=auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id,
        forecast_run_id=run.id,
        rows=rows,
    )
    return run, products


@pytest.mark.asyncio
async def test_generate_recommendations_requires_auth(recommendation_client) -> None:
    response = await recommendation_client.post(
        f"/api/v1/recommendations/runs/{uuid4()}/generate",
        json={},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_generate_recommendations_creates_risk_decisions(
    recommendation_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(recommendation_client)
    run, _ = await _seed_recommendation_fixture(
        recommendation_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await recommendation_client.post(
        f"/api/v1/recommendations/runs/{run.id}/generate",
        headers=_auth_headers(access_token),
        json={},
    )
    data = response.json()["data"]

    assert response.status_code == 201
    assert data["forecast_run_id"] == str(run.id)
    assert data["total_products"] == 5
    assert data["recommendations_created"] == 5
    assert data["critical_count"] == 1
    assert data["high_count"] == 1
    assert data["medium_count"] == 1
    assert data["low_count"] == 1
    assert data["overstocked_count"] == 1

    list_response = await recommendation_client.get(
        "/api/v1/recommendations",
        headers=_auth_headers(access_token),
        params={"limit": 20, "sort_by": "sku", "sort_order": "asc"},
    )
    recommendations = list_response.json()["data"]["recommendations"]
    by_name = {row["product_name"]: row for row in recommendations}

    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 5
    assert by_name["High Rice"]["predicted_demand"] == "10.000"
    assert by_name["High Rice"]["required_stock"] == "12.000"
    assert by_name["High Rice"]["stock_gap"] == "9.000"
    assert by_name["High Rice"]["reorder_quantity"] == "9.000"
    assert by_name["High Rice"]["risk_level"] == "high"
    assert by_name["High Rice"]["recommended_action"] == "reorder_now"
    assert by_name["Overstock Tea"]["risk_level"] == "overstocked"
    assert by_name["Overstock Tea"]["recommended_action"] == "overstock_review"


@pytest.mark.asyncio
async def test_generate_recommendations_requires_completed_run(
    recommendation_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(recommendation_client)
    user_id = auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id
    run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={"horizon_days": 7, "status": "pending"},
    )

    response = await recommendation_client.post(
        f"/api/v1/recommendations/runs/{run.id}/generate",
        headers=_auth_headers(access_token),
        json={},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "recommendation_forecast_run_not_completed"
    )


@pytest.mark.asyncio
async def test_generate_recommendations_requires_predictions(
    recommendation_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(recommendation_client)
    run = await _create_completed_run(
        auth_repository,
        forecast_repository,
        owner_email=OWNER_PAYLOAD["email"],
        total_products=1,
    )

    response = await recommendation_client.post(
        f"/api/v1/recommendations/runs/{run.id}/generate",
        headers=_auth_headers(access_token),
        json={},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == (
        "recommendation_forecast_predictions_not_found"
    )


@pytest.mark.asyncio
async def test_generate_recommendations_requires_inventory_for_forecasted_products(
    recommendation_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(recommendation_client)
    product = await _create_product(
        recommendation_client,
        access_token,
        sku=f"missing-inventory-{uuid4().hex[:8]}",
        name="Missing Inventory Product",
    )
    run = await _create_completed_run(
        auth_repository,
        forecast_repository,
        owner_email=OWNER_PAYLOAD["email"],
        total_products=1,
    )
    await forecast_repository.bulk_create_forecast_predictions(
        user_id=auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id,
        forecast_run_id=run.id,
        rows=[
            {
                "product_id": UUID(product["id"]),
                "forecast_date": date(2026, 7, 10),
                "predicted_demand": Decimal("5.000"),
                "model_name": "recommendation_test_model",
            }
        ],
    )

    response = await recommendation_client.post(
        f"/api/v1/recommendations/runs/{run.id}/generate",
        headers=_auth_headers(access_token),
        json={},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "recommendation_inventory_missing"


@pytest.mark.asyncio
async def test_generate_recommendations_supports_safe_refresh(
    recommendation_client,
    auth_repository,
    forecast_repository,
    inventory_repository,
) -> None:
    access_token = await _register(recommendation_client)
    run, products = await _seed_recommendation_fixture(
        recommendation_client,
        access_token,
        auth_repository,
        forecast_repository,
    )
    generate_url = f"/api/v1/recommendations/runs/{run.id}/generate"

    first_response = await recommendation_client.post(
        generate_url,
        headers=_auth_headers(access_token),
        json={},
    )
    assert first_response.status_code == 201

    conflict_response = await recommendation_client.post(
        generate_url,
        headers=_auth_headers(access_token),
        json={},
    )
    assert conflict_response.status_code == 409
    assert conflict_response.json()["error"]["code"] == (
        "recommendations_already_generated"
    )

    first_list = await recommendation_client.get(
        "/api/v1/recommendations",
        headers=_auth_headers(access_token),
    )
    first_ids = {
        row["id"] for row in first_list.json()["data"]["recommendations"]
    }
    target_product_id = UUID(products[3]["id"])
    for item in inventory_repository.items_by_id.values():
        if item.product_id == target_product_id:
            item.current_stock = Decimal("1.000")

    refresh_response = await recommendation_client.post(
        generate_url,
        headers=_auth_headers(access_token),
        json={"refresh": True},
    )
    refreshed_list = await recommendation_client.get(
        "/api/v1/recommendations",
        headers=_auth_headers(access_token),
    )
    refreshed_rows = refreshed_list.json()["data"]["recommendations"]
    refreshed_ids = {row["id"] for row in refreshed_rows}
    low_product = next(
        row for row in refreshed_rows if row["product_name"] == "Low Sugar"
    )

    assert refresh_response.status_code == 201
    assert refresh_response.json()["data"]["refreshed"] is True
    assert len(refreshed_ids) == 5
    assert first_ids.isdisjoint(refreshed_ids)
    assert low_product["current_stock"] == "1.000"
    assert low_product["risk_level"] == "high"


@pytest.mark.asyncio
async def test_recommendation_run_list_summary_detail_and_status_update(
    recommendation_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(recommendation_client)
    run, _ = await _seed_recommendation_fixture(
        recommendation_client,
        access_token,
        auth_repository,
        forecast_repository,
    )
    await recommendation_client.post(
        f"/api/v1/recommendations/runs/{run.id}/generate",
        headers=_auth_headers(access_token),
        json={},
    )

    run_response = await recommendation_client.get(
        f"/api/v1/recommendations/runs/{run.id}",
        headers=_auth_headers(access_token),
        params={"risk_level": "high"},
    )
    high_recommendation = run_response.json()["data"]["recommendations"][0]

    detail_response = await recommendation_client.get(
        f"/api/v1/recommendations/{high_recommendation['id']}",
        headers=_auth_headers(access_token),
    )
    summary_response = await recommendation_client.get(
        f"/api/v1/recommendations/runs/{run.id}/summary",
        headers=_auth_headers(access_token),
    )
    update_response = await recommendation_client.patch(
        f"/api/v1/recommendations/{high_recommendation['id']}/status",
        headers=_auth_headers(access_token),
        json={"status": "acknowledged"},
    )
    invalid_response = await recommendation_client.patch(
        f"/api/v1/recommendations/{high_recommendation['id']}/status",
        headers=_auth_headers(access_token),
        json={"status": "open"},
    )

    assert run_response.status_code == 200
    assert run_response.json()["data"]["total"] == 1
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["recommendation"]["id"] == (
        high_recommendation["id"]
    )
    assert summary_response.status_code == 200
    assert summary_response.json()["data"]["total_recommendations"] == 5
    assert summary_response.json()["data"]["total_reorder_quantity"] == "16.000"
    assert len(summary_response.json()["data"]["top_reorder_products"]) == 5
    assert update_response.status_code == 200
    assert update_response.json()["data"]["recommendation"]["status"] == "acknowledged"
    assert (
        update_response.json()["data"]["recommendation"]["acknowledged_at"] is not None
    )
    assert invalid_response.status_code == 409
    assert invalid_response.json()["error"]["code"] == (
        "invalid_recommendation_status_transition"
    )


@pytest.mark.asyncio
async def test_recommendations_are_user_scoped(
    recommendation_client,
    auth_repository,
    forecast_repository,
) -> None:
    first_token = await _register(recommendation_client)
    second_token = await _register(recommendation_client, SECOND_OWNER_PAYLOAD)
    run, _ = await _seed_recommendation_fixture(
        recommendation_client,
        first_token,
        auth_repository,
        forecast_repository,
    )
    await recommendation_client.post(
        f"/api/v1/recommendations/runs/{run.id}/generate",
        headers=_auth_headers(first_token),
        json={},
    )
    owned_list = await recommendation_client.get(
        "/api/v1/recommendations",
        headers=_auth_headers(first_token),
    )
    recommendation_id = owned_list.json()["data"]["recommendations"][0]["id"]

    second_list = await recommendation_client.get(
        "/api/v1/recommendations",
        headers=_auth_headers(second_token),
    )
    second_run_response = await recommendation_client.get(
        f"/api/v1/recommendations/runs/{run.id}",
        headers=_auth_headers(second_token),
    )
    second_detail_response = await recommendation_client.get(
        f"/api/v1/recommendations/{recommendation_id}",
        headers=_auth_headers(second_token),
    )

    assert second_list.status_code == 200
    assert second_list.json()["data"]["total"] == 0
    assert second_run_response.status_code == 404
    assert second_run_response.json()["error"]["code"] == (
        "recommendation_forecast_run_not_found"
    )
    assert second_detail_response.status_code == 404
    assert second_detail_response.json()["error"]["code"] == "recommendation_not_found"


@pytest.mark.asyncio
async def test_run_recommendations_return_conflict_before_generation(
    recommendation_client,
    auth_repository,
    forecast_repository,
) -> None:
    access_token = await _register(recommendation_client)
    run, _ = await _seed_recommendation_fixture(
        recommendation_client,
        access_token,
        auth_repository,
        forecast_repository,
    )

    response = await recommendation_client.get(
        f"/api/v1/recommendations/runs/{run.id}",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "recommendations_not_generated"
