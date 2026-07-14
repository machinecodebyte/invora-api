from __future__ import annotations

from typing import Any

from app.modules.jobs.domain.exceptions import QueueUnavailableError


class RedisConnectionFactory:
    def __init__(self, *, redis_url: str) -> None:
        self.redis_url = redis_url
        self._connection: Any | None = None

    def get_connection(self) -> Any:
        if self._connection is None:
            try:
                from redis import Redis

                self._connection = Redis.from_url(
                    self.redis_url,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            except Exception as exc:
                raise QueueUnavailableError() from exc
        return self._connection

    def ping(self) -> bool:
        try:
            return bool(self.get_connection().ping())
        except Exception as exc:
            raise QueueUnavailableError() from exc
