from app.core.exceptions import AppError


class SettingsNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "System settings could not be found.",
            code="settings_not_found",
            status_code=404,
        )


class InvalidSettingsValueError(AppError):
    def __init__(self, field: str) -> None:
        super().__init__(
            f"Invalid value for setting '{field}'.",
            code="invalid_settings_value",
            status_code=400,
        )


class InvalidSettingsCategoryError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "The requested settings category is not supported.",
            code="invalid_settings_category",
            status_code=400,
        )


class ProtectedSettingsFieldError(AppError):
    def __init__(self, field: str) -> None:
        super().__init__(
            f"Setting '{field}' cannot be updated.",
            code="protected_settings_field",
            status_code=400,
        )


class UnknownSettingsFieldError(AppError):
    def __init__(self, field: str) -> None:
        super().__init__(
            f"Setting '{field}' is not supported.",
            code="unknown_settings_field",
            status_code=400,
        )


class SettingsUpdateConflictError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "System settings could not be updated due to a concurrent change.",
            code="settings_update_conflict",
            status_code=409,
        )


class TimezoneInvalidError(InvalidSettingsValueError):
    def __init__(self) -> None:
        AppError.__init__(
            self,
            "Invalid value for setting 'timezone'.",
            code="invalid_timezone",
            status_code=400,
        )


class LocaleInvalidError(InvalidSettingsValueError):
    def __init__(self) -> None:
        AppError.__init__(
            self,
            "Invalid value for setting 'locale'.",
            code="invalid_locale",
            status_code=400,
        )
