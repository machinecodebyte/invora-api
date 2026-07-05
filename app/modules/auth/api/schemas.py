from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_MAX_LENGTH = 320


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=EMAIL_MAX_LENGTH)
    password: str = Field(..., min_length=1, max_length=256)
    full_name: str | None = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email_for_schema(value)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=EMAIL_MAX_LENGTH)
    password: str = Field(..., min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email_for_schema(value)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class UserPublic(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int


class AuthData(BaseModel):
    user: UserPublic
    tokens: TokenPairResponse


class UserData(BaseModel):
    user: UserPublic


class MessageData(BaseModel):
    message: str


class AuthResponse(BaseModel):
    success: Literal[True] = True
    data: AuthData


class MeResponse(BaseModel):
    success: Literal[True] = True
    data: UserData


class MessageResponse(BaseModel):
    success: Literal[True] = True
    data: MessageData


def normalize_email_for_schema(value: str) -> str:
    normalized = value.strip().lower()
    local, separator, domain = normalized.partition("@")
    if (
        not separator
        or not local
        or not domain
        or "." not in domain
        or any(character.isspace() for character in normalized)
    ):
        msg = "Enter a valid email address."
        raise ValueError(msg)
    return normalized
