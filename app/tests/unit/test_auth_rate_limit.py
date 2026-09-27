from __future__ import annotations

from collections import defaultdict

import pytest

from app.modules.auth.domain.exceptions import AuthRateLimitExceededError
from app.modules.auth.infrastructure.rate_limit import (
    AuthRateLimiter,
    RateLimitCounter,
)


class InMemoryRateLimitStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self._attempts: defaultdict[str, int] = defaultdict(int)

    async def increment(
        self,
        *,
        key: str,
        window_seconds: int,
    ) -> RateLimitCounter:
        self.calls.append((key, window_seconds))
        self._attempts[key] += 1
        return RateLimitCounter(
            attempts=self._attempts[key],
            retry_after_seconds=120,
        )


def build_limiter(
    store: InMemoryRateLimitStore,
    *,
    enabled: bool = True,
    login_attempts_per_ip: int = 2,
    login_attempts_per_account: int = 2,
) -> AuthRateLimiter:
    return AuthRateLimiter(
        store=store,
        secret="test-rate-limit-secret",
        enabled=enabled,
        window_seconds=120,
        login_attempts_per_ip=login_attempts_per_ip,
        login_attempts_per_account=login_attempts_per_account,
        registration_attempts_per_ip=2,
        refresh_attempts_per_ip=2,
    )


@pytest.mark.asyncio
async def test_login_limits_by_hashed_ip_and_normalized_account() -> None:
    store = InMemoryRateLimitStore()
    limiter = build_limiter(store, login_attempts_per_account=1)

    await limiter.enforce_login(client_ip="203.0.113.8", email="Owner@Example.com")

    with pytest.raises(AuthRateLimitExceededError) as raised:
        await limiter.enforce_login(client_ip="203.0.113.8", email="owner@example.com")

    assert raised.value.code == "authentication_rate_limited"
    assert raised.value.headers == {"Retry-After": "120"}
    keys = [key for key, _ in store.calls]
    assert all("203.0.113.8" not in key for key in keys)
    assert all("owner@example.com" not in key.lower() for key in keys)
    assert keys[1] == keys[3]


@pytest.mark.asyncio
async def test_disabled_rate_limiter_does_not_touch_the_store() -> None:
    store = InMemoryRateLimitStore()
    limiter = build_limiter(store, enabled=False)

    await limiter.enforce_registration(client_ip="203.0.113.8")
    await limiter.enforce_refresh(client_ip="203.0.113.8")

    assert store.calls == []


@pytest.mark.asyncio
async def test_registration_limit_uses_a_separate_scope() -> None:
    store = InMemoryRateLimitStore()
    limiter = build_limiter(store)

    await limiter.enforce_registration(client_ip="203.0.113.8")
    await limiter.enforce_login(client_ip="203.0.113.8", email="owner@example.com")

    keys = [key for key, _ in store.calls]
    assert "register-ip" in keys[0]
    assert "login-ip" in keys[1]
