from app.core.exceptions import AppError


class DuplicateEmailError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Email is already registered.",
            code="duplicate_email",
            status_code=409,
        )


class WeakPasswordError(AppError):
    def __init__(self, message: str = "Password does not meet strength rules.") -> None:
        super().__init__(message, code="weak_password", status_code=400)


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Invalid email or password.",
            code="invalid_credentials",
            status_code=401,
        )


class InactiveUserError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "User account is inactive.",
            code="inactive_user",
            status_code=403,
        )


class InvalidAccessTokenError(AppError):
    def __init__(self, message: str = "Invalid access token.") -> None:
        super().__init__(message, code="invalid_access_token", status_code=401)


class ExpiredAccessTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Access token has expired.",
            code="expired_access_token",
            status_code=401,
        )


class InvalidRefreshTokenError(AppError):
    def __init__(self, message: str = "Invalid refresh token.") -> None:
        super().__init__(message, code="invalid_refresh_token", status_code=401)


class ExpiredRefreshTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Refresh token has expired.",
            code="expired_refresh_token",
            status_code=401,
        )


class RevokedRefreshTokenError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Refresh token has been revoked.",
            code="revoked_refresh_token",
            status_code=401,
        )


class AuthRateLimitExceededError(AppError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            "Too many authentication attempts. Please try again later.",
            code="authentication_rate_limited",
            status_code=429,
            headers={"Retry-After": str(max(1, retry_after_seconds))},
        )


class AuthRateLimitUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Authentication is temporarily unavailable. Please try again later.",
            code="authentication_rate_limit_unavailable",
            status_code=503,
        )
