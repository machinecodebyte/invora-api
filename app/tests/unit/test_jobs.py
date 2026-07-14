from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import AppError
from app.modules.jobs.domain.enums import JobEntityType, JobStatus, JobType
from app.modules.jobs.domain.exceptions import (
    InvalidJobFilterError,
    InvalidJobStatusTransitionError,
    JobNotCancellableError,
    JobNotRetryableError,
    JobRetryLimitExceededError,
)
from app.modules.jobs.domain.rules import (
    ensure_cancellable_status,
    ensure_job_sort_field,
    ensure_retryable_status,
    ensure_valid_status_transition,
    is_retryable_exception,
    map_rq_status_to_job_status,
    normalize_job_sort_order,
    sanitize_result_summary,
)
from app.modules.jobs.tasks import execute_forecast_processing_job
from app.shared.utils import utc_now


@dataclass(slots=True)
class JobObject:
    id: UUID
    rq_job_id: str
    user_id: UUID
    job_type: str
    entity_type: str
    entity_id: UUID
    queue_name: str
    status: str
    attempts: int
    max_retries: int
    started_at: object | None = None
    completed_at: object | None = None
    failed_at: object | None = None
    error_code: str | None = None
    error_message: str | None = None
    result_summary: dict | None = None


class TaskRepository:
    def __init__(self, job: JobObject) -> None:
        self.job = job
        self.commits = 0
        self.rollbacks = 0

    async def get_job_by_id(self, *, job_id: UUID) -> JobObject | None:
        if self.job.id == job_id:
            return self.job
        return None

    async def mark_job_started(self, job: JobObject) -> JobObject:
        job.status = JobStatus.STARTED.value
        job.attempts += 1
        job.started_at = utc_now()
        return job

    async def mark_job_finished(
        self,
        job: JobObject,
        *,
        result_summary: dict | None,
    ) -> JobObject:
        job.status = JobStatus.FINISHED.value
        job.completed_at = utc_now()
        job.result_summary = result_summary
        return job

    async def mark_job_failed(
        self,
        job: JobObject,
        *,
        error_code: str,
        error_message: str,
        result_summary: dict | None = None,
    ) -> JobObject:
        job.status = JobStatus.FAILED.value
        job.failed_at = utc_now()
        job.error_code = error_code
        job.error_message = error_message
        job.result_summary = result_summary
        return job

    async def mark_job_retrying(
        self,
        job: JobObject,
        *,
        error_code: str,
        error_message: str,
    ) -> JobObject:
        job.status = JobStatus.RETRYING.value
        job.error_code = error_code
        job.error_message = error_message
        return job

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class SuccessfulMLService:
    async def process_forecast_run(self, *, user_id: UUID, run_id: UUID) -> dict:
        return {
            "run_id": run_id,
            "status": "completed",
            "horizon_days": 7,
            "total_products": 1,
            "total_sales_records": 2,
            "predictions_created": 7,
        }


class FailingMLService:
    async def process_forecast_run(self, *, user_id: UUID, run_id: UUID) -> dict:
        raise AppError("No data.", code="no_data", status_code=409)


def add_numbers_job(left: int, right: int) -> int:
    return left + right


def _job(
    *,
    user_id: UUID | None = None,
    run_id: UUID | None = None,
    status: str = JobStatus.QUEUED.value,
    attempts: int = 0,
) -> JobObject:
    user_id = user_id or uuid4()
    run_id = run_id or uuid4()
    job_id = uuid4()
    return JobObject(
        id=job_id,
        rq_job_id=f"forecast-processing:{job_id}",
        user_id=user_id,
        job_type=JobType.FORECAST_PROCESSING.value,
        entity_type=JobEntityType.FORECAST_RUN.value,
        entity_id=run_id,
        queue_name="invora-forecasting",
        status=status,
        attempts=attempts,
        max_retries=3,
    )


def test_job_status_transitions_are_explicit() -> None:
    ensure_valid_status_transition("queued", "started")
    ensure_valid_status_transition("started", "finished")
    ensure_valid_status_transition("started", "retrying")
    ensure_valid_status_transition("retrying", "failed")

    with pytest.raises(InvalidJobStatusTransitionError):
        ensure_valid_status_transition("finished", "queued")


def test_cancellation_rules_allow_only_queued_jobs() -> None:
    ensure_cancellable_status("queued")

    with pytest.raises(JobNotCancellableError):
        ensure_cancellable_status("started")
    with pytest.raises(JobNotCancellableError):
        ensure_cancellable_status("finished")


def test_retry_rules_require_failed_status_and_available_attempts() -> None:
    ensure_retryable_status(status="failed", attempts=1, max_retries=3)

    with pytest.raises(JobNotRetryableError):
        ensure_retryable_status(status="queued", attempts=1, max_retries=3)
    with pytest.raises(JobRetryLimitExceededError):
        ensure_retryable_status(status="failed", attempts=3, max_retries=3)


def test_rq_status_mapping_and_safe_filter_validation() -> None:
    assert map_rq_status_to_job_status("queued") == "queued"
    assert map_rq_status_to_job_status("started") == "started"
    assert map_rq_status_to_job_status("finished") == "finished"
    assert map_rq_status_to_job_status("failed") == "failed"
    assert map_rq_status_to_job_status("canceled") == "cancelled"
    assert ensure_job_sort_field("created_at") == "created_at"
    assert normalize_job_sort_order("asc") == "asc"

    with pytest.raises(InvalidJobFilterError):
        ensure_job_sort_field("unsafe_sql")
    with pytest.raises(InvalidJobFilterError):
        normalize_job_sort_order("sideways")


def test_result_summary_is_sanitized() -> None:
    summary = sanitize_result_summary(
        {
            "safe": "x" * 600,
            "_private": "hidden",
            "nested": {"value": 1},
        }
    )

    assert "_private" not in summary
    assert len(summary["safe"]) == 500
    assert summary["nested"]["value"] == 1


def test_exception_classification_keeps_domain_failures_non_retryable() -> None:
    assert not is_retryable_exception(
        AppError("Invalid state.", code="invalid_state", status_code=409)
    )
    assert is_retryable_exception(ConnectionError("temporary connection issue"))


@pytest.mark.asyncio
async def test_worker_task_success_marks_job_finished() -> None:
    user_id = uuid4()
    run_id = uuid4()
    job = _job(user_id=user_id, run_id=run_id)
    repository = TaskRepository(job)

    result = await execute_forecast_processing_job(
        jobs_repository=repository,
        ml_service=SuccessfulMLService(),
        background_job_id=job.id,
        forecast_run_id=run_id,
        user_id=user_id,
    )

    assert job.status == "finished"
    assert job.attempts == 1
    assert job.completed_at is not None
    assert result["predictions_created"] == 7
    assert repository.commits >= 2


@pytest.mark.asyncio
async def test_worker_task_domain_failure_marks_job_failed() -> None:
    user_id = uuid4()
    run_id = uuid4()
    job = _job(user_id=user_id, run_id=run_id)
    repository = TaskRepository(job)

    result = await execute_forecast_processing_job(
        jobs_repository=repository,
        ml_service=FailingMLService(),
        background_job_id=job.id,
        forecast_run_id=run_id,
        user_id=user_id,
    )

    assert result == {"status": "failed", "error_code": "no_data"}
    assert job.status == "failed"
    assert job.failed_at is not None
    assert job.error_code == "no_data"


def test_rq_simple_worker_executes_enqueued_job() -> None:
    import fakeredis
    from rq import Queue, SimpleWorker

    connection = fakeredis.FakeRedis()
    queue = Queue("invora-test-forecasting", connection=connection)
    job = queue.enqueue(add_numbers_job, 2, 3)

    worker = SimpleWorker([queue], connection=connection)
    worker.work(burst=True)
    job.refresh()

    assert job.is_finished
    assert job.return_value() == 5
