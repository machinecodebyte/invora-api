from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.users.api.dependencies import get_user_profile_service
from app.modules.users.api.schemas import (
    ChangePasswordData,
    ChangePasswordRequest,
    ChangePasswordResponse,
    UserProfileData,
    UserProfilePublic,
    UserProfileResponse,
    UserProfileUpdateRequest,
)
from app.modules.users.application.service import UserProfileService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get my profile",
    description=(
        "Requires a Bearer access token and returns the current user's safe "
        "profile."
    ),
)
async def get_my_profile(
    current_user: Annotated[object, Depends(get_current_user)],
    profile_service: Annotated[UserProfileService, Depends(get_user_profile_service)],
) -> UserProfileResponse:
    profile = await profile_service.get_current_profile(current_user.id)
    return _profile_response(profile)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update my profile",
    description=(
        "Requires a Bearer access token and updates only safe profile fields: "
        "full_name, phone_number, avatar_url, timezone, and locale."
    ),
)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    profile_service: Annotated[UserProfileService, Depends(get_user_profile_service)],
) -> UserProfileResponse:
    profile = await profile_service.update_profile(
        user_id=current_user.id,
        values=payload.update_values(),
    )
    return _profile_response(profile)


@router.post(
    "/me/change-password",
    response_model=ChangePasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Change my password",
    description=(
        "Requires a Bearer access token, verifies the current password, stores a "
        "new password hash, and revokes existing refresh tokens for the user."
    ),
)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    profile_service: Annotated[UserProfileService, Depends(get_user_profile_service)],
) -> ChangePasswordResponse:
    message = await profile_service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return ChangePasswordResponse(data=ChangePasswordData(message=message))


def _profile_response(profile: object) -> UserProfileResponse:
    return UserProfileResponse(
        data=UserProfileData(profile=UserProfilePublic.model_validate(profile)),
    )
