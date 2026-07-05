from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.db.session import get_db_session
from app.modules.auth.application.service import AuthService
from app.modules.auth.domain.exceptions import InvalidAccessTokenError
from app.modules.auth.infrastructure.repositories import AuthRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_service(session=Depends(get_db_session)) -> AuthService:
    return AuthService(repository=AuthRepository(session), settings=get_settings())


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidAccessTokenError("Bearer access token is required.")
    return await auth_service.get_current_user(credentials.credentials)
