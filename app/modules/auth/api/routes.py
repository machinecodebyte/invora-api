from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.modules.auth.api.dependencies import get_auth_service, get_current_user
from app.modules.auth.api.schemas import (
    AuthData,
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    MessageData,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserData,
    UserPublic,
)
from app.modules.auth.application.service import AuthResult, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


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
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    result = await auth_service.register(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
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
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    result = await auth_service.login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
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
    payload: RefreshRequest,
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthResponse:
    result = await auth_service.refresh_token(
        refresh_token=payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
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
    payload: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> MessageResponse:
    message = await auth_service.logout(refresh_token=payload.refresh_token)
    return MessageResponse(data=MessageData(message=message))


def _auth_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        data=AuthData(
            user=UserPublic.model_validate(result.user),
            tokens=TokenPairResponse(
                access_token=result.tokens.access_token,
                refresh_token=result.tokens.refresh_token,
                token_type=result.tokens.token_type,
                expires_in=result.tokens.expires_in,
            ),
        ),
    )


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host
