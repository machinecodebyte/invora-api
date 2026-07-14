from enum import StrEnum


class JobType(StrEnum):
    FORECAST_PROCESSING = "forecast_processing"


class JobEntityType(StrEnum):
    FORECAST_RUN = "forecast_run"


class JobStatus(StrEnum):
    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
