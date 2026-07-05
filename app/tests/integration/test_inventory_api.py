from decimal import Decimal

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


async def _create_inventory_item(
    client,
    access_token: str,
    product_id: str,
    *,
    opening_stock: str = "10.000",
    minimum_stock: str = "5.000",
) -> dict:
    response = await client.post(
        "/api/v1/inventory/items",
        headers=_auth_headers(access_token),
        json={
            "product_id": product_id,
            "opening_stock": opening_stock,
            "minimum_stock": minimum_stock,
            "safety_stock": "2.000",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["item"]


@pytest.mark.asyncio
async def test_post_inventory_items_requires_auth(inventory_client) -> None:
    response = await inventory_client.post(
        "/api/v1/inventory/items",
        json={"product_id": "00000000-0000-0000-0000-000000000001"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_create_inventory_item_success(inventory_client) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)

    item = await _create_inventory_item(
        inventory_client,
        access_token,
        product["id"],
    )

    assert item["product_id"] == product["id"]
    assert Decimal(str(item["current_stock"])) == Decimal("10.000")
    assert item["product"]["sku"] == "MILK-1"


@pytest.mark.asyncio
async def test_duplicate_inventory_item_returns_409(inventory_client) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)
    await _create_inventory_item(inventory_client, access_token, product["id"])

    response = await inventory_client.post(
        "/api/v1/inventory/items",
        headers=_auth_headers(access_token),
        json={"product_id": product["id"]},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "inventory_item_already_exists"


@pytest.mark.asyncio
async def test_cannot_create_inventory_for_another_users_product(
    inventory_client,
) -> None:
    first_token = await _register(inventory_client)
    second_token = await _register(inventory_client, SECOND_OWNER_PAYLOAD)
    product = await _create_product(inventory_client, first_token)

    response = await inventory_client.post(
        "/api/v1/inventory/items",
        headers=_auth_headers(second_token),
        json={"product_id": product["id"]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "inventory_product_not_found"


@pytest.mark.asyncio
async def test_list_inventory_items_returns_only_current_user_inventory(
    inventory_client,
) -> None:
    first_token = await _register(inventory_client)
    second_token = await _register(inventory_client, SECOND_OWNER_PAYLOAD)
    first_product = await _create_product(inventory_client, first_token, sku="milk-1")
    second_product = await _create_product(inventory_client, second_token, sku="rice-1")
    await _create_inventory_item(inventory_client, first_token, first_product["id"])
    await _create_inventory_item(inventory_client, second_token, second_product["id"])

    response = await inventory_client.get(
        "/api/v1/inventory/items",
        headers=_auth_headers(first_token),
    )
    items = response.json()["data"]["items"]

    assert response.status_code == 200
    assert len(items) == 1
    assert items[0]["product"]["sku"] == "MILK-1"


@pytest.mark.asyncio
async def test_get_inventory_item_and_cross_user_access(inventory_client) -> None:
    first_token = await _register(inventory_client)
    second_token = await _register(inventory_client, SECOND_OWNER_PAYLOAD)
    product = await _create_product(inventory_client, first_token)
    await _create_inventory_item(inventory_client, first_token, product["id"])

    own_response = await inventory_client.get(
        f"/api/v1/inventory/items/{product['id']}",
        headers=_auth_headers(first_token),
    )
    other_response = await inventory_client.get(
        f"/api/v1/inventory/items/{product['id']}",
        headers=_auth_headers(second_token),
    )

    assert own_response.status_code == 200
    assert other_response.status_code == 404


@pytest.mark.asyncio
async def test_patch_thresholds_success_and_blocks_current_stock(
    inventory_client,
) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)
    await _create_inventory_item(inventory_client, access_token, product["id"])

    update_response = await inventory_client.patch(
        f"/api/v1/inventory/items/{product['id']}",
        headers=_auth_headers(access_token),
        json={"minimum_stock": "6.000", "safety_stock": "3.000"},
    )
    blocked_response = await inventory_client.patch(
        f"/api/v1/inventory/items/{product['id']}",
        headers=_auth_headers(access_token),
        json={"current_stock": "99.000"},
    )

    assert update_response.status_code == 200
    assert Decimal(str(update_response.json()["data"]["item"]["minimum_stock"])) == (
        Decimal("6.000")
    )
    assert blocked_response.status_code == 400
    assert blocked_response.json()["error"]["code"] == "invalid_inventory_field"


@pytest.mark.asyncio
async def test_stock_in_and_stock_out_movements_update_stock(inventory_client) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)
    await _create_inventory_item(inventory_client, access_token, product["id"])

    stock_in_response = await inventory_client.post(
        "/api/v1/inventory/movements",
        headers=_auth_headers(access_token),
        json={
            "product_id": product["id"],
            "movement_type": "stock_in",
            "quantity": "4.000",
        },
    )
    stock_out_response = await inventory_client.post(
        "/api/v1/inventory/movements",
        headers=_auth_headers(access_token),
        json={
            "product_id": product["id"],
            "movement_type": "stock_out",
            "quantity": "3.000",
        },
    )
    item_response = await inventory_client.get(
        f"/api/v1/inventory/items/{product['id']}",
        headers=_auth_headers(access_token),
    )

    assert stock_in_response.status_code == 201
    assert stock_out_response.status_code == 201
    assert Decimal(str(item_response.json()["data"]["item"]["current_stock"])) == (
        Decimal("11.000")
    )


@pytest.mark.asyncio
async def test_stock_out_beyond_current_stock_returns_conflict(
    inventory_client,
) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)
    await _create_inventory_item(
        inventory_client,
        access_token,
        product["id"],
        opening_stock="1.000",
    )

    response = await inventory_client.post(
        "/api/v1/inventory/movements",
        headers=_auth_headers(access_token),
        json={
            "product_id": product["id"],
            "movement_type": "stock_out",
            "quantity": "2.000",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"


@pytest.mark.asyncio
async def test_adjustment_sets_absolute_stock(inventory_client) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)
    await _create_inventory_item(inventory_client, access_token, product["id"])

    response = await inventory_client.post(
        "/api/v1/inventory/movements",
        headers=_auth_headers(access_token),
        json={
            "product_id": product["id"],
            "movement_type": "adjustment",
            "quantity": "7.500",
        },
    )

    assert response.status_code == 201
    movement = response.json()["data"]["movement"]
    assert Decimal(str(movement["quantity_delta"])) == Decimal("-2.500")
    assert Decimal(str(movement["quantity_after"])) == Decimal("7.500")


@pytest.mark.asyncio
async def test_every_stock_change_creates_movement_row(inventory_client) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)
    await _create_inventory_item(inventory_client, access_token, product["id"])
    await inventory_client.post(
        "/api/v1/inventory/movements",
        headers=_auth_headers(access_token),
        json={
            "product_id": product["id"],
            "movement_type": "stock_in",
            "quantity": "1.000",
        },
    )
    await inventory_client.post(
        "/api/v1/inventory/movements",
        headers=_auth_headers(access_token),
        json={
            "product_id": product["id"],
            "movement_type": "correction",
            "quantity": "-1.000",
        },
    )

    response = await inventory_client.get(
        "/api/v1/inventory/movements",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 3


@pytest.mark.asyncio
async def test_list_movements_returns_only_current_users_movements(
    inventory_client,
) -> None:
    first_token = await _register(inventory_client)
    second_token = await _register(inventory_client, SECOND_OWNER_PAYLOAD)
    first_product = await _create_product(inventory_client, first_token, sku="milk-1")
    second_product = await _create_product(inventory_client, second_token, sku="rice-1")
    await _create_inventory_item(inventory_client, first_token, first_product["id"])
    await _create_inventory_item(inventory_client, second_token, second_product["id"])

    response = await inventory_client.get(
        "/api/v1/inventory/movements",
        headers=_auth_headers(first_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_low_stock_endpoint_returns_correct_products(inventory_client) -> None:
    access_token = await _register(inventory_client)
    low_product = await _create_product(inventory_client, access_token, sku="low-1")
    healthy_product = await _create_product(
        inventory_client,
        access_token,
        sku="healthy-1",
        name="Healthy Milk",
    )
    await _create_inventory_item(
        inventory_client,
        access_token,
        low_product["id"],
        opening_stock="3.000",
        minimum_stock="5.000",
    )
    await _create_inventory_item(
        inventory_client,
        access_token,
        healthy_product["id"],
        opening_stock="10.000",
        minimum_stock="5.000",
    )

    response = await inventory_client.get(
        "/api/v1/inventory/low-stock",
        headers=_auth_headers(access_token),
    )
    items = response.json()["data"]["items"]

    assert response.status_code == 200
    assert len(items) == 1
    assert items[0]["product"]["sku"] == "LOW-1"


@pytest.mark.asyncio
async def test_summary_endpoint_returns_counts(inventory_client) -> None:
    access_token = await _register(inventory_client)
    product = await _create_product(inventory_client, access_token)
    await _create_inventory_item(
        inventory_client,
        access_token,
        product["id"],
        opening_stock="0.000",
        minimum_stock="5.000",
    )

    response = await inventory_client.get(
        "/api/v1/inventory/summary",
        headers=_auth_headers(access_token),
    )
    summary = response.json()["data"]

    assert response.status_code == 200
    assert summary["total_inventory_items"] == 1
    assert summary["total_products_tracked"] == 1
    assert summary["low_stock_count"] == 1
    assert summary["out_of_stock_count"] == 1
