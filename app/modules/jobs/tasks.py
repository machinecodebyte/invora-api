from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.forecasting.application.service import MLForecastingService
from app.modules.forecasting.infrastructure.repositories import ForecastRunRepository
from app.modules.jobs.domain.enums import JobEntityType, JobStatus, JobType
from app.modules.jobs.domain.exceptions import JobExecutionError
from app.modules.jobs.domain.rules import (
    is_retryable_exception,
    sanitize_result_summary,
    sanitized_error,
)
from app.modules.jobs.infrastructure.repositories import BackgroundJobRepository

logger = logging.getLogger(__name__)


def process_forecast_run_job(
    background_job_id: str,
    forecast_run_id: str,
    user_id: str,
) -> dict[str, Any]:
    return asyncio.run(
        _process_forecast_run_job_async(
            background_job_id=UUID(str(background_job_id)),
            forecast_run_id=UUID(str(forecast_run_id)),
            user_id=UUID(str(user_id)),
        )
    )


async def _process_forecast_run_job_async(
    *,
    background_job_id: UUID,
    forecast_run_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        jobs_repository = BackgroundJobRepository(session)
        ml_service = MLForecastingService(
            repository=ForecastRunRepository(session),
        )
        return await execute_forecast_processing_job(
            jobs_repository=jobs_repository,
            ml_service=ml_service,
            background_job_id=background_job_id,
            forecast_run_id=forecast_run_id,
            user_id=user_id,
        )


async def execute_forecast_processing_job(
    *,
    jobs_repository: Any,
    ml_service: Any,
    background_job_id: UUID,
    forecast_run_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    started = perf_counter()
    job = await jobs_repository.get_job_by_id(job_id=background_job_id)
    if job is None:
        raise JobExecutionError()
    _validate_job_payload(
        job=job,
        forecast_run_id=forecast_run_id,
        user_id=user_id,
    )
    if job.status == JobStatus.CANCELLED.value:
        return {"status": JobStatus.CANCELLED.value}

    try:
        await jobs_repository.mark_job_started(job)
        await jobs_repository.commit()
        logger.info(
            "background_job_started",
            extra=_log_fields(job=job, forecast_run_id=forecast_run_id),
        )
        result = await ml_service.process_forecast_run(
            user_id=user_id,
            run_id=forecast_run_id,
        )
        summary = sanitize_result_summary(
            {
                "forecast_run_id": str(forecast_run_id),
                "status": result.get("status"),
                "horizon_days": result.get("horizon_days"),
                "total_products": result.get("total_products"),
                "total_sales_records": result.get("total_sales_records"),
                "predictions_created": result.get("predictions_created"),
                "duration_ms": int((perf_counter() - started) * 1000),
            }
        )
        await jobs_repository.mark_job_finished(job, result_summary=summary)
        await jobs_repository.commit()
        logger.info(
            "background_job_finished",
            extra={
                **_log_fields(job=job, forecast_run_id=forecast_run_id),
                "duration_ms": summary["duration_ms"],
            },
        )
        return summary
    except AppError as exc:
        await _mark_non_retryable_failure(
            jobs_repository=jobs_repository,
            job=job,
            exc=exc,
            started=started,
            forecast_run_id=forecast_run_id,
        )
        return {"status": JobStatus.FAILED.value, "error_code": exc.code}
    except Exception as exc:
        await _mark_unexpected_failure(
            jobs_repository=jobs_repository,
            job=job,
            exc=exc,
            started=started,
            forecast_run_id=forecast_run_id,
        )
        raise


def _validate_job_payload(*, job: Any, forecast_run_id: UUID, user_id: UUID) -> None:
    if (
        job.user_id != user_id
        or job.job_type != JobType.FORECAST_PROCESSING.value
        or job.entity_type != JobEntityType.FORECAST_RUN.value
        or job.entity_id != forecast_run_id
    ):
        raise JobExecutionError()


async def _mark_non_retryable_failure(
    *,
    jobs_repository: Any,
    job: Any,
    exc: Exception,
    started: float,
    forecast_run_id: UUID,
) -> None:
    code, message = sanitized_error(exc)
    summary = sanitize_result_summary(
        {
            "forecast_run_id": str(forecast_run_id),
            "status": JobStatus.FAILED.value,
            "error_code": code,
            "duration_ms": int((perf_counter() - started) * 1000),
        }
    )
    try:
        await jobs_repository.mark_job_failed(
            job,
            error_code=code,
            error_message=message,
            result_summary=summary,
        )
        await jobs_repository.commit()
    except Exception:
        await jobs_repository.rollback()
        raise
    logger.warning(
        "background_job_failed",
        extra={**_log_fields(job=job, forecast_run_id=forecast_run_id), "error": code},
    )


async def _mark_unexpected_failure(
    *,
    jobs_repository: Any,
    job: Any,
    exc: Exception,
    started: float,
    forecast_run_id: UUID,
) -> None:
    code, message = sanitized_error(exc)
    summary = sanitize_result_summary(
        {
            "forecast_run_id": str(forecast_run_id),
            "status": JobStatus.FAILED.value,
            "error_code": code,
            "duration_ms": int((perf_counter() - started) * 1000),
        }
    )
    try:
        if is_retryable_exception(exc) and job.attempts < job.max_retries:
            await jobs_repository.mark_job_retrying(
                job,
                error_code=code,
                error_message=message,
            )
        else:
            await jobs_repository.mark_job_failed(
                job,
                error_code=code,
                error_message=message,
                result_summary=summary,
            )
        await jobs_repository.commit()
    except Exception:
        await jobs_repository.rollback()
        raise
    logger.exception(
        "background_job_unexpected_failure",
        extra={**_log_fields(job=job, forecast_run_id=forecast_run_id), "error": code},
        exc_info=True,
    )


def _log_fields(*, job: Any, forecast_run_id: UUID) -> dict[str, Any]:
    return {
        "job_id": str(job.id),
        "rq_job_id": job.rq_job_id,
        "job_type": job.job_type,
        "forecast_run_id": str(forecast_run_id),
        "user_id": str(job.user_id),
        "queue_name": job.queue_name,
        "attempt": job.attempts,
        "status": job.status,
    }
