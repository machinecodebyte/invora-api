import pytest

REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Owner User",
}


async def _register(auth_client) -> dict:
    response = await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    return response.json()["data"]


@pytest.mark.asyncio
async def test_get_users_me_without_token_returns_401(auth_client) -> None:
    response = await auth_client.get("/api/v1/users/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_get_users_me_with_token_returns_current_profile(auth_client) -> None:
    data = await _register(auth_client)
    access_token = data["tokens"]["access_token"]

    response = await auth_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["profile"]["email"] == "owner@example.com"
    assert "hashed_password" not in body["data"]["profile"]


@pytest.mark.asyncio
async def test_patch_users_me_updates_allowed_fields(auth_client) -> None:
    data = await _register(auth_client)
    access_token = data["tokens"]["access_token"]

    response = await auth_client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "full_name": "  Updated   Owner ",
            "phone_number": "+91 98765 43210",
            "avatar_url": "https://example.com/avatar.png",
            "timezone": "Asia/Kolkata",
            "locale": "en_IN",
        },
    )
    profile = response.json()["data"]["profile"]

    assert response.status_code == 200
    assert profile["full_name"] == "Updated Owner"
    assert profile["phone_number"] == "+91 98765 43210"
    assert profile["avatar_url"] == "https://example.com/avatar.png"
    assert profile["timezone"] == "Asia/Kolkata"
    assert profile["locale"] == "en-IN"


@pytest.mark.asyncio
async def test_patch_users_me_cannot_update_protected_fields(auth_client) -> None:
    data = await _register(auth_client)
    access_token = data["tokens"]["access_token"]

    response = await auth_client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"email": "new@example.com"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_profile_update"


@pytest.mark.asyncio
async def test_change_password_succeeds_with_correct_current_password(
    auth_client,
) -> None:
    data = await _register(auth_client)
    access_token = data["tokens"]["access_token"]

    response = await auth_client.post(
        "/api/v1/users/me/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "StrongPass1!",
            "new_password": "NewStrong1!",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["message"] == "Password changed successfully."


@pytest.mark.asyncio
async def test_change_password_fails_with_wrong_current_password(auth_client) -> None:
    data = await _register(auth_client)
    access_token = data["tokens"]["access_token"]

    response = await auth_client.post(
        "/api/v1/users/me/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "WrongPass1!",
            "new_password": "NewStrong1!",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_current_password"


@pytest.mark.asyncio
async def test_login_password_behavior_after_password_change(auth_client) -> None:
    data = await _register(auth_client)
    access_token = data["tokens"]["access_token"]

    change_response = await auth_client.post(
        "/api/v1/users/me/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "StrongPass1!",
            "new_password": "NewStrong1!",
        },
    )
    assert change_response.status_code == 200

    old_login_response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "StrongPass1!"},
    )
    assert old_login_response.status_code == 401

    new_login_response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "NewStrong1!"},
    )
    assert new_login_response.status_code == 200
    assert new_login_response.json()["data"]["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_refresh_token_reuse_after_password_change_fails(auth_client) -> None:
    data = await _register(auth_client)
    access_token = data["tokens"]["access_token"]
    refresh_token = data["tokens"]["refresh_token"]

    change_response = await auth_client.post(
        "/api/v1/users/me/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "current_password": "StrongPass1!",
            "new_password": "NewStrong1!",
        },
    )
    assert change_response.status_code == 200

    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "revoked_refresh_token"
