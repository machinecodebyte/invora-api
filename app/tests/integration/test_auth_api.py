import pytest

REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Owner User",
}


@pytest.mark.asyncio
async def test_register_success(auth_client) -> None:
    response = await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    body = response.json()

    assert response.status_code == 201
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "owner@example.com"
    assert body["data"]["tokens"]["token_type"] == "bearer"
    assert body["data"]["tokens"]["access_token"]
    assert body["data"]["tokens"]["refresh_token"]


@pytest.mark.asyncio
async def test_duplicate_register_returns_409(auth_client) -> None:
    await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"


@pytest.mark.asyncio
async def test_login_success(auth_client) -> None:
    await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "StrongPass1!"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "owner@example.com"
    assert body["data"]["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_login_invalid_password_returns_401(auth_client) -> None:
    await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "WrongPass1!"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(auth_client) -> None:
    response = await auth_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user(auth_client) -> None:
    register_response = await auth_client.post(
        "/api/v1/auth/register",
        json=REGISTER_PAYLOAD,
    )
    access_token = register_response.json()["data"]["tokens"]["access_token"]

    response = await auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["user"]["email"] == "owner@example.com"


@pytest.mark.asyncio
async def test_refresh_returns_rotated_tokens(auth_client) -> None:
    register_response = await auth_client.post(
        "/api/v1/auth/register",
        json=REGISTER_PAYLOAD,
    )
    old_refresh_token = register_response.json()["data"]["tokens"]["refresh_token"]

    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    body = refresh_response.json()

    assert refresh_response.status_code == 200
    assert body["data"]["tokens"]["refresh_token"] != old_refresh_token

    reuse_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "revoked_refresh_token"


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(auth_client) -> None:
    register_response = await auth_client.post(
        "/api/v1/auth/register",
        json=REGISTER_PAYLOAD,
    )
    refresh_token = register_response.json()["data"]["tokens"]["refresh_token"]

    logout_response = await auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["data"]["message"] == "Logged out successfully."

    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "revoked_refresh_token"
