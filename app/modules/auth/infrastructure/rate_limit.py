from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from redis.asyncio import Redis

from app.core.config import get_settings
from app.modules.auth.domain.exceptions import (
    AuthRateLimitExceededError,
    AuthRateLimitUnavailableError,
)

_INCREMENT_WITH_EXPIRY = """
local attempts = redis.call('INCR', KEYS[1])
if attempts == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return {attempts, redis.call('TTL', KEYS[1])}
"""


@dataclass(frozen=True, slots=True)
class RateLimitCounter:
    attempts: int
    retry_after_seconds: int


class AuthRateLimitStore(Protocol):
    async def increment(
        self,
        *,
        key: str,
        window_seconds: int,
    ) -> RateLimitCounter: ...


class RedisAuthRateLimitStore:
    def __init__(self, *, redis_url: str) -> None:
        self._client = Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    async def increment(
        self,
        *,
        key: str,
        window_seconds: int,
    ) -> RateLimitCounter:
        try:
            result = await self._client.eval(
                _INCREMENT_WITH_EXPIRY,
                1,
                key,
                window_seconds,
            )
            attempts, ttl = result
            return RateLimitCounter(
                attempts=int(attempts),
                retry_after_seconds=max(1, int(ttl)),
            )
        except Exception as exc:
            raise AuthRateLimitUnavailableError() from exc


class AuthRateLimiter:
    def __init__(
        self,
        *,
        store: AuthRateLimitStore,
        secret: str,
        enabled: bool,
        window_seconds: int,
        login_attempts_per_ip: int,
        login_attempts_per_account: int,
        registration_attempts_per_ip: int,
        refresh_attempts_per_ip: int,
    ) -> None:
        self._store = store
        self._secret = secret.encode("utf-8")
        self._enabled = enabled
        self._window_seconds = window_seconds
        self._login_attempts_per_ip = login_attempts_per_ip
        self._login_attempts_per_account = login_attempts_per_account
        self._registration_attempts_per_ip = registration_attempts_per_ip
        self._refresh_attempts_per_ip = refresh_attempts_per_ip

    async def enforce_login(self, *, client_ip: str | None, email: str) -> None:
        await self._enforce(
            ("login-ip", client_ip or "unknown", self._login_attempts_per_ip),
            ("login-account", email.strip().lower(), self._login_attempts_per_account),
        )

    async def enforce_registration(self, *, client_ip: str | None) -> None:
        await self._enforce(
            ("register-ip", client_ip or "unknown", self._registration_attempts_per_ip),
        )

    async def enforce_refresh(self, *, client_ip: str | None) -> None:
        await self._enforce(
            ("refresh-ip", client_ip or "unknown", self._refresh_attempts_per_ip),
        )

    async def _enforce(self, *limits: tuple[str, str, int]) -> None:
        if not self._enabled:
            return

        for scope, subject, maximum_attempts in limits:
            counter = await self._store.increment(
                key=self._key(scope=scope, subject=subject),
                window_seconds=self._window_seconds,
            )
            if counter.attempts > maximum_attempts:
                raise AuthRateLimitExceededError(counter.retry_after_seconds)

    def _key(self, *, scope: str, subject: str) -> str:
        digest = hmac.new(
            self._secret,
            f"{scope}:{subject}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"invora:rate-limit:auth:{scope}:{digest}"


@lru_cache
def get_auth_rate_limiter() -> AuthRateLimiter:
    settings = get_settings()
    return AuthRateLimiter(
        store=RedisAuthRateLimitStore(redis_url=settings.REDIS_URL),
        secret=settings.JWT_SECRET_KEY.get_secret_value(),
        enabled=settings.AUTH_RATE_LIMIT_ENABLED,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
        login_attempts_per_ip=settings.AUTH_LOGIN_MAX_ATTEMPTS_PER_IP,
        login_attempts_per_account=settings.AUTH_LOGIN_MAX_ATTEMPTS_PER_ACCOUNT,
        registration_attempts_per_ip=settings.AUTH_REGISTER_MAX_ATTEMPTS_PER_IP,
        refresh_attempts_per_ip=settings.AUTH_REFRESH_MAX_ATTEMPTS_PER_IP,
    )
