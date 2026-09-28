import pytest

from app.modules.auth.domain.exceptions import AuthRateLimitExceededError

REFRESH_COOKIE_NAME = "invora_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"
AUTH_ORIGIN = "http://localhost:3000"
REGISTER_PAYLOAD = {
    "email": "owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Owner User",
}


def assert_refresh_cookie(response) -> None:
    cookie = response.headers["set-cookie"]

    assert REFRESH_COOKIE_NAME in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=1209600" in cookie
    assert "Secure" not in cookie


def assert_access_only_tokens(body: dict[str, object]) -> None:
    tokens = body["data"]["tokens"]
    assert isinstance(tokens, dict)
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert "refresh_token" not in tokens


@pytest.mark.asyncio
async def test_register_success_sets_http_only_refresh_cookie(auth_client) -> None:
    response = await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    body = response.json()

    assert response.status_code == 201
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "owner@example.com"
    assert_access_only_tokens(body)
    assert_refresh_cookie(response)


@pytest.mark.asyncio
async def test_duplicate_register_returns_409(auth_client) -> None:
    await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_email"


@pytest.mark.asyncio
async def test_register_rejects_weak_password(auth_client) -> None:
    response = await auth_client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "weak"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "weak_password"


@pytest.mark.asyncio
async def test_login_success_sets_http_only_refresh_cookie(auth_client) -> None:
    await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "StrongPass1!"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "owner@example.com"
    assert_access_only_tokens(body)
    assert_refresh_cookie(response)


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
async def test_login_rate_limit_returns_safe_error_and_retry_after(
    app,
    auth_client,
) -> None:
    from app.modules.auth.infrastructure.rate_limit import get_auth_rate_limiter

    class RejectingRateLimiter:
        async def enforce_login(self, *, client_ip: str | None, email: str) -> None:
            raise AuthRateLimitExceededError(45)

    app.dependency_overrides[get_auth_rate_limiter] = lambda: RejectingRateLimiter()

    response = await auth_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "StrongPass1!"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "45"
    assert response.json() == {
        "success": False,
        "error": {
            "code": "authentication_rate_limited",
            "message": "Too many authentication attempts. Please try again later.",
        },
    }


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
        headers={"Authorization": "Bearer " + access_token},
    )

    assert response.status_code == 200
    assert response.json()["data"]["user"]["email"] == "owner@example.com"


@pytest.mark.asyncio
async def test_refresh_rotates_cookie_and_rejects_the_previous_token(
    auth_client,
) -> None:
    await auth_client.post(
        "/api/v1/auth/register",
        json=REGISTER_PAYLOAD,
    )
    old_refresh_token = auth_client.cookies.get(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )
    assert old_refresh_token is not None

    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": AUTH_ORIGIN},
    )
    body = refresh_response.json()

    assert refresh_response.status_code == 200
    assert_access_only_tokens(body)
    assert_refresh_cookie(refresh_response)
    assert (
        auth_client.cookies.get(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
        != old_refresh_token
    )

    auth_client.cookies.clear()
    reuse_response = await auth_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Cookie": REFRESH_COOKIE_NAME + "=" + old_refresh_token,
            "Origin": AUTH_ORIGIN,
        },
    )
    assert reuse_response.status_code == 401
    assert reuse_response.json()["error"]["code"] == "revoked_refresh_token"
    assert "Max-Age=0" in reuse_response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_safe_error_and_clears_cookie(
    auth_client,
) -> None:
    response = await auth_client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": AUTH_ORIGIN},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_refresh_token"
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_logout_revokes_cookie_session_and_is_idempotent(auth_client) -> None:
    await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    refresh_token = auth_client.cookies.get(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )
    assert refresh_token is not None

    logout_response = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": AUTH_ORIGIN},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["data"]["message"] == "Logged out successfully."
    assert "Max-Age=0" in logout_response.headers["set-cookie"]

    repeated_logout_response = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": AUTH_ORIGIN},
    )
    assert repeated_logout_response.status_code == 200

    auth_client.cookies.clear()
    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Cookie": REFRESH_COOKIE_NAME + "=" + refresh_token,
            "Origin": AUTH_ORIGIN,
        },
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "revoked_refresh_token"


@pytest.mark.asyncio
async def test_auth_cors_preflight_allows_configured_frontend_origin(
    auth_client,
) -> None:
    response = await auth_client.options(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_auth_cors_does_not_grant_credentials_to_an_untrusted_origin(
    auth_client,
) -> None:
    response = await auth_client.options(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "https://malicious.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cookie_auth_mutations_require_a_configured_origin(auth_client) -> None:
    await auth_client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    original_token = auth_client.cookies.get(
        REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
    )

    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": "https://malicious.example"},
    )
    logout_response = await auth_client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "https://malicious.example"},
    )

    assert original_token is not None
    assert refresh_response.status_code == 403
    assert refresh_response.json()["error"]["code"] == "invalid_auth_request_origin"
    assert logout_response.status_code == 403
    assert logout_response.json()["error"]["code"] == "invalid_auth_request_origin"
    assert auth_client.cookies.get(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH) == (
        original_token
    )

    trusted_response = await auth_client.post(
        "/api/v1/auth/refresh",
        headers={"Origin": AUTH_ORIGIN},
    )
    assert trusted_response.status_code == 200
