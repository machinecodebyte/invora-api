from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.forecasting.api.dependencies import get_forecast_run_service
from app.modules.forecasting.api.schemas import (
    ForecastRunCancelResponse,
    ForecastRunCreateRequest,
    ForecastRunData,
    ForecastRunListData,
    ForecastRunListResponse,
    ForecastRunOptionsData,
    ForecastRunOptionsResponse,
    ForecastRunPublic,
    ForecastRunResponse,
)
from app.modules.forecasting.application.service import ForecastRunService

router = APIRouter(prefix="/forecast-runs", tags=["Forecast Runs"])


@router.post(
    "",
    response_model=ForecastRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create forecast run",
    description=(
        "Requires a Bearer access token and creates a pending forecast run. "
        "This endpoint manages lifecycle metadata only; ML prediction is handled "
        "by a future module."
    ),
)
async def create_forecast_run(
    request: ForecastRunCreateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    forecast_service: Annotated[
        ForecastRunService,
        Depends(get_forecast_run_service),
    ],
) -> ForecastRunResponse:
    run = await forecast_service.create_run(
        user_id=current_user.id,
        horizon_days=request.horizon_days,
    )
    return ForecastRunResponse(
        data=ForecastRunData(run=ForecastRunPublic.model_validate(run))
    )


@router.get(
    "",
    response_model=ForecastRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List forecast runs",
    description=(
        "Requires a Bearer access token and returns forecast runs owned by the "
        "current user."
    ),
)
async def list_forecast_runs(
    current_user: Annotated[object, Depends(get_current_user)],
    forecast_service: Annotated[
        ForecastRunService,
        Depends(get_forecast_run_service),
    ],
    status_filter: str | None = Query(default=None, alias="status"),
    horizon_days: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="requested_at"),
    sort_order: str = Query(default="desc"),
) -> ForecastRunListResponse:
    runs, total = await forecast_service.list_runs(
        user_id=current_user.id,
        status=status_filter,
        horizon_days=horizon_days,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ForecastRunListResponse(
        data=ForecastRunListData(
            runs=[ForecastRunPublic.model_validate(run) for run in runs],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/options",
    response_model=ForecastRunOptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get forecast run options",
    description=(
        "Requires a Bearer access token and returns supported forecast horizons "
        "and lifecycle statuses for frontend controls."
    ),
)
async def get_forecast_run_options(
    _: Annotated[object, Depends(get_current_user)],
    forecast_service: Annotated[
        ForecastRunService,
        Depends(get_forecast_run_service),
    ],
) -> ForecastRunOptionsResponse:
    return ForecastRunOptionsResponse(
        data=ForecastRunOptionsData(**await forecast_service.get_options())
    )


@router.get(
    "/{run_id}",
    response_model=ForecastRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get forecast run detail",
    description=(
        "Requires a Bearer access token and returns a forecast run only when it "
        "belongs to the current user."
    ),
)
async def get_forecast_run(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    forecast_service: Annotated[
        ForecastRunService,
        Depends(get_forecast_run_service),
    ],
) -> ForecastRunResponse:
    run = await forecast_service.get_run(user_id=current_user.id, run_id=run_id)
    return ForecastRunResponse(
        data=ForecastRunData(run=ForecastRunPublic.model_validate(run))
    )


@router.post(
    "/{run_id}/cancel",
    response_model=ForecastRunCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel forecast run",
    description=(
        "Requires a Bearer access token and cancels an owned pending or running "
        "forecast run. Completed, failed, and already cancelled runs cannot be "
        "cancelled."
    ),
)
async def cancel_forecast_run(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    forecast_service: Annotated[
        ForecastRunService,
        Depends(get_forecast_run_service),
    ],
) -> ForecastRunCancelResponse:
    run = await forecast_service.cancel_run(user_id=current_user.id, run_id=run_id)
    return ForecastRunCancelResponse(
        data=ForecastRunData(run=ForecastRunPublic.model_validate(run))
    )
