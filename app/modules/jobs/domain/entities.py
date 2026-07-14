from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QueueStats:
    name: str
    queued_job_count: int
    started_job_count: int
    failed_job_count: int
