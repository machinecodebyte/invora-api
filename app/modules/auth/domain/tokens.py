from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.security import JWT_ALGORITHM
from app.modules.auth.domain.exceptions import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
)

ACCESS_TOKEN_TYPE = "access"


@dataclass(frozen=True, slots=True)
class AccessTokenPayload:
    subject: UUID
    expires_at: datetime


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _json_encode(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def create_access_token(
    *,
    subject: UUID,
    secret: str,
    expires_delta: timedelta,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + expires_delta
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(subject),
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    encoded_header = _base64url_encode(_json_encode(header))
    encoded_payload = _base64url_encode(_json_encode(payload))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(
    token: str,
    *,
    secret: str,
    now: datetime | None = None,
) -> AccessTokenPayload:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise InvalidAccessTokenError() from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()

    try:
        actual_signature = _base64url_decode(encoded_signature)
    except Exception as exc:
        raise InvalidAccessTokenError() from exc

    if not hmac.compare_digest(actual_signature, expected_signature):
        raise InvalidAccessTokenError()

    try:
        header = json.loads(_base64url_decode(encoded_header))
        payload = json.loads(_base64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise InvalidAccessTokenError() from exc

    if header.get("alg") != JWT_ALGORITHM or payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidAccessTokenError()

    expires_at_raw = payload.get("exp")
    subject_raw = payload.get("sub")
    if not isinstance(expires_at_raw, int) or not isinstance(subject_raw, str):
        raise InvalidAccessTokenError()

    current_time = now or datetime.now(UTC)
    expires_at = datetime.fromtimestamp(expires_at_raw, UTC)
    if expires_at <= current_time:
        raise ExpiredAccessTokenError()

    try:
        subject = UUID(subject_raw)
    except ValueError as exc:
        raise InvalidAccessTokenError() from exc

    return AccessTokenPayload(subject=subject, expires_at=expires_at)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str, *, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
