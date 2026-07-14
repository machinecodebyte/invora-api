from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.exceptions import AppError
from app.modules.jobs.domain.enums import JobEntityType, JobStatus, JobType
from app.modules.jobs.domain.exceptions import (
    ForecastRunNotProcessableJobError,
    InvalidJobFilterError,
    InvalidJobStatusTransitionError,
    JobNotCancellableError,
    JobNotRetryableError,
    JobRetryLimitExceededError,
)

ACTIVE_JOB_STATUSES = (
    JobStatus.QUEUED.value,
    JobStatus.STARTED.value,
    JobStatus.RETRYING.value,
)
TERMINAL_JOB_STATUSES = (
    JobStatus.FINISHED.value,
    JobStatus.FAILED.value,
    JobStatus.CANCELLED.value,
)
SUPPORTED_JOB_TYPES = tuple(job_type.value for job_type in JobType)
SUPPORTED_ENTITY_TYPES = tuple(entity_type.value for entity_type in JobEntityType)
SUPPORTED_JOB_STATUSES = tuple(status.value for status in JobStatus)
JOB_SORT_FIELDS = (
    "created_at",
    "updated_at",
    "enqueued_at",
    "started_at",
    "completed_at",
    "failed_at",
    "cancelled_at",
    "status",
    "job_type",
    "queue_name",
)

ALLOWED_STATUS_TRANSITIONS = {
    JobStatus.QUEUED.value: {
        JobStatus.STARTED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
    },
    JobStatus.STARTED.value: {
        JobStatus.FINISHED.value,
        JobStatus.FAILED.value,
        JobStatus.RETRYING.value,
    },
    JobStatus.RETRYING.value: {
        JobStatus.STARTED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
    },
    JobStatus.FINISHED.value: set(),
    JobStatus.FAILED.value: set(),
    JobStatus.CANCELLED.value: set(),
}


def normalize_job_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_JOB_TYPES:
        raise InvalidJobFilterError()
    return normalized


def normalize_job_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_JOB_STATUSES:
        raise InvalidJobFilterError()
    return normalized


def validate_job_date_range(
    date_from: datetime | None,
    date_to: datetime | None,
) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise InvalidJobFilterError()


def ensure_job_sort_field(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in JOB_SORT_FIELDS:
        raise InvalidJobFilterError()
    return normalized


def normalize_job_sort_order(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"asc", "desc"}:
        raise InvalidJobFilterError()
    return normalized


def ensure_valid_status_transition(current_status: str, next_status: str) -> None:
    current = current_status.strip().lower()
    next_value = next_status.strip().lower()
    if current == next_value:
        return
    if next_value not in ALLOWED_STATUS_TRANSITIONS.get(current, set()):
        raise InvalidJobStatusTransitionError()


def ensure_cancellable_status(status: str) -> None:
    normalized = status.strip().lower()
    if normalized == JobStatus.QUEUED.value:
        return
    if normalized == JobStatus.STARTED.value:
        raise JobNotCancellableError(
            "Started background jobs cannot be cancelled safely by this worker.",
        )
    raise JobNotCancellableError()


def ensure_retryable_status(*, status: str, attempts: int, max_retries: int) -> None:
    if status.strip().lower() != JobStatus.FAILED.value:
        raise JobNotRetryableError("Only failed background jobs can be retried.")
    if attempts >= max_retries:
        raise JobRetryLimitExceededError()


def ensure_forecast_run_processable(status: str) -> None:
    if status.strip().lower() in {"pending", "failed"}:
        return
    raise ForecastRunNotProcessableJobError()


def map_rq_status_to_job_status(status: str | None) -> str | None:
    if status is None:
        return None
    normalized = str(status).strip().lower()
    if normalized in {"queued", "deferred", "scheduled"}:
        return JobStatus.QUEUED.value
    if normalized in {"started", "busy"}:
        return JobStatus.STARTED.value
    if normalized == "finished":
        return JobStatus.FINISHED.value
    if normalized == "failed":
        return JobStatus.FAILED.value
    if normalized in {"canceled", "cancelled", "stopped"}:
        return JobStatus.CANCELLED.value
    return None


def is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, AppError):
        return False
    retryable_types: tuple[type[BaseException], ...] = (
        TimeoutError,
        ConnectionError,
        OSError,
    )
    try:
        from redis.exceptions import RedisError

        retryable_types = (*retryable_types, RedisError)
    except Exception:
        pass
    try:
        from sqlalchemy.exc import SQLAlchemyError

        retryable_types = (*retryable_types, SQLAlchemyError)
    except Exception:
        pass
    return isinstance(exc, retryable_types)


def sanitized_error(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, AppError):
        code = exc.code
        message = exc.message
    else:
        code = "job_execution_failed"
        message = "Background job execution failed."
    return code[:128], " ".join(message.split())[:500]


def sanitize_result_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"result": _safe_value(value)}
    return {
        str(key)[:64]: _safe_value(item)
        for key, item in list(value.items())[:20]
        if not str(key).startswith("_")
    }


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | float | str):
        if isinstance(value, str):
            return value[:500]
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            str(key)[:64]: _safe_value(item)
            for key, item in list(value.items())[:20]
            if not str(key).startswith("_")
        }
    if isinstance(value, list | tuple):
        return [_safe_value(item) for item in value[:20]]
    return str(value)[:500]
