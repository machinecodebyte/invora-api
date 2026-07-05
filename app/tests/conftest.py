import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient


def pytest_configure() -> None:
    os.environ["APP_NAME"] = "Invora Backend Test"
    os.environ["APP_ENV"] = "test"
    os.environ["DEBUG"] = "false"
    os.environ["API_V1_PREFIX"] = "/api/v1"
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/invora_test"
    )
    os.environ["REDIS_URL"] = "redis://localhost:56379/1"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-foundation"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
    os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "14"


@pytest.fixture
def app():
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    return create_app()


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    from app.db.session import close_database_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_database_engine()


@dataclass(slots=True)
class FakeUser:
    id: UUID
    email: str
    full_name: str | None
    hashed_password: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    phone_number: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None
    locale: str | None = None


@dataclass(slots=True)
class FakeRefreshToken:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    replaced_by_token_id: UUID | None
    user_agent: str | None
    ip_address: str | None


class FakeAuthRepository:
    def __init__(self) -> None:
        self.users_by_email: dict[str, FakeUser] = {}
        self.users_by_id: dict[UUID, FakeUser] = {}
        self.refresh_tokens_by_hash: dict[str, FakeRefreshToken] = {}

    async def create_user(
        self,
        *,
        email: str,
        full_name: str | None,
        hashed_password: str,
    ) -> FakeUser:
        from app.modules.auth.domain.exceptions import DuplicateEmailError
        from app.shared.utils import utc_now

        if email in self.users_by_email:
            raise DuplicateEmailError()

        now = utc_now()
        user = FakeUser(
            id=uuid4(),
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            created_at=now,
            updated_at=now,
        )
        self.users_by_email[user.email] = user
        self.users_by_id[user.id] = user
        return user

    async def get_user_by_email(self, email: str) -> FakeUser | None:
        return self.users_by_email.get(email)

    async def get_user_by_id(self, user_id: UUID) -> FakeUser | None:
        return self.users_by_id.get(user_id)

    async def email_exists(self, email: str) -> bool:
        return email in self.users_by_email

    async def create_refresh_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> FakeRefreshToken:
        from app.shared.utils import utc_now

        refresh_token = FakeRefreshToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            created_at=utc_now(),
            replaced_by_token_id=None,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.refresh_tokens_by_hash[token_hash] = refresh_token
        return refresh_token

    async def get_refresh_token_by_hash(
        self,
        token_hash: str,
    ) -> FakeRefreshToken | None:
        return self.refresh_tokens_by_hash.get(token_hash)

    async def revoke_refresh_token(
        self,
        refresh_token: FakeRefreshToken,
        *,
        revoked_at: datetime,
        replaced_by_token_id: UUID | None = None,
    ) -> None:
        refresh_token.revoked_at = revoked_at
        refresh_token.replaced_by_token_id = replaced_by_token_id

    async def rotate_refresh_token(
        self,
        refresh_token: FakeRefreshToken,
        *,
        new_token_hash: str,
        expires_at: datetime,
        revoked_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> FakeRefreshToken:
        new_refresh_token = await self.create_refresh_token(
            user_id=refresh_token.user_id,
            token_hash=new_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.revoke_refresh_token(
            refresh_token,
            revoked_at=revoked_at,
            replaced_by_token_id=new_refresh_token.id,
        )
        return new_refresh_token

    async def update_user_profile(
        self,
        user: FakeUser,
        values: dict[str, object],
    ) -> FakeUser:
        from app.shared.utils import utc_now

        for field, value in values.items():
            setattr(user, field, value)
        user.updated_at = utc_now()
        return user

    async def update_password_hash(
        self,
        user: FakeUser,
        hashed_password: str,
    ) -> FakeUser:
        from app.shared.utils import utc_now

        user.hashed_password = hashed_password
        user.updated_at = utc_now()
        return user

    async def revoke_user_refresh_tokens(self, user_id: UUID) -> None:
        from app.shared.utils import utc_now

        revoked_at = utc_now()
        for refresh_token in self.refresh_tokens_by_hash.values():
            if refresh_token.user_id == user_id and refresh_token.revoked_at is None:
                refresh_token.revoked_at = revoked_at

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


@pytest.fixture
def auth_repository() -> FakeAuthRepository:
    return FakeAuthRepository()


@pytest.fixture
async def auth_client(app, auth_repository) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()
