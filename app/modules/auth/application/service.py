from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.core.config import Settings
from app.core.exceptions import AppError
from app.modules.auth.domain.exceptions import (
    DuplicateEmailError,
    ExpiredRefreshTokenError,
    InactiveUserError,
    InvalidAccessTokenError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RevokedRefreshTokenError,
)
from app.modules.auth.domain.passwords import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.modules.auth.domain.tokens import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.shared.utils import utc_now


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: Any
    tokens: TokenPair


class AuthService:
    def __init__(self, *, repository: Any, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings
        self.jwt_secret = settings.JWT_SECRET_KEY.get_secret_value()

    async def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str | None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResult:
        normalized_email = normalize_email(email)
        validate_password_strength(password)

        if await self.repository.email_exists(normalized_email):
            raise DuplicateEmailError()

        try:
            user = await self.repository.create_user(
                email=normalized_email,
                full_name=normalize_full_name(full_name),
                hashed_password=hash_password(password),
            )
            tokens = await self._issue_tokens(
                user,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return AuthResult(user=user, tokens=tokens)

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResult:
        normalized_email = normalize_email(email)
        user = await self.repository.get_user_by_email(normalized_email)

        if user is None or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()
        if not user.is_active:
            raise InactiveUserError()

        try:
            tokens = await self._issue_tokens(
                user,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return AuthResult(user=user, tokens=tokens)

    async def get_current_user(self, access_token: str) -> Any:
        payload = decode_access_token(access_token, secret=self.jwt_secret)
        user = await self.repository.get_user_by_id(payload.subject)
        if user is None:
            raise InvalidAccessTokenError()
        if not user.is_active:
            raise InactiveUserError()
        return user

    async def refresh_token(
        self,
        *,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> AuthResult:
        stored_refresh_token = await self._get_valid_refresh_token(refresh_token)
        user = await self.repository.get_user_by_id(stored_refresh_token.user_id)
        if user is None:
            raise InvalidRefreshTokenError()
        if not user.is_active:
            raise InactiveUserError()

        now = utc_now()
        new_raw_refresh_token = generate_refresh_token()
        new_refresh_token_hash = hash_refresh_token(
            new_raw_refresh_token,
            secret=self.jwt_secret,
        )
        try:
            refresh_expires_at = now + timedelta(
                days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS,
            )
            await self.repository.rotate_refresh_token(
                stored_refresh_token,
                new_token_hash=new_refresh_token_hash,
                expires_at=refresh_expires_at,
                revoked_at=now,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return AuthResult(
            user=user,
            tokens=self._build_token_pair(user, new_raw_refresh_token),
        )

    async def logout(self, *, refresh_token: str) -> str:
        stored_refresh_token = await self._get_valid_refresh_token(refresh_token)
        try:
            await self.repository.revoke_refresh_token(
                stored_refresh_token,
                revoked_at=utc_now(),
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return "Logged out successfully."

    async def _issue_tokens(
        self,
        user: Any,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        raw_refresh_token = generate_refresh_token()
        refresh_token_hash = hash_refresh_token(
            raw_refresh_token,
            secret=self.jwt_secret,
        )
        refresh_expires_at = utc_now() + timedelta(
            days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS,
        )
        await self.repository.create_refresh_token(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return self._build_token_pair(user, raw_refresh_token)

    def _build_token_pair(self, user: Any, refresh_token: str) -> TokenPair:
        access_token_minutes = self.settings.ACCESS_TOKEN_EXPIRE_MINUTES
        access_token = create_access_token(
            subject=user.id,
            secret=self.jwt_secret,
            expires_delta=timedelta(minutes=access_token_minutes),
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=access_token_minutes * 60,
        )

    async def _get_valid_refresh_token(self, raw_refresh_token: str) -> Any:
        if not raw_refresh_token:
            raise InvalidRefreshTokenError()

        refresh_token_hash = hash_refresh_token(
            raw_refresh_token,
            secret=self.jwt_secret,
        )
        stored_refresh_token = await self.repository.get_refresh_token_by_hash(
            refresh_token_hash,
        )
        if stored_refresh_token is None:
            raise InvalidRefreshTokenError()
        if stored_refresh_token.revoked_at is not None:
            raise RevokedRefreshTokenError()
        if stored_refresh_token.expires_at <= utc_now():
            raise ExpiredRefreshTokenError()
        return stored_refresh_token


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_full_name(full_name: str | None) -> str | None:
    if full_name is None:
        return None
    normalized = " ".join(full_name.strip().split())
    return normalized or None
