import pytest

from app.modules.auth.domain.exceptions import WeakPasswordError
from app.modules.auth.domain.passwords import (
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    password_hash = hash_password("StrongPass1!")

    assert password_hash != "StrongPass1!"
    assert verify_password("StrongPass1!", password_hash)
    assert not verify_password("WrongPass1!", password_hash)


@pytest.mark.parametrize(
    "password",
    [
        "Short1!",
        "lowercase1!",
        "UPPERCASE1!",
        "NoNumber!",
        "NoSpecial1",
    ],
)
def test_password_policy_rejects_weak_passwords(password: str) -> None:
    with pytest.raises(WeakPasswordError):
        validate_password_strength(password)


def test_password_policy_accepts_strong_password() -> None:
    validate_password_strength("StrongPass1!")
