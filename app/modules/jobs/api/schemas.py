from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JobStatusLiteral = Literal[
    "queued",
    "started",
    "finished",
    "failed",
    "cancelled",
    "retrying",
]


class BackgroundJobPublic(BaseModel):
    job_id: UUID = Field(validation_alias="id")
    rq_job_id: str
    job_type: Literal["forecast_processing"]
    entity_type: Literal["forecast_run"] | None
    entity_id: UUID | None
    status: JobStatusLiteral
    attempts: int
    max_retries: int
    queue_name: str
    timeout_seconds: int
    enqueued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    error_code: str | None
    error_message: str | None
    result_summary: dict[str, Any] | None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias="job_metadata",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForecastJobEnqueueData(BaseModel):
    job_id: UUID
    rq_job_id: str
    forecast_run_id: UUID
    status: JobStatusLiteral
    queue_name: str
    enqueued_at: datetime
    status_url: str


class ForecastJobEnqueueResponse(BaseModel):
    success: Literal[True] = True
    data: ForecastJobEnqueueData


class BackgroundJobData(BaseModel):
    job: BackgroundJobPublic


class BackgroundJobResponse(BaseModel):
    success: Literal[True] = True
    data: BackgroundJobData


class BackgroundJobListData(BaseModel):
    jobs: list[BackgroundJobPublic]
    total: int
    limit: int
    offset: int


class BackgroundJobListResponse(BaseModel):
    success: Literal[True] = True
    data: BackgroundJobListData


class BackgroundJobCancelData(BaseModel):
    job: BackgroundJobPublic
    message: str


class BackgroundJobCancelResponse(BaseModel):
    success: Literal[True] = True
    data: BackgroundJobCancelData


class BackgroundJobRetryData(ForecastJobEnqueueData):
    retry_of_job_id: UUID


class BackgroundJobRetryResponse(BaseModel):
    success: Literal[True] = True
    data: BackgroundJobRetryData


class JobQueueStatsResponse(BaseModel):
    name: str
    queued_job_count: int
    started_job_count: int
    failed_job_count: int


class JobQueueHealthData(BaseModel):
    redis_available: bool
    queues_available: bool
    queues: list[JobQueueStatsResponse]
    active_worker_count: int
    worker_names: list[str]


class JobQueueHealthResponse(BaseModel):
    success: Literal[True] = True
    data: JobQueueHealthData


class BackgroundJobOptionsData(BaseModel):
    supported_job_types: tuple[Literal["forecast_processing"], ...]
    supported_statuses: tuple[JobStatusLiteral, ...]
    available_queues: tuple[str, ...]
    retry_policy: dict[str, Any]
    cancellation_policy: dict[str, str]


class BackgroundJobOptionsResponse(BaseModel):
    success: Literal[True] = True
    data: BackgroundJobOptionsData
