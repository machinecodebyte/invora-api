from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.modules.jobs.domain.exceptions import QueueUnavailableError
from app.modules.jobs.infrastructure.redis import RedisConnectionFactory


class RQQueueFactory:
    def __init__(self, *, redis_factory: RedisConnectionFactory) -> None:
        self.redis_factory = redis_factory
        self._queues: dict[str, Any] = {}

    def get_connection(self) -> Any:
        return self.redis_factory.get_connection()

    def get_queue(self, queue_name: str) -> Any:
        if queue_name not in self._queues:
            try:
                from rq import Queue

                self._queues[queue_name] = Queue(
                    name=queue_name,
                    connection=self.get_connection(),
                )
            except Exception as exc:
                raise QueueUnavailableError() from exc
        return self._queues[queue_name]

    def check_ready(self) -> bool:
        return self.redis_factory.ping()

    def get_health(self, queue_names: list[str]) -> dict[str, Any]:
        try:
            from rq import Worker
            from rq.registry import FailedJobRegistry, StartedJobRegistry

            self.check_ready()
            connection = self.get_connection()
            queue_stats = []
            for queue_name in queue_names:
                queue = self.get_queue(queue_name)
                started = StartedJobRegistry(queue_name, connection=connection)
                failed = FailedJobRegistry(queue_name, connection=connection)
                queue_stats.append(
                    {
                        "name": queue_name,
                        "queued_job_count": len(queue),
                        "started_job_count": len(started),
                        "failed_job_count": len(failed),
                    }
                )
            workers = Worker.all(connection=connection)
            return {
                "redis_available": True,
                "queues_available": True,
                "queues": queue_stats,
                "active_worker_count": len(workers),
                "worker_names": sorted(worker.name for worker in workers),
            }
        except Exception as exc:
            raise QueueUnavailableError() from exc


@lru_cache
def get_rq_queue_factory() -> RQQueueFactory:
    settings = get_settings()
    return RQQueueFactory(
        redis_factory=RedisConnectionFactory(redis_url=settings.REDIS_URL),
    )
