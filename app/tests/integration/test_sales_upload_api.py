from decimal import Decimal
from uuid import UUID

import pytest

OWNER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Owner User",
}
SECOND_OWNER_PAYLOAD = {
    "email": "second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Owner",
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


async def _upload_csv(
    client,
    access_token: str,
    content: str,
    *,
    filename: str = "sales.csv",
):
    return await client.post(
        "/api/v1/sales/uploads",
        headers=_auth_headers(access_token),
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
    )


@pytest.mark.asyncio
async def test_post_sales_upload_requires_auth(sales_client) -> None:
    response = await sales_client.post(
        "/api/v1/sales/uploads",
        files={"file": ("sales.csv", b"sale_date,product_sku,quantity\n", "text/csv")},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_upload_valid_csv_succeeds(sales_client, sales_repository) -> None:
    access_token = await _register(sales_client)
    await _create_product(sales_client, access_token)

    response = await _upload_csv(
        sales_client,
        access_token,
        "sale_date,product_sku,quantity,unit_price\n"
        "2026-07-01, milk 1 ,2.000,12.50\n",
    )
    upload = response.json()["data"]["upload"]

    assert response.status_code == 201
    assert upload["status"] == "completed"
    assert upload["accepted_rows"] == 1
    assert upload["rejected_rows"] == 0
    assert len(sales_repository.transactions_by_id) == 1
    transaction = next(iter(sales_repository.transactions_by_id.values()))
    assert transaction.total_amount == Decimal("25.00")


@pytest.mark.asyncio
async def test_upload_missing_required_columns_returns_400(sales_client) -> None:
    access_token = await _register(sales_client)

    response = await _upload_csv(
        sales_client,
        access_token,
        "sale_date,product_sku\n2026-07-01,MILK-1\n",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "missing_sales_csv_columns"


@pytest.mark.asyncio
async def test_upload_mixed_rows_persists_transactions_and_rejections(
    sales_client,
    sales_repository,
) -> None:
    access_token = await _register(sales_client)
    await _create_product(sales_client, access_token)

    response = await _upload_csv(
        sales_client,
        access_token,
        "sale_date,product_sku,quantity,unit_price\n"
        "2026-07-01,MILK-1,2.000,10.00\n"
        "2026-07-02,MILK-1,-1.000,10.00\n"
        "2026-07-03,UNKNOWN,5.000,10.00\n",
    )
    upload = response.json()["data"]["upload"]

    assert response.status_code == 201
    assert upload["status"] == "completed_with_errors"
    assert upload["accepted_rows"] == 1
    assert upload["rejected_rows"] == 2
    assert len(sales_repository.transactions_by_id) == 1
    assert len(sales_repository.rejected_rows_by_id) == 2


@pytest.mark.asyncio
async def test_upload_unknown_sku_rejects_only_affected_rows(sales_client) -> None:
    access_token = await _register(sales_client)
    await _create_product(sales_client, access_token, sku="milk-1")

    response = await _upload_csv(
        sales_client,
        access_token,
        "sale_date,product_sku,quantity\n"
        "2026-07-01,MILK-1,2.000\n"
        "2026-07-02,RICE-1,5.000\n",
    )
    upload = response.json()["data"]["upload"]

    assert response.status_code == 201
    assert upload["accepted_rows"] == 1
    assert upload["rejected_rows"] == 1


@pytest.mark.asyncio
async def test_upload_cannot_create_records_for_another_users_product(
    sales_client,
    sales_repository,
) -> None:
    first_token = await _register(sales_client)
    second_token = await _register(sales_client, SECOND_OWNER_PAYLOAD)
    await _create_product(sales_client, first_token, sku="milk-1")

    response = await _upload_csv(
        sales_client,
        second_token,
        "sale_date,product_sku,quantity\n2026-07-01,MILK-1,2.000\n",
    )
    upload = response.json()["data"]["upload"]

    assert response.status_code == 201
    assert upload["accepted_rows"] == 0
    assert upload["rejected_rows"] == 1
    assert len(sales_repository.transactions_by_id) == 0


@pytest.mark.asyncio
async def test_duplicate_file_upload_returns_409(sales_client) -> None:
    access_token = await _register(sales_client)
    await _create_product(sales_client, access_token)
    content = "sale_date,product_sku,quantity\n2026-07-01,MILK-1,2.000\n"
    first_response = await _upload_csv(sales_client, access_token, content)
    second_response = await _upload_csv(sales_client, access_token, content)

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["error"]["code"] == "duplicate_sales_upload"


@pytest.mark.asyncio
async def test_list_uploads_returns_only_current_users_uploads(sales_client) -> None:
    first_token = await _register(sales_client)
    second_token = await _register(sales_client, SECOND_OWNER_PAYLOAD)
    await _create_product(sales_client, first_token, sku="milk-1")
    await _create_product(sales_client, second_token, sku="rice-1")
    await _upload_csv(
        sales_client,
        first_token,
        "sale_date,product_sku,quantity\n2026-07-01,MILK-1,2.000\n",
    )
    await _upload_csv(
        sales_client,
        second_token,
        "sale_date,product_sku,quantity\n2026-07-01,RICE-1,2.000\n",
    )

    response = await sales_client.get(
        "/api/v1/sales/uploads",
        headers=_auth_headers(first_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_get_upload_detail_and_cross_user_access(sales_client) -> None:
    first_token = await _register(sales_client)
    second_token = await _register(sales_client, SECOND_OWNER_PAYLOAD)
    await _create_product(sales_client, first_token)
    upload_response = await _upload_csv(
        sales_client,
        first_token,
        "sale_date,product_sku,quantity\n2026-07-01,MILK-1,2.000\n",
    )
    upload_id = upload_response.json()["data"]["upload"]["id"]

    own_response = await sales_client.get(
        f"/api/v1/sales/uploads/{upload_id}",
        headers=_auth_headers(first_token),
    )
    other_response = await sales_client.get(
        f"/api/v1/sales/uploads/{upload_id}",
        headers=_auth_headers(second_token),
    )

    assert own_response.status_code == 200
    assert other_response.status_code == 404


@pytest.mark.asyncio
async def test_rejected_rows_returns_only_owned_upload_rows(sales_client) -> None:
    access_token = await _register(sales_client)
    await _create_product(sales_client, access_token)
    upload_response = await _upload_csv(
        sales_client,
        access_token,
        "sale_date,product_sku,quantity\n2026-07-01,UNKNOWN,2.000\n",
    )
    upload_id = upload_response.json()["data"]["upload"]["id"]

    response = await sales_client.get(
        f"/api/v1/sales/uploads/{upload_id}/rejected-rows",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["rejected_rows"][0]["error_code"] == (
        "unknown_product_sku"
    )


@pytest.mark.asyncio
async def test_template_returns_expected_columns(sales_client) -> None:
    access_token = await _register(sales_client)

    response = await sales_client.get(
        "/api/v1/sales/uploads/template",
        headers=_auth_headers(access_token),
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["required_columns"] == ["sale_date", "product_sku", "quantity"]
    assert "unit_price" in data["optional_columns"]


@pytest.mark.asyncio
async def test_sales_upload_does_not_reduce_inventory_stock(
    sales_client,
    auth_repository,
    inventory_repository,
) -> None:
    from app.modules.inventory.application.service import InventoryService

    access_token = await _register(sales_client)
    product = await _create_product(sales_client, access_token)
    user_id = auth_repository.users_by_email["owner@example.com"].id
    inventory_service = InventoryService(repository=inventory_repository)
    item = await inventory_service.create_inventory_item(
        user_id=user_id,
        product_id=UUID(product["id"]),
        values={"opening_stock": Decimal("10.000")},
    )

    response = await _upload_csv(
        sales_client,
        access_token,
        "sale_date,product_sku,quantity\n2026-07-01,MILK-1,3.000\n",
    )

    assert response.status_code == 201
    assert item.current_stock == Decimal("10.000")
    assert len(inventory_repository.movements_by_id) == 1
