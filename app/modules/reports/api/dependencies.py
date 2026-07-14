from fastapi import Depends

from app.db.session import get_db_session
from app.modules.reports.application.service import ReportsService
from app.modules.reports.infrastructure.repositories import ReportsRepository


async def get_reports_service(session=Depends(get_db_session)) -> ReportsService:
    return ReportsService(repository=ReportsRepository(session))
