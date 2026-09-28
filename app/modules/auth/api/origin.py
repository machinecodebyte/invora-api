from fastapi import Request

from app.core.config import Settings
from app.modules.auth.domain.exceptions import InvalidAuthRequestOriginError


def enforce_cookie_auth_origin(request: Request, *, settings: Settings) -> None:
    """Require cookie-authenticated mutations to originate from a trusted UI."""
    origin = request.headers.get("origin")
    if origin is None or origin not in settings.cors_origin_list:
        raise InvalidAuthRequestOriginError()
