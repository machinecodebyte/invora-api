from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.auth.domain.exceptions import ExpiredAccessTokenError
from app.modules.auth.domain.tokens import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


def test_access_token_creation_and_validation() -> None:
    subject = uuid4()
    now = datetime(2026, 7, 5, tzinfo=UTC)
    token = create_access_token(
        subject=subject,
        secret="test-secret-key-for-foundation",
        expires_delta=timedelta(minutes=30),
        now=now,
    )

    payload = decode_access_token(
        token,
        secret="test-secret-key-for-foundation",
        now=now + timedelta(minutes=1),
    )

    assert payload.subject == subject


def test_expired_access_token_is_rejected() -> None:
    now = datetime(2026, 7, 5, tzinfo=UTC)
    token = create_access_token(
        subject=uuid4(),
        secret="test-secret-key-for-foundation",
        expires_delta=timedelta(minutes=1),
        now=now,
    )

    with pytest.raises(ExpiredAccessTokenError):
        decode_access_token(
            token,
            secret="test-secret-key-for-foundation",
            now=now + timedelta(minutes=2),
        )


def test_refresh_token_hashing_is_stable_and_not_plaintext() -> None:
    token = generate_refresh_token()
    token_hash = hash_refresh_token(token, secret="test-secret-key-for-foundation")

    assert token_hash == hash_refresh_token(
        token,
        secret="test-secret-key-for-foundation",
    )
    assert token_hash != token
