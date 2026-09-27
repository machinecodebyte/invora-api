from app.modules.jobs.infrastructure.queue import RQQueueFactory


class FakeRedisConnection:
    def __init__(
        self,
        *,
        memberships: dict[str, set[bytes]],
        metadata: dict[str, dict[bytes, bytes]] | None = None,
    ) -> None:
        self.requested_queue_keys: list[str] = []
        self.memberships = memberships
        self.metadata = metadata or {}

    def smembers(self, key: str) -> set[bytes]:
        self.requested_queue_keys.append(key)
        return self.memberships.get(key, set())

    def ttl(self, key: str) -> int:
        return 120 if key.endswith("active-worker") else -2

    def hgetall(self, key: str) -> dict[bytes, bytes]:
        return self.metadata.get(key, {})


def test_active_worker_names_uses_live_queue_registrations() -> None:
    connection = FakeRedisConnection(
        memberships={
            "rq:workers:invora-default": {
                b"rq:worker:active-worker",
                b"rq:worker:expired-worker",
                b"rq:worker:default-only",
            },
            "rq:workers:invora-forecasting": {
                b"rq:worker:active-worker",
                b"rq:worker:expired-worker",
            },
        }
    )

    worker_names = RQQueueFactory._active_worker_names(
        connection,
        required_queue_names=["invora-default", "invora-forecasting"],
    )

    assert connection.requested_queue_keys == [
        "rq:workers:invora-default",
        "rq:workers:invora-forecasting",
    ]
    assert worker_names == ["active-worker"]


def test_active_worker_names_excludes_dead_or_wrong_queue_workers() -> None:
    dead_connection = FakeRedisConnection(
        memberships={
            "rq:workers:invora-default": {b"rq:worker:active-worker"},
            "rq:workers:invora-forecasting": {b"rq:worker:active-worker"},
        },
        metadata={"rq:worker:active-worker": {b"death": b"2026-09-27T00:01:00Z"}},
    )
    wrong_queue_connection = FakeRedisConnection(
        memberships={"rq:workers:invora-default": {b"rq:worker:active-worker"}},
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
