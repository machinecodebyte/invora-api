from __future__ import annotations

import logging
import os
import socket
import sys

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> int:
    try:
        settings = get_settings()
        configure_logging(settings.LOG_LEVEL)
        from redis import Redis
        from rq import Queue, Worker

        connection = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        connection.ping()
        queue_names = [settings.RQ_FORECAST_QUEUE, settings.RQ_DEFAULT_QUEUE]
        queues = [Queue(name, connection=connection) for name in queue_names]
        worker_name = (
            f"{settings.RQ_WORKER_NAME_PREFIX}-{socket.gethostname()}-{os.getpid()}"
        )
        logger.info(
            "background_worker_starting",
            extra={"worker_name": worker_name, "queues": queue_names},
        )
        worker = Worker(queues, connection=connection, name=worker_name)
        worker.work(with_scheduler=False)
        return 0
    except Exception:
        logger.exception("background_worker_startup_failed", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
