from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.infrastructure.models import RefreshTokenModel, UserModel
from app.shared.utils import utc_now


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_user_by_id(self, user_id: UUID) -> UserModel | None:
        return await self.session.get(UserModel, user_id)

    async def update_user_profile(
        self,
        user: UserModel,
        values: dict[str, Any],
    ) -> UserModel:
        for field, value in values.items():
            setattr(user, field, value)
        user.updated_at = utc_now()
        await self.session.flush()
        return user

    async def update_password_hash(
        self,
        user: UserModel,
        hashed_password: str,
    ) -> UserModel:
        user.hashed_password = hashed_password
        user.updated_at = utc_now()
        await self.session.flush()
        return user

    async def revoke_user_refresh_tokens(self, user_id: UUID) -> None:
        await self.session.execute(
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
            .values(revoked_at=utc_now())
        )
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
