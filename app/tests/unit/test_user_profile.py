import pytest

from app.modules.auth.domain.passwords import hash_password, verify_password
from app.modules.users.application.service import UserProfileService
from app.modules.users.domain.exceptions import (
    InvalidCurrentPasswordError,
    InvalidProfileUpdateError,
)
from app.modules.users.domain.profile import (
    ensure_no_protected_fields,
    normalize_profile_updates,
)


def test_profile_update_validation_normalizes_allowed_fields() -> None:
    updates = normalize_profile_updates(
        {
            "full_name": "  Owner   User ",
            "phone_number": "+91 98765 43210",
            "avatar_url": "https://example.com/avatar.png",
            "timezone": "Asia/Kolkata",
            "locale": "en_IN",
        }
    )

    assert updates == {
        "full_name": "Owner User",
        "phone_number": "+91 98765 43210",
        "avatar_url": "https://example.com/avatar.png",
        "timezone": "Asia/Kolkata",
        "locale": "en-IN",
    }


def test_profile_update_rejects_protected_fields() -> None:
    with pytest.raises(InvalidProfileUpdateError):
        ensure_no_protected_fields({"email"})


def test_profile_update_rejects_invalid_avatar_url() -> None:
    with pytest.raises(InvalidProfileUpdateError):
        normalize_profile_updates({"avatar_url": "javascript:alert(1)"})


@pytest.mark.asyncio
async def test_current_password_verification_behavior(auth_repository) -> None:
    user = await auth_repository.create_user(
        email="owner@example.com",
        full_name="Owner",
        hashed_password=hash_password("StrongPass1!"),
    )
    service = UserProfileService(repository=auth_repository)

    with pytest.raises(InvalidCurrentPasswordError):
        await service.change_password(
            user_id=user.id,
            current_password="WrongPass1!",
            new_password="NewStrong1!",
        )


@pytest.mark.asyncio
async def test_password_strength_validation_on_change(auth_repository) -> None:
    user = await auth_repository.create_user(
        email="owner@example.com",
        full_name="Owner",
        hashed_password=hash_password("StrongPass1!"),
    )
    service = UserProfileService(repository=auth_repository)

    with pytest.raises(Exception) as exc_info:
        await service.change_password(
            user_id=user.id,
            current_password="StrongPass1!",
            new_password="weak",
        )

    assert exc_info.value.__class__.__name__ == "WeakPasswordError"


@pytest.mark.asyncio
async def test_password_hash_update_behavior(auth_repository) -> None:
    user = await auth_repository.create_user(
        email="owner@example.com",
        full_name="Owner",
        hashed_password=hash_password("StrongPass1!"),
    )
    service = UserProfileService(repository=auth_repository)

    await service.change_password(
        user_id=user.id,
        current_password="StrongPass1!",
        new_password="NewStrong1!",
    )

    assert not verify_password("StrongPass1!", user.hashed_password)
    assert verify_password("NewStrong1!", user.hashed_password)
