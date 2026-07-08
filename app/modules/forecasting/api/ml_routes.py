from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.forecasting.api.dependencies import get_ml_forecasting_service
from app.modules.forecasting.api.schemas import (
    MLForecastingHealthData,
    MLForecastingHealthResponse,
    MLForecastingOptionsData,
    MLForecastingOptionsResponse,
)
from app.modules.forecasting.application.service import MLForecastingService

router = APIRouter(prefix="/ml/forecasting", tags=["ML Forecasting"])


@router.get(
    "/options",
    response_model=MLForecastingOptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ML forecasting options",
    description=(
        "Requires a Bearer access token and returns supported ML forecasting "
        "model, horizon, fallback, and minimum-data settings."
    ),
)
async def get_ml_forecasting_options(
    _: Annotated[object, Depends(get_current_user)],
    ml_service: Annotated[
        MLForecastingService,
        Depends(get_ml_forecasting_service),
    ],
) -> MLForecastingOptionsResponse:
    return MLForecastingOptionsResponse(
        data=MLForecastingOptionsData(**await ml_service.get_forecasting_options())
    )


@router.get(
    "/health",
    response_model=MLForecastingHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get ML forecasting health",
    description=(
        "Requires a Bearer access token and reports whether pandas, numpy, "
        "scikit-learn, and the local forecasting pipeline are available."
    ),
)
async def get_ml_forecasting_health(
    _: Annotated[object, Depends(get_current_user)],
    ml_service: Annotated[
        MLForecastingService,
        Depends(get_ml_forecasting_service),
    ],
) -> MLForecastingHealthResponse:
    return MLForecastingHealthResponse(
        data=MLForecastingHealthData(**await ml_service.get_ml_health())
    )
