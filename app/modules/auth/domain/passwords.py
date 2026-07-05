import base64
import hashlib
import hmac
import secrets

from app.modules.auth.domain.exceptions import WeakPasswordError

PASSWORD_HASH_SCHEME = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    if not any(character.islower() for character in password):
        raise WeakPasswordError("Password must include a lowercase letter.")
    if not any(character.isupper() for character in password):
        raise WeakPasswordError("Password must include an uppercase letter.")
    if not any(character.isdigit() for character in password):
        raise WeakPasswordError("Password must include a number.")
    if not any(not character.isalnum() for character in password):
        raise WeakPasswordError("Password must include a special character.")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
    encoded_hash = base64.urlsafe_b64encode(password_hash).decode("ascii")
    return (
        f"{PASSWORD_HASH_SCHEME}${PASSWORD_HASH_ITERATIONS}"
        f"${encoded_salt}${encoded_hash}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations_value, encoded_salt, encoded_hash = stored_hash.split("$")
        iterations = int(iterations_value)
    except ValueError:
        return False

    if scheme != PASSWORD_HASH_SCHEME:
        return False

    try:
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_hash = base64.urlsafe_b64decode(encoded_hash.encode("ascii"))
    except ValueError:
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual_hash, expected_hash)
