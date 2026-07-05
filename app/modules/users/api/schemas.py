from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.domain.profile import (
    ALLOWED_PROFILE_FIELDS,
    ensure_no_protected_fields,
    normalize_profile_updates,
)


class UserProfilePublic(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    phone_number: str | None
    avatar_url: str | None
    timezone: str | None
    locale: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileData(BaseModel):
    profile: UserProfilePublic


class ChangePasswordData(BaseModel):
    message: str


class UserProfileResponse(BaseModel):
    success: Literal[True] = True
    data: UserProfileData


class ChangePasswordResponse(BaseModel):
    success: Literal[True] = True
    data: ChangePasswordData


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None
    locale: str | None = None

    model_config = ConfigDict(extra="allow")

    def update_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_protected_fields(extra_fields)

        provided_values = {
            field: getattr(self, field)
            for field in ALLOWED_PROFILE_FIELDS
            if field in self.model_fields_set
        }
        return normalize_profile_updates(provided_values)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=1, max_length=256)
