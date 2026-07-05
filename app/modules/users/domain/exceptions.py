from app.core.exceptions import AppError


class ProfileNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "User profile was not found.",
            code="profile_not_found",
            status_code=404,
        )


class InvalidProfileUpdateError(AppError):
    def __init__(
        self,
        message: str = "Profile update contains invalid fields.",
    ) -> None:
        super().__init__(
            message,
            code="invalid_profile_update",
            status_code=400,
        )


class InvalidCurrentPasswordError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Current password is invalid.",
            code="invalid_current_password",
            status_code=400,
        )
