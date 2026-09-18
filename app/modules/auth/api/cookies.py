from fastapi import Response

from app.core.config import Settings


def set_refresh_cookie(
    response: Response,
    *,
    refresh_token: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.refresh_cookie_max_age_seconds,
        path=settings.refresh_cookie_path,
        domain=settings.REFRESH_COOKIE_DOMAIN,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )


def clear_refresh_cookie(response: Response, *, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.refresh_cookie_path,
        domain=settings.REFRESH_COOKIE_DOMAIN,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
    )
