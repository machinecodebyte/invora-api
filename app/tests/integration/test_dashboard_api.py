from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.shared.utils import utc_now

OWNER_PAYLOAD = {
    "email": "dashboard-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Dashboard Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "dashboard-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Dashboard Owner",
}


async def _register(client, payload: dict = OWNER_PAYLOAD) -> str:
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()["data"]["tokens"]["access_token"]


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _create_category(client, access_token: str, name: str) -> dict:
    response = await client.post(
        "/api/v1/products/categories",
        headers=_auth_headers(access_token),
        json={"name": name},
    )
    assert response.status_code == 201
    return response.json()["data"]["category"]


async def _create_product(
    client,
    access_token: str,
    *,
    sku: str,
    name: str,
    category_id: str | None = None,
) -> dict:
    payload = {
        "name": name,
        "sku": sku,
        "unit": "pcs",
        "selling_price": "10.00",
    }
    if category_id is not None:
        payload["category_id"] = category_id
    response = await client.post(
        "/api/v1/products",
        headers=_auth_headers(access_token),
        json=payload,
    )
    assert response.status_code == 201
    return response.json()["data"]["product"]


async def _create_inventory_item(
    client,
    access_token: str,
    *,
    product_id: str,
    opening_stock: str,
    minimum_stock: str,
    safety_stock: str = "0.000",
) -> dict:
    response = await client.post(
        "/api/v1/inventory/items",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "opening_stock": opening_stock,
            "minimum_stock": minimum_stock,
            "safety_stock": safety_stock,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["item"]


async def _create_sale(
    client,
    access_token: str,
    *,
    product_id: str,
    sale_date: date,
    quantity: str,
    unit_price: str = "10.00",
) -> dict:
    response = await client.post(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "sale_date": sale_date.isoformat(),
            "quantity": quantity,
            "unit_price": unit_price,
            "channel": "store",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["transaction"]


async def _seed_dashboard_data(
    client,
    access_token: str,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> dict[str, object]:
    now = utc_now()
    category = await _create_category(client, access_token, "Staples")
    low_product = await _create_product(
        client,
        access_token,
        sku=f"low-{uuid4().hex[:8]}",
        name="Low Rice",
        category_id=category["id"],
    )
    out_product = await _create_product(
        client,
        access_token,
        sku=f"out-{uuid4().hex[:8]}",
        name="Out Flour",
        category_id=category["id"],
    )
    healthy_product = await _create_product(
        client,
        access_token,
        sku=f"ok-{uuid4().hex[:8]}",
        name="Healthy Oil",
        category_id=category["id"],
    )
    await _create_inventory_item(
        client,
        access_token,
        product_id=low_product["id"],
        opening_stock="2.000",
        minimum_stock="5.000",
        safety_stock="2.000",
    )
    await _create_inventory_item(
        client,
        access_token,
        product_id=out_product["id"],
        opening_stock="0.000",
        minimum_stock="5.000",
        safety_stock="1.000",
    )
    await _create_inventory_item(
        client,
        access_token,
        product_id=healthy_product["id"],
        opening_stock="20.000",
        minimum_stock="5.000",
        safety_stock="3.000",
    )

    first_sale = await _create_sale(
        client,
        access_token,
        product_id=low_product["id"],
        sale_date=date(2026, 7, 1),
        quantity="2.000",
    )
    await _create_sale(
        client,
        access_token,
        product_id=low_product["id"],
        sale_date=date(2026, 7, 2),
        quantity="3.000",
    )
    await _create_sale(
        client,
        access_token,
        product_id=out_product["id"],
        sale_date=date(2026, 7, 3),
        quantity="4.000",
    )
    deleted_sale = await _create_sale(
        client,
        access_token,
        product_id=low_product["id"],
        sale_date=date(2026, 7, 2),
        quantity="99.000",
    )
    await sales_repository.soft_delete_transaction(
        sales_repository.transactions_by_id[UUID(deleted_sale["id"])],
        deleted_reason="dashboard test",
    )

    user_id = auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id
    await sales_repository.create_upload_batch(
        user_id=user_id,
        values={
            "original_filename": "dashboard-sales.csv",
            "status": "completed",
            "total_rows": 4,
            "accepted_rows": 3,
            "rejected_rows": 1,
            "started_at": now - timedelta(minutes=20),
            "completed_at": now - timedelta(minutes=19),
        },
    )
    completed_run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={
            "horizon_days": 7,
            "status": "completed",
            "requested_at": now - timedelta(minutes=10),
            "completed_at": now - timedelta(minutes=8),
            "total_products": 3,
            "total_sales_records": 3,
            "run_metadata": {"model_name": "dashboard_model"},
        },
    )
    pending_run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={
            "horizon_days": 7,
            "status": "pending",
            "requested_at": now - timedelta(minutes=1),
            "total_products": 3,
            "total_sales_records": 3,
        },
    )
    await forecast_repository.bulk_create_forecast_predictions(
        user_id=user_id,
        forecast_run_id=completed_run.id,
        rows=[
            {
                "product_id": UUID(low_product["id"]),
                "forecast_date": date(2026, 7, 10),
                "predicted_demand": Decimal("5.000"),
                "model_name": "dashboard_model",
            },
            {
                "product_id": UUID(out_product["id"]),
                "forecast_date": date(2026, 7, 11),
                "predicted_demand": Decimal("6.000"),
                "model_name": "dashboard_model",
            },
        ],
    )
    await forecast_repository.create_forecast_metrics(
        user_id=user_id,
        forecast_run_id=completed_run.id,
        values={
            "model_name": "dashboard_model",
            "mae": Decimal("1.0000"),
            "rmse": Decimal("2.0000"),
            "mape": Decimal("12.3400"),
            "training_rows": 30,
            "validation_rows": 6,
            "total_products": 3,
            "fallback_products": 0,
        },
    )
    await recommendation_repository.bulk_create_recommendations(
        user_id=user_id,
        rows=[
            {
                "forecast_run_id": completed_run.id,
                "product_id": UUID(low_product["id"]),
                "predicted_demand": Decimal("10.000"),
                "current_stock": Decimal("2.000"),
                "minimum_stock": Decimal("5.000"),
                "safety_stock": Decimal("1.000"),
                "required_stock": Decimal("11.000"),
                "reorder_quantity": Decimal("9.000"),
                "stock_gap": Decimal("9.000"),
                "risk_level": "high",
                "recommended_action": "reorder_now",
                "reason": "Dashboard test",
                "status": "open",
                "generated_at": now - timedelta(minutes=7),
            },
            {
                "forecast_run_id": completed_run.id,
                "product_id": UUID(out_product["id"]),
                "predicted_demand": Decimal("5.000"),
                "current_stock": Decimal("0.000"),
                "minimum_stock": Decimal("5.000"),
                "safety_stock": Decimal("0.000"),
                "required_stock": Decimal("5.000"),
                "reorder_quantity": Decimal("5.000"),
                "stock_gap": Decimal("5.000"),
                "risk_level": "critical",
                "recommended_action": "reorder_now",
                "reason": "Dashboard test",
                "status": "open",
                "generated_at": now - timedelta(minutes=6),
            },
            {
                "forecast_run_id": completed_run.id,
                "product_id": UUID(healthy_product["id"]),
                "predicted_demand": Decimal("5.000"),
                "current_stock": Decimal("20.000"),
                "minimum_stock": Decimal("5.000"),
                "safety_stock": Decimal("0.000"),
                "required_stock": Decimal("5.000"),
                "reorder_quantity": Decimal("0.000"),
                "stock_gap": Decimal("-15.000"),
                "risk_level": "low",
                "recommended_action": "no_reorder_needed",
                "reason": "Dashboard test",
                "status": "acknowledged",
                "generated_at": now - timedelta(minutes=5),
            },
        ],
    )
    return {
        "user_id": user_id,
        "category": category,
        "low_product": low_product,
        "out_product": out_product,
        "healthy_product": healthy_product,
        "first_sale": first_sale,
        "completed_run": completed_run,
        "pending_run": pending_run,
    }


@pytest.mark.asyncio
async def test_dashboard_summary_requires_auth(dashboard_client) -> None:
    response = await dashboard_client.get("/api/v1/dashboard/summary")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_dashboard_summary_returns_empty_safe_shape(dashboard_client) -> None:
    access_token = await _register(dashboard_client)

    response = await dashboard_client.get(
        "/api/v1/dashboard/summary",
        headers=_auth_headers(access_token),
        params={"date_to": "2026-07-10"},
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["date_from"] == "2026-06-11"
    assert data["kpis"]["total_products"] == 0
    assert data["demand_trends"]["points"] == []
    assert data["forecast_overview"]["latest_forecast_run"] is None
    assert data["reorder_alerts"]["top_reorder_items"] == []
    assert data["recent_activity"]["activities"] == []


@pytest.mark.asyncio
async def test_dashboard_kpis_are_user_scoped(
    dashboard_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(dashboard_client)
    second_token = await _register(dashboard_client, SECOND_OWNER_PAYLOAD)
    await _seed_dashboard_data(
        dashboard_client,
        access_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )
    second_product = await _create_product(
        dashboard_client,
        second_token,
        sku=f"second-{uuid4().hex[:8]}",
        name="Second Product",
    )
    await _create_sale(
        dashboard_client,
        second_token,
        product_id=second_product["id"],
        sale_date=date(2026, 7, 1),
        quantity="50.000",
    )

    response = await dashboard_client.get(
        "/api/v1/dashboard/kpis",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["total_products"] == 3
    assert data["active_products"] == 3
    assert data["total_sales_records"] == 3
    assert data["total_inventory_items"] == 3
    assert data["low_stock_count"] == 1
    assert data["out_of_stock_count"] == 1
    assert data["total_forecast_runs"] == 2
    assert data["completed_forecast_runs"] == 1
    assert data["latest_forecast_mape"] == "12.3400"
    assert data["open_recommendations"] == 2
    assert data["high_risk_recommendations"] == 1
    assert data["critical_risk_recommendations"] == 1
    assert data["total_reorder_quantity"] == "14.000"


@pytest.mark.asyncio
async def test_dashboard_demand_trends_aggregate_and_filter_sales(
    dashboard_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(dashboard_client)
    seeded = await _seed_dashboard_data(
        dashboard_client,
        access_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await dashboard_client.get(
        "/api/v1/dashboard/demand-trends",
        headers=_auth_headers(access_token),
        params={
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
            "interval": "day",
        },
    )
    product_response = await dashboard_client.get(
        "/api/v1/dashboard/demand-trends",
        headers=_auth_headers(access_token),
        params={
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
            "interval": "day",
            "product_id": seeded["low_product"]["id"],
        },
    )
    week_response = await dashboard_client.get(
        "/api/v1/dashboard/demand-trends",
        headers=_auth_headers(access_token),
        params={
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
            "interval": "week",
        },
    )

    points = response.json()["data"]["points"]
    product_points = product_response.json()["data"]["points"]
    week_points = week_response.json()["data"]["points"]

    assert response.status_code == 200
    assert len(points) == 3
    assert points[0]["period"] == "2026-07-01"
    assert points[0]["total_quantity_sold"] == "2.000"
    assert sum(Decimal(row["total_quantity_sold"]) for row in points) == Decimal(
        "9.000"
    )
    assert product_response.status_code == 200
    assert len(product_points) == 2
    assert sum(
        Decimal(row["total_quantity_sold"]) for row in product_points
    ) == Decimal("5.000")
    assert week_response.status_code == 200
    assert len(week_points) == 1
    assert week_points[0]["period"] == "2026-06-29"
    assert week_points[0]["total_quantity_sold"] == "9.000"


@pytest.mark.asyncio
async def test_dashboard_demand_trends_reject_another_users_product(
    dashboard_client,
) -> None:
    first_token = await _register(dashboard_client)
    second_token = await _register(dashboard_client, SECOND_OWNER_PAYLOAD)
    second_product = await _create_product(
        dashboard_client,
        second_token,
        sku=f"foreign-{uuid4().hex[:8]}",
        name="Foreign Product",
    )

    response = await dashboard_client.get(
        "/api/v1/dashboard/demand-trends",
        headers=_auth_headers(first_token),
        params={"product_id": second_product["id"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "dashboard_product_not_found"


@pytest.mark.asyncio
async def test_dashboard_inventory_risk_returns_counts_and_preview(
    dashboard_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(dashboard_client)
    await _seed_dashboard_data(
        dashboard_client,
        access_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await dashboard_client.get(
        "/api/v1/dashboard/inventory-risk",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["total_inventory_items"] == 3
    assert data["low_stock_count"] == 1
    assert data["out_of_stock_count"] == 1
    assert data["healthy_stock_count"] == 1
    assert data["low_stock_items"][0]["product_name"] == "Low Rice"
    assert data["low_stock_items"][0]["stock_status"] == "low_stock"
    assert data["out_of_stock_items"][0]["product_name"] == "Out Flour"


@pytest.mark.asyncio
async def test_dashboard_forecast_overview_returns_latest_run_and_metrics(
    dashboard_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(dashboard_client)
    seeded = await _seed_dashboard_data(
        dashboard_client,
        access_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await dashboard_client.get(
        "/api/v1/dashboard/forecast-overview",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["latest_forecast_run"]["id"] == str(seeded["pending_run"].id)
    assert data["latest_completed_forecast_run"]["id"] == str(
        seeded["completed_run"].id
    )
    assert data["forecast_run_counts_by_status"]["pending"] == 1
    assert data["forecast_run_counts_by_status"]["completed"] == 1
    assert data["latest_metrics"]["mape"] == "12.3400"
    assert data["total_predictions_in_latest_run"] == 2
    assert data["forecast_date_range"]["date_from"] == "2026-07-10"
    assert data["forecast_date_range"]["date_to"] == "2026-07-11"
    assert data["total_predicted_demand"] == "11.000"


@pytest.mark.asyncio
async def test_dashboard_reorder_alerts_filter_and_scope_forecast_run(
    dashboard_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(dashboard_client)
    second_token = await _register(dashboard_client, SECOND_OWNER_PAYLOAD)
    seeded = await _seed_dashboard_data(
        dashboard_client,
        access_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )
    second_user_id = auth_repository.users_by_email[SECOND_OWNER_PAYLOAD["email"]].id
    second_run = await forecast_repository.create_forecast_run(
        user_id=second_user_id,
        values={"horizon_days": 7, "status": "completed"},
    )

    response = await dashboard_client.get(
        "/api/v1/dashboard/reorder-alerts",
        headers=_auth_headers(access_token),
        params={
            "forecast_run_id": str(seeded["completed_run"].id),
            "risk_level": "critical",
            "status": "open",
        },
    )
    foreign_response = await dashboard_client.get(
        "/api/v1/dashboard/reorder-alerts",
        headers=_auth_headers(access_token),
        params={"forecast_run_id": str(second_run.id)},
    )
    second_response = await dashboard_client.get(
        "/api/v1/dashboard/reorder-alerts",
        headers=_auth_headers(second_token),
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["critical_count"] == 1
    assert data["high_count"] == 1
    assert data["open_count"] == 2
    assert data["total_reorder_quantity"] == "14.000"
    assert len(data["top_reorder_items"]) == 1
    assert data["top_reorder_items"][0]["risk_level"] == "critical"
    assert foreign_response.status_code == 404
    assert foreign_response.json()["error"]["code"] == (
        "dashboard_forecast_run_not_found"
    )
    assert second_response.status_code == 200
    assert second_response.json()["data"]["open_count"] == 0


@pytest.mark.asyncio
async def test_dashboard_recent_activity_returns_combined_feed(
    dashboard_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(dashboard_client)
    await _seed_dashboard_data(
        dashboard_client,
        access_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await dashboard_client.get(
        "/api/v1/dashboard/recent-activity",
        headers=_auth_headers(access_token),
        params={"limit": 10},
    )
    activities = response.json()["data"]["activities"]
    event_types = {event["event_type"] for event in activities}

    assert response.status_code == 200
    assert "sales_upload" in event_types
    assert "forecast_run" in event_types
    assert "stock_movement" in event_types
    assert "reorder_recommendation" in event_types
    assert activities[0]["occurred_at"] >= activities[-1]["occurred_at"]
