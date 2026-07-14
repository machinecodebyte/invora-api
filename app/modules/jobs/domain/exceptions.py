from app.core.exceptions import AppError


class BackgroundJobNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Background job was not found.",
            code="background_job_not_found",
            status_code=404,
        )


class QueueUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Background job queue is temporarily unavailable.",
            code="queue_unavailable",
            status_code=503,
        )


class DuplicateActiveJobError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "An active background job already exists for this resource.",
            code="duplicate_active_job",
            status_code=409,
        )


class JobNotCancellableError(AppError):
    def __init__(self, message: str = "Background job cannot be cancelled.") -> None:
        super().__init__(
            message,
            code="job_not_cancellable",
            status_code=409,
        )


class JobNotRetryableError(AppError):
    def __init__(self, message: str = "Background job cannot be retried.") -> None:
        super().__init__(
            message,
            code="job_not_retryable",
            status_code=409,
        )


class JobRetryLimitExceededError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Background job retry limit has been reached.",
            code="job_retry_limit_exceeded",
            status_code=409,
        )


class InvalidJobStatusTransitionError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Background job status transition is invalid.",
            code="invalid_job_status_transition",
            status_code=409,
        )


class WorkerUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "No background worker is currently available.",
            code="worker_unavailable",
            status_code=503,
        )


class JobEnqueueError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Background job could not be enqueued.",
            code="job_enqueue_failed",
            status_code=503,
        )


class JobExecutionError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Background job execution failed.",
            code="job_execution_failed",
            status_code=500,
        )


class InvalidJobFilterError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Background job filter is invalid.",
            code="invalid_job_filter",
            status_code=400,
        )


class ForecastRunNotProcessableJobError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Forecast run cannot be processed by a background job in its "
            "current status.",
            code="forecast_run_not_processable_for_job",
            status_code=409,
        )
