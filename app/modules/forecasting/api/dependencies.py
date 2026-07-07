from fastapi import Depends

from app.db.session import get_db_session
from app.modules.forecasting.application.service import ForecastRunService
from app.modules.forecasting.infrastructure.repositories import ForecastRunRepository


async def get_forecast_run_service(
    session=Depends(get_db_session),
) -> ForecastRunService:
    return ForecastRunService(repository=ForecastRunRepository(session))
