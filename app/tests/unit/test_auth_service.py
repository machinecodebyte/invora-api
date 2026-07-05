import pytest

from app.core.config import get_settings
from app.modules.auth.application.service import AuthService
from app.modules.auth.domain.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
)


@pytest.mark.asyncio
async def test_duplicate_email_service_behavior(auth_repository) -> None:
    service = AuthService(repository=auth_repository, settings=get_settings())
    await service.register(
        email="owner@example.com",
        password="StrongPass1!",
        full_name="Owner",
    )

    with pytest.raises(DuplicateEmailError):
        await service.register(
            email="OWNER@example.com",
            password="StrongPass1!",
            full_name="Owner Again",
        )


@pytest.mark.asyncio
async def test_invalid_login_service_behavior(auth_repository) -> None:
    service = AuthService(repository=auth_repository, settings=get_settings())
    await service.register(
        email="owner@example.com",
        password="StrongPass1!",
        full_name="Owner",
    )

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="owner@example.com", password="WrongPass1!")
