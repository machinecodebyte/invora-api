from fastapi import Depends

from app.db.session import get_db_session
from app.modules.dashboard.application.service import DashboardAnalyticsService
from app.modules.dashboard.infrastructure.repositories import (
    DashboardAnalyticsRepository,
)


async def get_dashboard_analytics_service(
    session=Depends(get_db_session),
) -> DashboardAnalyticsService:
    return DashboardAnalyticsService(repository=DashboardAnalyticsRepository(session))
