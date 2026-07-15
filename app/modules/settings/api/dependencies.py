from fastapi import Depends

from app.db.session import get_db_session
from app.modules.settings.application.service import SystemSettingsService
from app.modules.settings.infrastructure.repositories import SystemSettingsRepository


async def get_system_settings_service(
    session=Depends(get_db_session),
) -> SystemSettingsService:
    return SystemSettingsService(repository=SystemSettingsRepository(session))
