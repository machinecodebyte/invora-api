from __future__ import annotations

import asyncio

from app.core.config import get_settings
from app.modules.jobs.domain.exceptions import QueueUnavailableError
from app.modules.jobs.infrastructure.queue import get_rq_queue_factory


async def check_background_jobs_ready() -> bool:
    """Check the dependencies required to accept asynchronous forecast work."""
    settings = get_settings()
    if not settings.WORKER_ENABLED:
        return True

    try:
        health = await asyncio.to_thread(
            get_rq_queue_factory().get_health,
            [settings.RQ_DEFAULT_QUEUE, settings.RQ_FORECAST_QUEUE],
        )
    except QueueUnavailableError:
        return False

    return bool(
        health.get("redis_available")
        and health.get("queues_available")
        and health.get("active_worker_count", 0) > 0
    )
