from decimal import Decimal
from uuid import UUID

import pytest

OWNER_PAYLOAD = {
    "email": "sales-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Sales Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "sales-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Sales Owner",
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


async def _create_transaction(
    client,
    access_token: str,
    product_id: str,
    *,
    sale_date: str = "2026-07-01",
    quantity: str = "2.000",
    unit_price: str = "12.50",
    channel: str = "store",
    customer_name: str = "Walk-in",
) -> dict:
    response = await client.post(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "sale_date": sale_date,
            "quantity": quantity,
            "unit_price": unit_price,
            "channel": channel,
            "customer_name": customer_name,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["transaction"]


async def _upload_csv(client, access_token: str, content: str):
    return await client.post(
        "/api/v1/sales/uploads",
        headers=_auth_headers(access_token),
        files={"file": ("sales.csv", content.encode("utf-8"), "text/csv")},
    )


@pytest.mark.asyncio
async def test_post_sales_transaction_requires_auth(sales_client) -> None:
    response = await sales_client.post(
        "/api/v1/sales/transactions",
        json={
            "product_id": "11111111-1111-1111-1111-111111111111",
            "sale_date": "2026-07-01",
            "quantity": "1.000",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_create_manual_sales_transaction_success(sales_client) -> None:
    access_token = await _register(sales_client)
    product = await _create_product(sales_client, access_token)

    transaction = await _create_transaction(
        sales_client,
        access_token,
        product["id"],
        quantity="3.000",
        unit_price="10.00",
    )

    assert transaction["source"] == "manual"
    assert transaction["total_amount"] == "30.00"
    assert transaction["product"]["sku"] == "MILK-1"


@pytest.mark.asyncio
async def test_create_manual_transaction_does_not_reduce_inventory_stock(
    sales_client,
    auth_repository,
    inventory_repository,
) -> None:
    from app.modules.inventory.application.service import InventoryService

    access_token = await _register(sales_client)
    product = await _create_product(sales_client, access_token)
    user_id = auth_repository.users_by_email[OWNER_PAYLOAD["email"]].id
    inventory_service = InventoryService(repository=inventory_repository)
    item = await inventory_service.create_inventory_item(
        user_id=user_id,
        product_id=UUID(product["id"]),
        values={"opening_stock": Decimal("10.000")},
    )

    await _create_transaction(sales_client, access_token, product["id"])

    assert item.current_stock == Decimal("10.000")
    assert len(inventory_repository.movements_by_id) == 1


@pytest.mark.asyncio
async def test_cannot_create_transaction_for_another_users_product(
    sales_client,
) -> None:
    first_token = await _register(sales_client)
    second_token = await _register(sales_client, SECOND_OWNER_PAYLOAD)
    product = await _create_product(sales_client, first_token)

    response = await sales_client.post(
        "/api/v1/sales/transactions",
        headers=_auth_headers(second_token),
        json={
            "product_id": product["id"],
            "sale_date": "2026-07-01",
            "quantity": "1.000",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sales_transaction_product_not_found"


@pytest.mark.asyncio
async def test_list_transactions_returns_only_current_user(sales_client) -> None:
    first_token = await _register(sales_client)
    second_token = await _register(sales_client, SECOND_OWNER_PAYLOAD)
    first_product = await _create_product(sales_client, first_token, sku="milk-1")
    second_product = await _create_product(sales_client, second_token, sku="rice-1")
    await _create_transaction(sales_client, first_token, first_product["id"])
    await _create_transaction(sales_client, second_token, second_product["id"])

    response = await sales_client.get(
        "/api/v1/sales/transactions",
        headers=_auth_headers(first_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_list_transactions_filters_by_product_date_and_source(
    sales_client,
) -> None:
    access_token = await _register(sales_client)
    milk = await _create_product(sales_client, access_token, sku="milk-1")
    rice = await _create_product(sales_client, access_token, sku="rice-1", name="Rice")
    await _create_transaction(
        sales_client,
        access_token,
        milk["id"],
        sale_date="2026-07-01",
    )
    await _create_transaction(
        sales_client,
        access_token,
        rice["id"],
        sale_date="2026-07-10",
    )

    response = await sales_client.get(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        params={
            "product_id": milk["id"],
            "date_from": "2026-07-01",
            "date_to": "2026-07-05",
            "source": "manual",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["transactions"][0]["product_id"] == milk["id"]


@pytest.mark.asyncio
async def test_get_transaction_detail_and_cross_user_access(sales_client) -> None:
    first_token = await _register(sales_client)
    second_token = await _register(sales_client, SECOND_OWNER_PAYLOAD)
    product = await _create_product(sales_client, first_token)
    transaction = await _create_transaction(sales_client, first_token, product["id"])

    own_response = await sales_client.get(
        f"/api/v1/sales/transactions/{transaction['id']}",
        headers=_auth_headers(first_token),
    )
    other_response = await sales_client.get(
        f"/api/v1/sales/transactions/{transaction['id']}",
        headers=_auth_headers(second_token),
    )

    assert own_response.status_code == 200
    assert other_response.status_code == 404


@pytest.mark.asyncio
async def test_patch_transaction_success_and_protected_field_rejection(
    sales_client,
) -> None:
    access_token = await _register(sales_client)
    product = await _create_product(sales_client, access_token)
    transaction = await _create_transaction(sales_client, access_token, product["id"])

    update_response = await sales_client.patch(
        f"/api/v1/sales/transactions/{transaction['id']}",
        headers=_auth_headers(access_token),
        json={"quantity": "4.000"},
    )
    protected_response = await sales_client.patch(
        f"/api/v1/sales/transactions/{transaction['id']}",
        headers=_auth_headers(access_token),
        json={"source": "api"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["data"]["transaction"]["total_amount"] == "50.00"
    assert protected_response.status_code == 400
    assert protected_response.json()["error"]["code"] == (
        "invalid_sales_transaction_field"
    )


@pytest.mark.asyncio
async def test_delete_transaction_soft_deletes_and_default_list_excludes_it(
    sales_client,
) -> None:
    access_token = await _register(sales_client)
    product = await _create_product(sales_client, access_token)
    transaction = await _create_transaction(sales_client, access_token, product["id"])

    delete_response = await sales_client.request(
        "DELETE",
        f"/api/v1/sales/transactions/{transaction['id']}",
        headers=_auth_headers(access_token),
        json={"deleted_reason": "Duplicate row"},
    )
    list_response = await sales_client.get(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
    )
    include_deleted_response = await sales_client.get(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        params={"include_deleted": "true"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["transaction"]["deleted_at"] is not None
    assert list_response.json()["data"]["total"] == 0
    assert include_deleted_response.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_summary_excludes_deleted_transactions(sales_client) -> None:
    access_token = await _register(sales_client)
    product = await _create_product(sales_client, access_token)
    kept = await _create_transaction(
        sales_client,
        access_token,
        product["id"],
        quantity="2.000",
        unit_price="10.00",
    )
    deleted = await _create_transaction(
        sales_client,
        access_token,
        product["id"],
        quantity="5.000",
        unit_price="10.00",
    )
    await sales_client.request(
        "DELETE",
        f"/api/v1/sales/transactions/{deleted['id']}",
        headers=_auth_headers(access_token),
    )

    response = await sales_client.get(
        "/api/v1/sales/transactions/summary",
        headers=_auth_headers(access_token),
    )

    assert kept["id"]
    assert response.status_code == 200
    assert response.json()["data"]["total_transactions"] == 1
    assert response.json()["data"]["total_quantity_sold"] == "2.000"
    assert response.json()["data"]["total_sales_amount"] == "20.00"


@pytest.mark.asyncio
async def test_trends_endpoint_aggregates_correctly(sales_client) -> None:
    access_token = await _register(sales_client)
    product = await _create_product(sales_client, access_token)
    await _create_transaction(
        sales_client,
        access_token,
        product["id"],
        sale_date="2026-07-01",
        quantity="2.000",
        unit_price="10.00",
    )
    await _create_transaction(
        sales_client,
        access_token,
        product["id"],
        sale_date="2026-07-01",
        quantity="3.000",
        unit_price="10.00",
    )

    response = await sales_client.get(
        "/api/v1/sales/transactions/trends",
        headers=_auth_headers(access_token),
        params={"interval": "day"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["trends"] == [
        {
            "period_start": "2026-07-01",
            "total_quantity": "5.000",
            "total_amount": "50.00",
            "transaction_count": 2,
        }
    ]


@pytest.mark.asyncio
async def test_by_product_endpoint_aggregates_correctly(sales_client) -> None:
    access_token = await _register(sales_client)
    milk = await _create_product(sales_client, access_token, sku="milk-1")
    rice = await _create_product(sales_client, access_token, sku="rice-1", name="Rice")
    await _create_transaction(sales_client, access_token, milk["id"], quantity="2.000")
    await _create_transaction(sales_client, access_token, rice["id"], quantity="5.000")

    response = await sales_client.get(
        "/api/v1/sales/transactions/by-product",
        headers=_auth_headers(access_token),
    )
    products = response.json()["data"]["products"]

    assert response.status_code == 200
    assert products[0]["sku"] == "RICE-1"
    assert products[0]["total_quantity"] == "5.000"
    assert products[1]["sku"] == "MILK-1"


@pytest.mark.asyncio
async def test_csv_upload_transactions_are_visible_in_transaction_list(
    sales_client,
) -> None:
    access_token = await _register(sales_client)
    await _create_product(sales_client, access_token)
    upload_response = await _upload_csv(
        sales_client,
        access_token,
        "sale_date,product_sku,quantity,unit_price\n"
        "2026-07-01,MILK-1,2.000,10.00\n",
    )

    response = await sales_client.get(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        params={"source": "csv_upload"},
    )

    assert upload_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["transactions"][0]["source"] == "csv_upload"
