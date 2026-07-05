from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.domain.exceptions import DuplicateEmailError
from app.modules.auth.infrastructure.models import RefreshTokenModel, UserModel


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(
        self,
        *,
        email: str,
        full_name: str | None,
        hashed_password: str,
    ) -> UserModel:
        user = UserModel(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
        )
        self.session.add(user)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateEmailError() from exc
        return user

    async def get_user_by_email(self, email: str) -> UserModel | None:
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email),
        )
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> UserModel | None:
        return await self.session.get(UserModel, user_id)

    async def email_exists(self, email: str) -> bool:
        result = await self.session.execute(
            select(UserModel.id).where(UserModel.email == email).limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def create_refresh_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RefreshTokenModel:
        refresh_token = RefreshTokenModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.session.add(refresh_token)
        await self.session.flush()
        return refresh_token

    async def get_refresh_token_by_hash(
        self,
        token_hash: str,
    ) -> RefreshTokenModel | None:
        result = await self.session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash),
        )
        return result.scalar_one_or_none()

    async def revoke_refresh_token(
        self,
        refresh_token: RefreshTokenModel,
        *,
        revoked_at: datetime,
        replaced_by_token_id: UUID | None = None,
    ) -> None:
        refresh_token.revoked_at = revoked_at
        refresh_token.replaced_by_token_id = replaced_by_token_id
        await self.session.flush()

    async def rotate_refresh_token(
        self,
        refresh_token: RefreshTokenModel,
        *,
        new_token_hash: str,
        expires_at: datetime,
        revoked_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RefreshTokenModel:
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

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
