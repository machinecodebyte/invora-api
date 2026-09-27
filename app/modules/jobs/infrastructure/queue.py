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
            worker_names = self._active_worker_names(
                connection,
                required_queue_names=queue_names,
            )
            return {
                "redis_available": True,
                "queues_available": True,
                "queues": queue_stats,
                "active_worker_count": len(worker_names),
                "worker_names": worker_names,
            }
        except Exception as exc:
            raise QueueUnavailableError() from exc

    @staticmethod
    def _active_worker_names(
        connection: Any,
        *,
        required_queue_names: list[str],
    ) -> list[str]:
        """Return live workers registered for every queue required by this API.

        RQ stores queue-to-worker membership in ``rq:workers:<queue>`` sets.
        In RQ 2.x, a long-running worker heartbeat can retain only
        ``last_heartbeat`` in the worker hash, so hash fields cannot reliably
        establish its queue assignment. Intersect the documented registration
        sets and use the worker-key TTL as the liveness boundary instead.
        """
        worker_names: list[str] = []
        prefix = "rq:worker:"
        registered_workers = [
            {
                raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
                for raw_key in connection.smembers(f"rq:workers:{queue_name}")
            }
            for queue_name in required_queue_names
        ]
        if not registered_workers:
            return worker_names

        for key in set.intersection(*registered_workers):
            if not key.startswith(prefix) or connection.ttl(key) <= 0:
                continue

            raw_metadata = connection.hgetall(key)
            metadata = {
                (
                    raw_field.decode()
                    if isinstance(raw_field, bytes)
                    else str(raw_field)
                ): raw_value.decode()
                if isinstance(raw_value, bytes)
                else str(raw_value)
                for raw_field, raw_value in raw_metadata.items()
            }
            if "death" not in metadata:
                worker_names.append(key.removeprefix(prefix))
        return sorted(worker_names)


@lru_cache
def get_rq_queue_factory() -> RQQueueFactory:
    settings = get_settings()
    return RQQueueFactory(
        redis_factory=RedisConnectionFactory(redis_url=settings.REDIS_URL),
    )
