from __future__ import annotations

import re
from typing import Any

from app.modules.users.domain.exceptions import InvalidProfileUpdateError

ALLOWED_PROFILE_FIELDS = {
    "full_name",
    "phone_number",
    "avatar_url",
    "timezone",
    "locale",
}
PROTECTED_PROFILE_FIELDS = {
    "id",
    "email",
    "hashed_password",
    "password",
    "is_active",
    "is_verified",
    "role",
    "is_admin",
    "created_at",
    "updated_at",
}
PHONE_PATTERN = re.compile(r"^\+?[0-9 .()\-]{7,32}$")
LOCALE_PATTERN = re.compile(r"^[a-z]{2}([_-][A-Za-z]{2})?$")


def ensure_no_protected_fields(extra_fields: set[str]) -> None:
    blocked = sorted(extra_fields & PROTECTED_PROFILE_FIELDS)
    if blocked:
        raise InvalidProfileUpdateError(
            f"Profile field cannot be updated: {', '.join(blocked)}."
        )

    if extra_fields:
        raise InvalidProfileUpdateError(
            f"Unsupported profile field: {', '.join(sorted(extra_fields))}."
        )


def normalize_profile_updates(values: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field, value in values.items():
        if field not in ALLOWED_PROFILE_FIELDS:
            raise InvalidProfileUpdateError(f"Unsupported profile field: {field}.")

        if value is None:
            normalized[field] = None
            continue

        if not isinstance(value, str):
            raise InvalidProfileUpdateError(f"{field} must be a string or null.")

        cleaned_value = " ".join(value.strip().split())
        if field == "avatar_url":
            cleaned_value = value.strip()

        if cleaned_value == "":
            normalized[field] = None
            continue

        _validate_profile_field(field, cleaned_value)
        normalized[field] = (
            cleaned_value.replace("_", "-") if field == "locale" else cleaned_value
        )

    if not normalized:
        raise InvalidProfileUpdateError("At least one profile field is required.")

    return normalized


def _validate_profile_field(field: str, value: str) -> None:
    max_lengths = {
        "full_name": 255,
        "phone_number": 32,
        "avatar_url": 1024,
        "timezone": 64,
        "locale": 16,
    }
    if len(value) > max_lengths[field]:
        raise InvalidProfileUpdateError(f"{field} is too long.")

    if field == "phone_number" and not PHONE_PATTERN.fullmatch(value):
        raise InvalidProfileUpdateError("Phone number format is invalid.")

    if field == "avatar_url" and not value.startswith(("http://", "https://")):
        raise InvalidProfileUpdateError("Avatar URL must start with http:// or https://.")

    if field == "timezone" and any(character.isspace() for character in value):
        raise InvalidProfileUpdateError("Timezone cannot contain spaces.")

    if field == "locale" and not LOCALE_PATTERN.fullmatch(value):
        raise InvalidProfileUpdateError("Locale format is invalid.")
