from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.shared.utils import utc_now

OWNER_PAYLOAD = {
    "email": "reports-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Reports Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "reports-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Reports Owner",
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
    channel: str = "store",
) -> dict:
    response = await client.post(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "sale_date": sale_date.isoformat(),
            "quantity": quantity,
            "unit_price": unit_price,
            "channel": channel,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["transaction"]


async def _seed_reports_data(
    client,
    access_token: str,
    second_token: str,
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
        sku=f"report-low-{uuid4().hex[:8]}",
        name="Report Low Rice",
        category_id=category["id"],
    )
    out_product = await _create_product(
        client,
        access_token,
        sku=f"report-out-{uuid4().hex[:8]}",
        name="Report Out Flour",
        category_id=category["id"],
    )
    healthy_product = await _create_product(
        client,
        access_token,
        sku=f"report-ok-{uuid4().hex[:8]}",
        name="Report Healthy Oil",
        category_id=category["id"],
    )
    second_category = await _create_category(client, second_token, "Foreign")
    second_product = await _create_product(
        client,
        second_token,
        sku=f"report-foreign-{uuid4().hex[:8]}",
        name="Foreign Product",
        category_id=second_category["id"],
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
    await _create_inventory_item(
        client,
        second_token,
        product_id=second_product["id"],
        opening_stock="100.000",
        minimum_stock="1.000",
    )

    await _create_sale(
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
        product_id=healthy_product["id"],
        sale_date=date(2026, 7, 4),
        quantity="99.000",
    )
    await sales_repository.soft_delete_transaction(
        sales_repository.transactions_by_id[UUID(deleted_sale["id"])],
        deleted_reason="reports test",
    )
    await _create_sale(
        client,
        second_token,
        product_id=second_product["id"],
        sale_date=date(2026, 7, 1),
        quantity="50.000",
    )

    user_id = auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id
    second_user_id = auth_repository.users_by_email[SECOND_OWNER_PAYLOAD["email"]].id
    completed_run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={
            "horizon_days": 7,
            "status": "completed",
            "requested_at": now - timedelta(minutes=20),
            "completed_at": now - timedelta(minutes=18),
            "total_products": 3,
            "total_sales_records": 3,
            "run_metadata": {"model_name": "reports_model"},
        },
    )
    failed_run = await forecast_repository.create_forecast_run(
        user_id=user_id,
        values={
            "horizon_days": 7,
            "status": "failed",
            "requested_at": now - timedelta(minutes=5),
            "failed_at": now - timedelta(minutes=4),
            "failure_reason": "test failure",
        },
    )
    second_run = await forecast_repository.create_forecast_run(
        user_id=second_user_id,
        values={
            "horizon_days": 7,
            "status": "completed",
            "requested_at": now - timedelta(minutes=15),
            "completed_at": now - timedelta(minutes=14),
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
                "model_name": "reports_model",
            },
            {
                "product_id": UUID(out_product["id"]),
                "forecast_date": date(2026, 7, 11),
                "predicted_demand": Decimal("6.000"),
                "model_name": "reports_model",
            },
        ],
    )
    await forecast_repository.bulk_create_forecast_predictions(
        user_id=second_user_id,
        forecast_run_id=second_run.id,
        rows=[
            {
                "product_id": UUID(second_product["id"]),
                "forecast_date": date(2026, 7, 10),
                "predicted_demand": Decimal("99.000"),
                "model_name": "foreign_model",
            }
        ],
    )
    await forecast_repository.create_forecast_metrics(
        user_id=user_id,
        forecast_run_id=completed_run.id,
        values={
            "model_name": "reports_model",
            "mae": Decimal("1.0000"),
            "rmse": Decimal("2.0000"),
            "mape": Decimal("12.3400"),
            "training_rows": 30,
            "validation_rows": 6,
            "total_products": 3,
            "fallback_products": 0,
        },
    )
    await forecast_repository.create_forecast_metrics(
        user_id=second_user_id,
        forecast_run_id=second_run.id,
        values={
            "model_name": "foreign_model",
            "mae": Decimal("0.1000"),
            "rmse": Decimal("0.2000"),
            "mape": Decimal("1.0000"),
            "training_rows": 10,
            "validation_rows": 2,
            "total_products": 1,
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
                "reason": "Reports test",
                "status": "open",
                "generated_at": now - timedelta(minutes=17),
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
                "reason": "Reports test",
                "status": "open",
                "generated_at": now - timedelta(minutes=16),
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
                "reason": "Reports test",
                "status": "acknowledged",
                "generated_at": now - timedelta(minutes=15),
            },
        ],
    )
    await recommendation_repository.bulk_create_recommendations(
        user_id=second_user_id,
        rows=[
            {
                "forecast_run_id": second_run.id,
                "product_id": UUID(second_product["id"]),
                "predicted_demand": Decimal("99.000"),
                "current_stock": Decimal("100.000"),
                "minimum_stock": Decimal("1.000"),
                "safety_stock": Decimal("0.000"),
                "required_stock": Decimal("99.000"),
                "reorder_quantity": Decimal("0.000"),
                "stock_gap": Decimal("-1.000"),
                "risk_level": "low",
                "recommended_action": "no_reorder_needed",
                "reason": "Foreign",
                "status": "open",
                "generated_at": now - timedelta(minutes=10),
            }
        ],
    )
    return {
        "category": category,
        "second_category": second_category,
        "low_product": low_product,
        "out_product": out_product,
        "healthy_product": healthy_product,
        "second_product": second_product,
        "completed_run": completed_run,
        "failed_run": failed_run,
        "second_run": second_run,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/v1/reports/model-performance", {}),
        ("/api/v1/reports/inventory-risk", {}),
        ("/api/v1/reports/reorder-summary", {}),
        ("/api/v1/reports/demand-forecast", {"forecast_run_id": str(uuid4())}),
        ("/api/v1/reports/sales-summary", {}),
        ("/api/v1/reports/options", {}),
    ],
)
async def test_reports_require_auth(reports_client, path: str, params: dict) -> None:
    response = await reports_client.get(path, params=params)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_model_performance_report_is_user_scoped(
    reports_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(reports_client)
    second_token = await _register(reports_client, SECOND_OWNER_PAYLOAD)
    await _seed_reports_data(
        reports_client,
        access_token,
        second_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await reports_client.get(
        "/api/v1/reports/model-performance",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["total_forecast_runs"] == 2
    assert data["completed_forecast_runs"] == 1
    assert data["failed_forecast_runs"] == 1
    assert data["average_mape"] == "12.3400"
    assert data["best_run_by_mape"]["model_name"] == "reports_model"
    assert len(data["rows"]) == 1
    assert data["rows"][0]["model_name"] == "reports_model"


@pytest.mark.asyncio
async def test_model_performance_empty_state(reports_client) -> None:
    access_token = await _register(reports_client)

    response = await reports_client.get(
        "/api/v1/reports/model-performance",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["total_forecast_runs"] == 0
    assert data["average_mape"] is None
    assert data["best_run_by_mape"] is None
    assert data["rows"] == []


@pytest.mark.asyncio
async def test_inventory_risk_report_counts_scope_and_category_validation(
    reports_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(reports_client)
    second_token = await _register(reports_client, SECOND_OWNER_PAYLOAD)
    seeded = await _seed_reports_data(
        reports_client,
        access_token,
        second_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await reports_client.get(
        "/api/v1/reports/inventory-risk",
        headers=_auth_headers(access_token),
        params={"category_id": seeded["category"]["id"]},
    )
    low_response = await reports_client.get(
        "/api/v1/reports/inventory-risk",
        headers=_auth_headers(access_token),
        params={"stock_status": "low_stock"},
    )
    foreign_response = await reports_client.get(
        "/api/v1/reports/inventory-risk",
        headers=_auth_headers(access_token),
        params={"category_id": seeded["second_category"]["id"]},
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["total_inventory_items"] == 3
    assert data["low_stock_count"] == 1
    assert data["out_of_stock_count"] == 1
    assert data["healthy_stock_count"] == 1
    assert {row["product_name"] for row in data["rows"]} == {
        "Report Low Rice",
        "Report Out Flour",
        "Report Healthy Oil",
    }
    assert low_response.status_code == 200
    assert low_response.json()["data"]["total_inventory_items"] == 1
    assert foreign_response.status_code == 404
    assert foreign_response.json()["error"]["code"] == "report_category_not_found"


@pytest.mark.asyncio
async def test_reorder_summary_report_counts_and_forecast_validation(
    reports_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(reports_client)
    second_token = await _register(reports_client, SECOND_OWNER_PAYLOAD)
    seeded = await _seed_reports_data(
        reports_client,
        access_token,
        second_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await reports_client.get(
        "/api/v1/reports/reorder-summary",
        headers=_auth_headers(access_token),
        params={"forecast_run_id": str(seeded["completed_run"].id)},
    )
    critical_response = await reports_client.get(
        "/api/v1/reports/reorder-summary",
        headers=_auth_headers(access_token),
        params={"risk_level": "critical", "status": "open"},
    )
    foreign_response = await reports_client.get(
        "/api/v1/reports/reorder-summary",
        headers=_auth_headers(access_token),
        params={"forecast_run_id": str(seeded["second_run"].id)},
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["total_recommendations"] == 3
    assert data["open_recommendations"] == 2
    assert data["acknowledged_recommendations"] == 1
    assert data["critical_count"] == 1
    assert data["high_count"] == 1
    assert data["low_count"] == 1
    assert data["total_reorder_quantity"] == "14.000"
    assert data["top_reorder_items"][0]["product_name"] == "Report Low Rice"
    assert critical_response.status_code == 200
    assert critical_response.json()["data"]["total_recommendations"] == 1
    assert foreign_response.status_code == 404
    assert foreign_response.json()["error"]["code"] == "report_forecast_run_not_found"


@pytest.mark.asyncio
async def test_demand_forecast_report_filters_and_scopes_run(
    reports_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(reports_client)
    second_token = await _register(reports_client, SECOND_OWNER_PAYLOAD)
    seeded = await _seed_reports_data(
        reports_client,
        access_token,
        second_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await reports_client.get(
        "/api/v1/reports/demand-forecast",
        headers=_auth_headers(access_token),
        params={"forecast_run_id": str(seeded["completed_run"].id)},
    )
    product_response = await reports_client.get(
        "/api/v1/reports/demand-forecast",
        headers=_auth_headers(access_token),
        params={
            "forecast_run_id": str(seeded["completed_run"].id),
            "product_id": seeded["low_product"]["id"],
        },
    )
    foreign_response = await reports_client.get(
        "/api/v1/reports/demand-forecast",
        headers=_auth_headers(access_token),
        params={"forecast_run_id": str(seeded["second_run"].id)},
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["forecast_run_id"] == str(seeded["completed_run"].id)
    assert data["horizon_days"] == 7
    assert data["total_products"] == 2
    assert data["total_predicted_demand"] == "11.000"
    assert len(data["rows"]) == 2
    assert product_response.status_code == 200
    assert product_response.json()["data"]["total_products"] == 1
    assert product_response.json()["data"]["rows"][0]["product_name"] == (
        "Report Low Rice"
    )
    assert foreign_response.status_code == 404
    assert foreign_response.json()["error"]["code"] == "report_forecast_run_not_found"


@pytest.mark.asyncio
async def test_sales_summary_report_aggregates_and_excludes_deleted_or_foreign_sales(
    reports_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(reports_client)
    second_token = await _register(reports_client, SECOND_OWNER_PAYLOAD)
    seeded = await _seed_reports_data(
        reports_client,
        access_token,
        second_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await reports_client.get(
        "/api/v1/reports/sales-summary",
        headers=_auth_headers(access_token),
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )
    product_response = await reports_client.get(
        "/api/v1/reports/sales-summary",
        headers=_auth_headers(access_token),
        params={
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
            "product_id": seeded["low_product"]["id"],
        },
    )

    data = response.json()["data"]
    assert response.status_code == 200
    assert data["total_transactions"] == 3
    assert data["total_quantity_sold"] == "9.000"
    assert data["total_sales_amount"] == "90.00"
    assert data["unique_products_sold"] == 2
    assert {row["product_name"] for row in data["rows"]} == {
        "Report Low Rice",
        "Report Out Flour",
    }
    assert product_response.status_code == 200
    assert product_response.json()["data"]["total_transactions"] == 2
    assert product_response.json()["data"]["total_quantity_sold"] == "5.000"


@pytest.mark.asyncio
async def test_reports_options_returns_supported_metadata(reports_client) -> None:
    access_token = await _register(reports_client)

    response = await reports_client.get(
        "/api/v1/reports/options",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert "demand_forecast" in data["available_report_types"]
    assert data["supported_formats"] == ["json", "csv"]
    assert "critical" in data["supported_risk_levels"]
    assert "healthy" in data["supported_stock_statuses"]


@pytest.mark.asyncio
async def test_csv_export_is_text_csv_and_user_scoped(
    reports_client,
    auth_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> None:
    access_token = await _register(reports_client)
    second_token = await _register(reports_client, SECOND_OWNER_PAYLOAD)
    await _seed_reports_data(
        reports_client,
        access_token,
        second_token,
        auth_repository,
        sales_repository,
        forecast_repository,
        recommendation_repository,
    )

    response = await reports_client.get(
        "/api/v1/reports/sales-summary",
        headers=_auth_headers(access_token),
        params={
            "date_from": "2026-07-01",
            "date_to": "2026-07-31",
            "format": "csv",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment;" in response.headers["content-disposition"]
    assert "Report Low Rice" in response.text
    assert "Foreign Product" not in response.text


@pytest.mark.asyncio
async def test_reports_reject_invalid_format_and_date_range(reports_client) -> None:
    access_token = await _register(reports_client)

    format_response = await reports_client.get(
        "/api/v1/reports/sales-summary",
        headers=_auth_headers(access_token),
        params={"format": "pdf"},
    )
    date_response = await reports_client.get(
        "/api/v1/reports/sales-summary",
        headers=_auth_headers(access_token),
        params={"date_from": "2026-07-31", "date_to": "2026-07-01"},
    )

    assert format_response.status_code == 400
    assert format_response.json()["error"]["code"] == "invalid_report_format"
    assert date_response.status_code == 400
    assert date_response.json()["error"]["code"] == "invalid_report_date_range"
