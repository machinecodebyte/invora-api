from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.auth.domain.exceptions import InactiveUserError
from app.modules.auth.domain.passwords import (
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.modules.users.domain.exceptions import (
    InvalidCurrentPasswordError,
    ProfileNotFoundError,
)
from app.modules.users.domain.profile import normalize_profile_updates


class UserProfileService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def get_current_profile(self, user_id: UUID) -> Any:
        user = await self._get_active_user(user_id)
        return user

    async def update_profile(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        updates = normalize_profile_updates(values)
        user = await self._get_active_user(user_id)

        try:
            user = await self.repository.update_user_profile(user, updates)
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return user

    async def change_password(
        self,
        *,
        user_id: UUID,
        current_password: str,
        new_password: str,
    ) -> str:
        user = await self._get_active_user(user_id)
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCurrentPasswordError()

        validate_password_strength(new_password)
        new_password_hash = hash_password(new_password)

        try:
            await self.repository.update_password_hash(user, new_password_hash)
            await self.repository.revoke_user_refresh_tokens(user.id)
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return "Password changed successfully."

    async def _get_active_user(self, user_id: UUID) -> Any:
        user = await self.repository.get_user_by_id(user_id)
        if user is None:
            raise ProfileNotFoundError()
        if not user.is_active:
            raise InactiveUserError()
        return user
