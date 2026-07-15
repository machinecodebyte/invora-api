from typing import Annotated

from fastapi import APIRouter, Body, Depends, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.settings.api.dependencies import get_system_settings_service
from app.modules.settings.api.schemas import (
    BackgroundJobsSettingsResponse,
    BackgroundJobsSettingsResponseData,
    BackgroundJobsSettingsUpdateRequest,
    DashboardSettingsResponse,
    DashboardSettingsResponseData,
    DashboardSettingsUpdateRequest,
    ForecastSettingsResponse,
    ForecastSettingsResponseData,
    ForecastSettingsUpdateRequest,
    InventorySettingsResponse,
    InventorySettingsResponseData,
    InventorySettingsUpdateRequest,
    ReportsSettingsResponse,
    ReportsSettingsResponseData,
    ReportsSettingsUpdateRequest,
    SalesUploadSettingsResponse,
    SalesUploadSettingsResponseData,
    SalesUploadSettingsUpdateRequest,
    SettingsOptionsData,
    SettingsOptionsResponse,
    SettingsResetData,
    SettingsResetRequest,
    SettingsResetResponse,
    SystemSettingsPublic,
    SystemSettingsResponse,
    SystemSettingsUpdateRequest,
)
from app.modules.settings.application.service import (
    SystemSettingsService,
    settings_payload,
)
from app.modules.settings.domain.rules import validate_reset_request_fields

router = APIRouter(prefix="/settings", tags=["System Settings"])

AUTH_ERRORS = {401: {"description": "Missing or invalid access token"}}
SAFE_SETTINGS_DESCRIPTION = (
    "Requires a Bearer access token and returns only user-scoped business "
    "preferences. Infrastructure secrets and deployment configuration are never "
    "exposed or mutable through this API."
)


@router.get(
    "/options",
    response_model=SettingsOptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get system settings options",
    description=SAFE_SETTINGS_DESCRIPTION,
    responses=AUTH_ERRORS,
)
async def get_settings_options(
    _: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> SettingsOptionsResponse:
    options = await settings_service.get_options()
    return SettingsOptionsResponse(data=SettingsOptionsData(**options))


@router.get(
    "",
    response_model=SystemSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user system settings",
    description=SAFE_SETTINGS_DESCRIPTION,
    responses=AUTH_ERRORS,
)
async def get_system_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> SystemSettingsResponse:
    settings = await settings_service.get_settings(user_id=current_user.id)
    return SystemSettingsResponse(
        data=SystemSettingsPublic(**settings_payload(settings))
    )


@router.patch(
    "",
    response_model=SystemSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user system settings",
    description=(
        f"{SAFE_SETTINGS_DESCRIPTION} Unknown and protected fields are rejected."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid or protected setting"}},
)
async def update_system_settings(
    request: SystemSettingsUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> SystemSettingsResponse:
    settings = await settings_service.update_settings(
        user_id=current_user.id,
        values=request.update_values(),
    )
    return SystemSettingsResponse(
        data=SystemSettingsPublic(**settings_payload(settings))
    )


@router.post(
    "/reset",
    response_model=SettingsResetResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset system settings to defaults",
    description=(
        "Requires a Bearer access token and resets all safe user preferences, "
        "or one allowed category, to Invora defaults. It never changes "
        "deployment configuration or secrets."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid reset category"}},
)
async def reset_system_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
    request: SettingsResetRequest | None = Body(default=None),
) -> SettingsResetResponse:
    values = request.update_values() if request is not None else {}
    validate_reset_request_fields(values)
    settings, category = await settings_service.reset_settings(
        user_id=current_user.id,
        category=values.get("category"),
    )
    return SettingsResetResponse(
        data=SettingsResetData(
            settings=SystemSettingsPublic(**settings_payload(settings)),
            reset_category=category,
        )
    )


@router.get(
    "/forecast",
    response_model=ForecastSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get forecast settings",
    description=(
        "Requires a Bearer access token and returns stored forecast defaults. "
        "It does not create or process forecast runs."
    ),
    responses=AUTH_ERRORS,
)
async def get_forecast_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> ForecastSettingsResponse:
    data = await settings_service.get_forecast_settings(user_id=current_user.id)
    return ForecastSettingsResponse(data=ForecastSettingsResponseData(**data))


@router.patch(
    "/forecast",
    response_model=ForecastSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update forecast settings",
    description=(
        "Requires a Bearer access token and updates stored forecast defaults. "
        "It never starts automatic forecast processing."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid setting value"}},
)
async def update_forecast_settings(
    request: ForecastSettingsUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> ForecastSettingsResponse:
    data = await settings_service.update_forecast_settings(
        user_id=current_user.id,
        values=request.update_values(),
    )
    return ForecastSettingsResponse(data=ForecastSettingsResponseData(**data))


@router.get(
    "/inventory",
    response_model=InventorySettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get inventory settings",
    description=(
        "Requires a Bearer access token and returns defaults for future inventory "
        "setup. Existing inventory rows are not changed."
    ),
    responses=AUTH_ERRORS,
)
async def get_inventory_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> InventorySettingsResponse:
    data = await settings_service.get_inventory_settings(user_id=current_user.id)
    return InventorySettingsResponse(data=InventorySettingsResponseData(**data))


@router.patch(
    "/inventory",
    response_model=InventorySettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update inventory settings",
    description=(
        "Requires a Bearer access token and updates future inventory defaults. "
        "It does not alter inventory balances or movement history."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid setting value"}},
)
async def update_inventory_settings(
    request: InventorySettingsUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> InventorySettingsResponse:
    data = await settings_service.update_inventory_settings(
        user_id=current_user.id,
        values=request.update_values(),
    )
    return InventorySettingsResponse(data=InventorySettingsResponseData(**data))


@router.get(
    "/sales-upload",
    response_model=SalesUploadSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sales upload settings",
    description=(
        "Requires a Bearer access token and returns stored sales upload "
        "preferences. It does not ingest or modify sales data."
    ),
    responses=AUTH_ERRORS,
)
async def get_sales_upload_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> SalesUploadSettingsResponse:
    data = await settings_service.get_sales_upload_settings(user_id=current_user.id)
    return SalesUploadSettingsResponse(data=SalesUploadSettingsResponseData(**data))


@router.patch(
    "/sales-upload",
    response_model=SalesUploadSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update sales upload settings",
    description=(
        "Requires a Bearer access token and updates stored upload preferences. "
        "It does not rewrite historical upload behavior."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid setting value"}},
)
async def update_sales_upload_settings(
    request: SalesUploadSettingsUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> SalesUploadSettingsResponse:
    data = await settings_service.update_sales_upload_settings(
        user_id=current_user.id,
        values=request.update_values(),
    )
    return SalesUploadSettingsResponse(data=SalesUploadSettingsResponseData(**data))


@router.get(
    "/reports",
    response_model=ReportsSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reports settings",
    description=(
        "Requires a Bearer access token and returns report export preferences. "
        "It does not generate or export a report."
    ),
    responses=AUTH_ERRORS,
)
async def get_reports_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> ReportsSettingsResponse:
    data = await settings_service.get_reports_settings(user_id=current_user.id)
    return ReportsSettingsResponse(data=ReportsSettingsResponseData(**data))


@router.patch(
    "/reports",
    response_model=ReportsSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update reports settings",
    description=(
        "Requires a Bearer access token and updates stored report preferences. "
        "It does not change report query behavior in this module."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid setting value"}},
)
async def update_reports_settings(
    request: ReportsSettingsUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> ReportsSettingsResponse:
    data = await settings_service.update_reports_settings(
        user_id=current_user.id,
        values=request.update_values(),
    )
    return ReportsSettingsResponse(data=ReportsSettingsResponseData(**data))


@router.get(
    "/dashboard",
    response_model=DashboardSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard settings",
    description=(
        "Requires a Bearer access token and returns a stored dashboard date-range "
        "preference. It does not change dashboard analytics responses."
    ),
    responses=AUTH_ERRORS,
)
async def get_dashboard_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> DashboardSettingsResponse:
    data = await settings_service.get_dashboard_settings(user_id=current_user.id)
    return DashboardSettingsResponse(data=DashboardSettingsResponseData(**data))


@router.patch(
    "/dashboard",
    response_model=DashboardSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update dashboard settings",
    description=(
        "Requires a Bearer access token and updates a stored dashboard date-range "
        "preference. It does not change dashboard analytics responses."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid setting value"}},
)
async def update_dashboard_settings(
    request: DashboardSettingsUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> DashboardSettingsResponse:
    data = await settings_service.update_dashboard_settings(
        user_id=current_user.id,
        values=request.update_values(),
    )
    return DashboardSettingsResponse(data=DashboardSettingsResponseData(**data))


@router.get(
    "/background-jobs",
    response_model=BackgroundJobsSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get background job settings",
    description=(
        "Requires a Bearer access token and returns the safe auto-retry preference. "
        "It does not expose worker internals or change queue configuration."
    ),
    responses=AUTH_ERRORS,
)
async def get_background_jobs_settings(
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> BackgroundJobsSettingsResponse:
    data = await settings_service.get_background_jobs_settings(user_id=current_user.id)
    return BackgroundJobsSettingsResponse(
        data=BackgroundJobsSettingsResponseData(**data)
    )


@router.patch(
    "/background-jobs",
    response_model=BackgroundJobsSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update background job settings",
    description=(
        "Requires a Bearer access token and updates the stored auto-retry "
        "preference. Existing RQ retry behavior is unchanged."
    ),
    responses={**AUTH_ERRORS, 400: {"description": "Invalid setting value"}},
)
async def update_background_jobs_settings(
    request: BackgroundJobsSettingsUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    settings_service: Annotated[
        SystemSettingsService,
        Depends(get_system_settings_service),
    ],
) -> BackgroundJobsSettingsResponse:
    data = await settings_service.update_background_jobs_settings(
        user_id=current_user.id,
        values=request.update_values(),
    )
    return BackgroundJobsSettingsResponse(
        data=BackgroundJobsSettingsResponseData(**data)
    )
