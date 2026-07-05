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


async def _create_category(client, access_token: str, name: str = "Beverages") -> dict:
    response = await client.post(
        "/api/v1/products/categories",
        headers=_auth_headers(access_token),
        json={"name": name, "description": "Catalog group"},
    )
    assert response.status_code == 201
    return response.json()["data"]["category"]


async def _create_product(
    client,
    access_token: str,
    *,
    sku: str = "milk-1",
    name: str = "Milk",
    category_id: str | None = None,
) -> dict:
    payload = {
        "name": name,
        "sku": sku,
        "category_id": category_id,
        "description": "Daily item",
        "unit": "liter",
        "selling_price": "12.50",
        "cost_price": "9.25",
    }
    response = await client.post(
        "/api/v1/products",
        headers=_auth_headers(access_token),
        json=payload,
    )
    assert response.status_code == 201
    return response.json()["data"]["product"]


@pytest.mark.asyncio
async def test_post_products_requires_auth(product_client) -> None:
    response = await product_client.post(
        "/api/v1/products",
        json={"name": "Milk", "sku": "milk-1", "unit": "liter"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_create_product_success(product_client) -> None:
    access_token = await _register(product_client)
    product = await _create_product(product_client, access_token)

    assert product["name"] == "Milk"
    assert product["sku"] == "MILK-1"
    assert product["unit"] == "liter"
    assert Decimal(str(product["selling_price"])) == Decimal("12.50")
    assert product["is_active"] is True
    assert "current_stock" not in product


@pytest.mark.asyncio
async def test_duplicate_sku_for_same_user_returns_409(product_client) -> None:
    access_token = await _register(product_client)
    await _create_product(product_client, access_token, sku="milk-1")

    response = await product_client.post(
        "/api/v1/products",
        headers=_auth_headers(access_token),
        json={"name": "Milk Two", "sku": " MILK 1 ", "unit": "liter"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_product_sku"


@pytest.mark.asyncio
async def test_same_sku_for_different_users_is_allowed(product_client) -> None:
    first_token = await _register(product_client)
    second_token = await _register(product_client, SECOND_OWNER_PAYLOAD)
    await _create_product(product_client, first_token, sku="milk-1")

    product = await _create_product(product_client, second_token, sku="milk-1")

    assert product["sku"] == "MILK-1"


@pytest.mark.asyncio
async def test_list_products_returns_only_current_users_products(
    product_client,
) -> None:
    first_token = await _register(product_client)
    second_token = await _register(product_client, SECOND_OWNER_PAYLOAD)
    await _create_product(product_client, first_token, sku="milk-1", name="Milk")
    await _create_product(product_client, second_token, sku="rice-1", name="Rice")

    response = await product_client.get(
        "/api/v1/products",
        headers=_auth_headers(first_token),
    )
    products = response.json()["data"]["products"]

    assert response.status_code == 200
    assert len(products) == 1
    assert products[0]["name"] == "Milk"


@pytest.mark.asyncio
async def test_search_filter_and_pagination(product_client) -> None:
    access_token = await _register(product_client)
    category = await _create_category(product_client, access_token, name="Dairy")
    await _create_product(
        product_client,
        access_token,
        sku="milk-1",
        name="Milk",
        category_id=category["id"],
    )
    await _create_product(product_client, access_token, sku="rice-1", name="Rice")

    response = await product_client.get(
        "/api/v1/products",
        headers=_auth_headers(access_token),
        params={
            "search": "milk",
            "category_id": category["id"],
            "limit": 1,
            "offset": 0,
        },
    )
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["total"] == 1
    assert data["products"][0]["sku"] == "MILK-1"


@pytest.mark.asyncio
async def test_get_product_and_cross_user_access(product_client) -> None:
    first_token = await _register(product_client)
    second_token = await _register(product_client, SECOND_OWNER_PAYLOAD)
    product = await _create_product(product_client, first_token)

    own_response = await product_client.get(
        f"/api/v1/products/{product['id']}",
        headers=_auth_headers(first_token),
    )
    other_response = await product_client.get(
        f"/api/v1/products/{product['id']}",
        headers=_auth_headers(second_token),
    )

    assert own_response.status_code == 200
    assert other_response.status_code == 404
    assert other_response.json()["error"]["code"] == "product_not_found"


@pytest.mark.asyncio
async def test_update_product_success_and_blocks_stock_field(product_client) -> None:
    access_token = await _register(product_client)
    product = await _create_product(product_client, access_token)

    update_response = await product_client.patch(
        f"/api/v1/products/{product['id']}",
        headers=_auth_headers(access_token),
        json={"name": "Fresh Milk", "selling_price": "13.00"},
    )
    blocked_response = await product_client.patch(
        f"/api/v1/products/{product['id']}",
        headers=_auth_headers(access_token),
        json={"current_stock": 50},
    )

    assert update_response.status_code == 200
    assert update_response.json()["data"]["product"]["name"] == "Fresh Milk"
    assert blocked_response.status_code == 400
    assert blocked_response.json()["error"]["code"] == "invalid_product_field"


@pytest.mark.asyncio
async def test_update_sku_duplicate_returns_409(product_client) -> None:
    access_token = await _register(product_client)
    first = await _create_product(product_client, access_token, sku="milk-1")
    await _create_product(product_client, access_token, sku="rice-1", name="Rice")

    response = await product_client.patch(
        f"/api/v1/products/{first['id']}",
        headers=_auth_headers(access_token),
        json={"sku": "rice-1"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_product_sku"


@pytest.mark.asyncio
async def test_archive_product_success(product_client) -> None:
    access_token = await _register(product_client)
    product = await _create_product(product_client, access_token)

    response = await product_client.delete(
        f"/api/v1/products/{product['id']}",
        headers=_auth_headers(access_token),
    )
    get_response = await product_client.get(
        f"/api/v1/products/{product['id']}",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["message"] == "Product archived."
    assert get_response.json()["data"]["product"]["is_active"] is False


@pytest.mark.asyncio
async def test_category_crud_and_active_product_archive_conflict(
    product_client,
) -> None:
    access_token = await _register(product_client)
    category = await _create_category(product_client, access_token, name="Dairy")

    duplicate_response = await product_client.post(
        "/api/v1/products/categories",
        headers=_auth_headers(access_token),
        json={"name": " dairy "},
    )
    list_response = await product_client.get(
        "/api/v1/products/categories",
        headers=_auth_headers(access_token),
    )
    update_response = await product_client.patch(
        f"/api/v1/products/categories/{category['id']}",
        headers=_auth_headers(access_token),
        json={"name": "Cold Dairy"},
    )
    await _create_product(
        product_client,
        access_token,
        category_id=category["id"],
    )
    archive_response = await product_client.delete(
        f"/api/v1/products/categories/{category['id']}",
        headers=_auth_headers(access_token),
    )

    assert duplicate_response.status_code == 409
    assert list_response.status_code == 200
    assert list_response.json()["data"]["total"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["data"]["category"]["name"] == "Cold Dairy"
    assert archive_response.status_code == 409
    assert archive_response.json()["error"]["code"] == (
        "product_category_has_active_products"
    )


@pytest.mark.asyncio
async def test_units_api_returns_allowed_units(product_client) -> None:
    access_token = await _register(product_client)

    response = await product_client.get(
        "/api/v1/products/units",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["units"] == [
        "pcs",
        "kg",
        "gram",
        "liter",
        "ml",
        "box",
        "packet",
        "dozen",
    ]
