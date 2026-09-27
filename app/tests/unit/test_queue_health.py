from app.modules.jobs.infrastructure.queue import RQQueueFactory


class FakeRedisConnection:
    def __init__(self, metadata: dict[bytes, bytes] | None = None) -> None:
        self.requested_match: str | None = None
        self.metadata = metadata

    def scan_iter(self, *, match: str):
        self.requested_match = match
        return iter(
            [
                b"rq:worker:active-worker",
                b"rq:worker:expired-worker",
            ]
        )

    def ttl(self, key: str) -> int:
        return 120 if key.endswith("active-worker") else -2

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        if self.metadata is not None:
            return self.metadata
        if key.endswith("active-worker"):
            return {
                b"birth": b"2026-09-27T00:00:00Z",
                b"queues": b"invora-default,invora-forecasting",
            }
        return {}


def test_active_worker_names_uses_non_expired_rq_worker_keys() -> None:
    connection = FakeRedisConnection()

    worker_names = RQQueueFactory._active_worker_names(
        connection,
        required_queue_names=["invora-default", "invora-forecasting"],
    )

    assert connection.requested_match == "rq:worker:*"
    assert worker_names == ["active-worker"]


def test_active_worker_names_excludes_dead_or_wrong_queue_workers() -> None:
    dead_connection = FakeRedisConnection(
        {
            b"birth": b"2026-09-27T00:00:00Z",
            b"death": b"2026-09-27T00:01:00Z",
            b"queues": b"invora-default,invora-forecasting",
        }
    )
    wrong_queue_connection = FakeRedisConnection(
        {
            b"birth": b"2026-09-27T00:00:00Z",
            b"queues": b"invora-default",
        }
    )

    assert (
        RQQueueFactory._active_worker_names(
            dead_connection,
            required_queue_names=["invora-default", "invora-forecasting"],
        )
        == []
    )
    assert (
        RQQueueFactory._active_worker_names(
            wrong_queue_connection,
            required_queue_names=["invora-default", "invora-forecasting"],
        )
        == []
    )
