from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.modules.auth.api.cookies import clear_refresh_cookie, set_refresh_cookie
from app.modules.auth.api.dependencies import (
    get_auth_service,
    get_current_user,
)
from app.modules.auth.api.schemas import (
    AccessTokenResponse,
    AuthData,
    AuthResponse,
    LoginRequest,
    MeResponse,
    MessageData,
    MessageResponse,
    RegisterRequest,
    UserData,
    UserPublic,
)
from app.modules.auth.application.service import AuthResult, AuthService
from app.modules.auth.domain.exceptions import (
    ExpiredRefreshTokenError,
    InvalidRefreshTokenError,
    RevokedRefreshTokenError,
)
from app.modules.auth.infrastructure.rate_limit import (
    AuthRateLimiter,
    get_auth_rate_limiter,
)
from app.shared.responses import error_response

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
    description="Create an active user account and issue access and refresh tokens.",
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    rate_limiter: Annotated[AuthRateLimiter, Depends(get_auth_rate_limiter)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    await rate_limiter.enforce_registration(client_ip=_client_ip(request))
    result = await auth_service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    set_refresh_cookie(
        response,
        refresh_token=result.tokens.refresh_token,
        settings=settings,
    )
    return _auth_response(result)


@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login user",
    description="Authenticate with email and password and issue fresh tokens.",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    rate_limiter: Annotated[AuthRateLimiter, Depends(get_auth_rate_limiter)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse:
    await rate_limiter.enforce_login(
        client_ip=_client_ip(request),
        email=payload.email,
    )
    result = await auth_service.login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    set_refresh_cookie(
        response,
        refresh_token=result.tokens.refresh_token,
        settings=settings,
    )
    return _auth_response(result)


@router.get(
    "/me",
    response_model=MeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Return the authenticated user for a valid Bearer access token.",
)
async def me(current_user: Annotated[object, Depends(get_current_user)]) -> MeResponse:
    return MeResponse(data=UserData(user=UserPublic.model_validate(current_user)))


@router.post(
    "/refresh",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh tokens",
    description="Rotate a valid refresh token and return a new token pair.",
)
async def refresh(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    rate_limiter: Annotated[AuthRateLimiter, Depends(get_auth_rate_limiter)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthResponse | JSONResponse:
    await rate_limiter.enforce_refresh(client_ip=_client_ip(request))
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    try:
        result = await auth_service.refresh_token(
            refresh_token=refresh_token or "",
            user_agent=request.headers.get("user-agent"),
            ip_address=_client_ip(request),
        )
    except (
        InvalidRefreshTokenError,
        ExpiredRefreshTokenError,
        RevokedRefreshTokenError,
    ) as exc:
        error = JSONResponse(
            status_code=exc.status_code,
            content=error_response(code=exc.code, message=exc.message),
        )
        clear_refresh_cookie(error, settings=settings)
        return error

    set_refresh_cookie(
        response,
        refresh_token=result.tokens.refresh_token,
        settings=settings,
    )
    return _auth_response(result)


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Revoke a valid refresh token so it cannot be reused.",
)
async def logout(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MessageResponse:
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh_token:
        try:
            await auth_service.logout(refresh_token=refresh_token)
        except (
            InvalidRefreshTokenError,
            ExpiredRefreshTokenError,
            RevokedRefreshTokenError,
        ):
            # Logout is intentionally idempotent. The browser still needs its
            # stale cookie removed even if the persisted session is gone.
            pass
    clear_refresh_cookie(response, settings=settings)
    return MessageResponse(data=MessageData(message="Logged out successfully."))


def _auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        data=AuthData(
            user=UserPublic.model_validate(result.user),
            tokens=AccessTokenResponse(
                access_token=result.tokens.access_token,
                token_type=result.tokens.token_type,
                expires_in=result.tokens.expires_in,
            ),
        ),
    )


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host
