from fastapi import Depends

from app.db.session import get_db_session
from app.modules.forecasting.application.service import (
    ForecastResultService,
    ForecastRunService,
    MLForecastingService,
)
from app.modules.forecasting.infrastructure.repositories import ForecastRunRepository


async def get_forecast_run_service(
    session=Depends(get_db_session),
) -> ForecastRunService:
    return ForecastRunService(repository=ForecastRunRepository(session))


async def get_ml_forecasting_service(
    session=Depends(get_db_session),
) -> MLForecastingService:
    return MLForecastingService(repository=ForecastRunRepository(session))


async def get_forecast_result_service(
    session=Depends(get_db_session),
) -> ForecastResultService:
    return ForecastResultService(repository=ForecastRunRepository(session))
