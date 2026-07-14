from fastapi import Depends

from app.core.config import get_settings
from app.db.session import get_db_session
from app.modules.jobs.application.dispatchers import ForecastJobDispatcher
from app.modules.jobs.application.services import BackgroundJobService
from app.modules.jobs.infrastructure.queue import get_rq_queue_factory
from app.modules.jobs.infrastructure.repositories import BackgroundJobRepository


async def get_background_job_service(
    session=Depends(get_db_session),
) -> BackgroundJobService:
    return BackgroundJobService(
        repository=BackgroundJobRepository(session),
        dispatcher=ForecastJobDispatcher(queue_factory=get_rq_queue_factory()),
        settings=get_settings(),
    )
