from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.forecasting.api.dependencies import get_forecast_result_service
from app.modules.forecasting.api.schemas import (
    ForecastChartData,
    ForecastChartResponse,
    ForecastMetricsData,
    ForecastMetricsResponse,
    ForecastPredictionListData,
    ForecastPredictionListResponse,
    ForecastResultOverviewData,
    ForecastResultOverviewResponse,
    ProductForecastDetailData,
    ProductForecastDetailResponse,
)
from app.modules.forecasting.application.service import ForecastResultService

router = APIRouter(prefix="/forecast-results", tags=["Forecast Results"])


@router.get(
    "/runs/{run_id}",
    response_model=ForecastResultOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get forecast result overview",
    description=(
        "Requires a Bearer access token and returns an overview for an owned "
        "completed forecast run with persisted predictions."
    ),
)
async def get_forecast_result_overview(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    result_service: Annotated[
        ForecastResultService,
        Depends(get_forecast_result_service),
    ],
) -> ForecastResultOverviewResponse:
    result = await result_service.get_result_overview(
        user_id=current_user.id,
        run_id=run_id,
    )
    return ForecastResultOverviewResponse(data=ForecastResultOverviewData(**result))


@router.get(
    "/runs/{run_id}/predictions",
    response_model=ForecastPredictionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List forecast predictions",
    description=(
        "Requires a Bearer access token and returns paginated product/date "
        "predictions for an owned forecast run. Inventory fields are context "
        "only and no reorder quantity is calculated."
    ),
)
async def list_forecast_predictions(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    result_service: Annotated[
        ForecastResultService,
        Depends(get_forecast_result_service),
    ],
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="forecast_date"),
    sort_order: str = Query(default="asc"),
) -> ForecastPredictionListResponse:
    result = await result_service.list_predictions(
        user_id=current_user.id,
        run_id=run_id,
        product_id=product_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ForecastPredictionListResponse(data=ForecastPredictionListData(**result))


@router.get(
    "/runs/{run_id}/metrics",
    response_model=ForecastMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get forecast model metrics",
    description=(
        "Requires a Bearer access token and returns persisted model metrics for "
        "an owned forecast run."
    ),
)
async def get_forecast_metrics(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    result_service: Annotated[
        ForecastResultService,
        Depends(get_forecast_result_service),
    ],
) -> ForecastMetricsResponse:
    result = await result_service.get_metrics(user_id=current_user.id, run_id=run_id)
    return ForecastMetricsResponse(data=ForecastMetricsData(**result))


@router.get(
    "/runs/{run_id}/chart",
    response_model=ForecastChartResponse,
    status_code=status.HTTP_200_OK,
    summary="Get forecast chart data",
    description=(
        "Requires a Bearer access token and returns chart-friendly predicted "
        "demand by day, week, or month. Actual sales are included for matching "
        "forecast periods when available, otherwise they are null."
    ),
)
async def get_forecast_chart(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    result_service: Annotated[
        ForecastResultService,
        Depends(get_forecast_result_service),
    ],
    product_id: UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    interval: str = Query(default="day"),
) -> ForecastChartResponse:
    result = await result_service.get_chart_data(
        user_id=current_user.id,
        run_id=run_id,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        interval=interval,
    )
    return ForecastChartResponse(data=ForecastChartData(**result))


@router.get(
    "/runs/{run_id}/products/{product_id}",
    response_model=ProductForecastDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product forecast detail",
    description=(
        "Requires a Bearer access token and returns all persisted forecast "
        "points for one owned product in an owned forecast run."
    ),
)
async def get_product_forecast_detail(
    run_id: UUID,
    product_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    result_service: Annotated[
        ForecastResultService,
        Depends(get_forecast_result_service),
    ],
) -> ProductForecastDetailResponse:
    result = await result_service.get_product_forecast_detail(
        user_id=current_user.id,
        run_id=run_id,
        product_id=product_id,
    )
    return ProductForecastDetailResponse(data=ProductForecastDetailData(**result))
