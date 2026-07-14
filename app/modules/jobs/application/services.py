from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.modules.forecasting.domain.exceptions import ForecastRunNotFoundError
from app.modules.forecasting.domain.runs import validate_minimum_data
from app.modules.jobs.domain.enums import JobEntityType, JobStatus, JobType
from app.modules.jobs.domain.exceptions import (
    BackgroundJobNotFoundError,
    DuplicateActiveJobError,
    JobEnqueueError,
    QueueUnavailableError,
)
from app.modules.jobs.domain.rules import (
    ensure_cancellable_status,
    ensure_forecast_run_processable,
    ensure_job_sort_field,
    ensure_retryable_status,
    map_rq_status_to_job_status,
    normalize_job_sort_order,
    normalize_job_status,
    normalize_job_type,
    sanitize_result_summary,
    validate_job_date_range,
)
from app.shared.utils import utc_now


class BackgroundJobService:
    def __init__(
        self,
        *,
        repository: Any,
        dispatcher: Any,
        settings: Any,
    ) -> None:
        self.repository = repository
        self.dispatcher = dispatcher
        self.settings = settings

    async def enqueue_forecast_run(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> dict[str, Any]:
        run = await self._get_forecast_run(user_id=user_id, run_id=run_id)
        active_job = await self.repository.get_active_job_for_entity(
            user_id=user_id,
            job_type=JobType.FORECAST_PROCESSING.value,
            entity_type=JobEntityType.FORECAST_RUN.value,
            entity_id=run.id,
        )
        if active_job is not None:
            return self._enqueue_payload(active_job, forecast_run_id=run.id)

        ensure_forecast_run_processable(run.status)
        await self._validate_forecast_inputs(user_id=user_id)
        try:
            job = await self._create_forecast_processing_job(
                user_id=user_id,
                forecast_run_id=run.id,
                metadata=None,
            )
        except DuplicateActiveJobError:
            active_job = await self.repository.get_active_job_for_entity(
                user_id=user_id,
                job_type=JobType.FORECAST_PROCESSING.value,
                entity_type=JobEntityType.FORECAST_RUN.value,
                entity_id=run.id,
            )
            if active_job is not None:
                return self._enqueue_payload(active_job, forecast_run_id=run.id)
            raise
        try:
            await self._dispatch_job(job=job, forecast_run_id=run.id, user_id=user_id)
        except (QueueUnavailableError, JobEnqueueError):
            await self._mark_enqueue_failed(job)
            raise
        return self._enqueue_payload(job, forecast_run_id=run.id)

    async def list_jobs(
        self,
        *,
        user_id: UUID,
        job_type: str | None,
        status: str | None,
        entity_id: UUID | None,
        queue_name: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Any], int]:
        validate_job_date_range(date_from, date_to)
        return await self.repository.list_jobs_for_user(
            user_id=user_id,
            job_type=normalize_job_type(job_type),
            status=normalize_job_status(status),
            entity_id=entity_id,
            queue_name=_normalize_optional_string(queue_name),
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            sort_by=ensure_job_sort_field(sort_by),
            sort_order=normalize_job_sort_order(sort_order),
        )

    async def get_job(self, *, user_id: UUID, job_id: UUID) -> Any:
        job = await self.repository.get_job_for_user(user_id=user_id, job_id=job_id)
        if job is None:
            raise BackgroundJobNotFoundError()
        await self._reconcile_job_status(job)
        return job

    async def cancel_job(self, *, user_id: UUID, job_id: UUID) -> Any:
        job = await self.get_job(user_id=user_id, job_id=job_id)
        ensure_cancellable_status(job.status)
        self.dispatcher.cancel_job(rq_job_id=job.rq_job_id)
        run = None
        if (
            job.entity_type == JobEntityType.FORECAST_RUN.value
            and job.entity_id is not None
        ):
            run = await self._get_forecast_run(user_id=user_id, run_id=job.entity_id)
        try:
            await self.repository.mark_job_cancelled(job)
            if run is not None:
                await self.repository.update_forecast_run_status(
                    run,
                    {
                        "status": "cancelled",
                        "cancelled_at": utc_now(),
                        "failure_reason": None,
                    },
                )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise
        return job

    async def retry_job(self, *, user_id: UUID, job_id: UUID) -> dict[str, Any]:
        failed_job = await self.get_job(user_id=user_id, job_id=job_id)
        ensure_retryable_status(
            status=failed_job.status,
            attempts=failed_job.attempts,
            max_retries=failed_job.max_retries,
        )
        if (
            failed_job.entity_type != JobEntityType.FORECAST_RUN.value
            or failed_job.entity_id is None
        ):
            raise DuplicateActiveJobError()

        run = await self._get_forecast_run(user_id=user_id, run_id=failed_job.entity_id)
        active_job = await self.repository.get_active_job_for_entity(
            user_id=user_id,
            job_type=failed_job.job_type,
            entity_type=failed_job.entity_type,
            entity_id=failed_job.entity_id,
        )
        if active_job is not None:
            return self._enqueue_payload(active_job, forecast_run_id=run.id)

        ensure_forecast_run_processable(run.status)
        await self._validate_forecast_inputs(user_id=user_id)
        try:
            await self.repository.update_forecast_run_status(
                run,
                {
                    "status": "pending",
                    "started_at": None,
                    "failed_at": None,
                    "failure_reason": None,
                },
            )
            job = await self._create_forecast_processing_job(
                user_id=user_id,
                forecast_run_id=run.id,
                metadata={"retry_of_job_id": str(failed_job.id)},
                commit=False,
            )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise

        try:
            await self._dispatch_job(job=job, forecast_run_id=run.id, user_id=user_id)
        except (QueueUnavailableError, JobEnqueueError):
            await self._mark_enqueue_failed(job)
            raise
        return self._enqueue_payload(job, forecast_run_id=run.id)

    async def get_queue_health(self) -> dict[str, Any]:
        return self.dispatcher.get_queue_health(
            queue_names=[
                self.settings.RQ_FORECAST_QUEUE,
                self.settings.RQ_DEFAULT_QUEUE,
            ]
        )

    async def get_options(self) -> dict[str, Any]:
        return {
            "supported_job_types": (JobType.FORECAST_PROCESSING.value,),
            "supported_statuses": tuple(status.value for status in JobStatus),
            "available_queues": (
                self.settings.RQ_FORECAST_QUEUE,
                self.settings.RQ_DEFAULT_QUEUE,
            ),
            "retry_policy": {
                "manual_retry_status": JobStatus.FAILED.value,
                "max_retries": self.settings.RQ_MAX_RETRIES,
                "retry_interval_seconds": self.settings.RQ_RETRY_INTERVAL_SECONDS,
            },
            "cancellation_policy": {
                "queued_jobs": "supported",
                "started_jobs": "not_supported_without_cooperative_cancellation",
            },
        }

    async def _create_forecast_processing_job(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        metadata: dict[str, Any] | None,
        commit: bool = True,
    ) -> Any:
        job_id = uuid4()
        rq_job_id = f"forecast-processing:{job_id}"
        try:
            job = await self.repository.create_background_job(
                values={
                    "id": job_id,
                    "rq_job_id": rq_job_id,
                    "user_id": user_id,
                    "job_type": JobType.FORECAST_PROCESSING.value,
                    "entity_type": JobEntityType.FORECAST_RUN.value,
                    "entity_id": forecast_run_id,
                    "queue_name": self.settings.RQ_FORECAST_QUEUE,
                    "status": JobStatus.QUEUED.value,
                    "attempts": 0,
                    "max_retries": self.settings.RQ_MAX_RETRIES,
                    "timeout_seconds": self.settings.RQ_JOB_TIMEOUT_SECONDS,
                    "enqueued_at": utc_now(),
                    "job_metadata": metadata,
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                },
            )
            if commit:
                await self.repository.commit()
            return job
        except IntegrityError as exc:
            await self.repository.rollback()
            raise DuplicateActiveJobError() from exc

    async def _dispatch_job(
        self,
        *,
        job: Any,
        forecast_run_id: UUID,
        user_id: UUID,
    ) -> None:
        rq_job_id = self.dispatcher.enqueue_forecast_processing(
            background_job_id=job.id,
            rq_job_id=job.rq_job_id,
            forecast_run_id=forecast_run_id,
            user_id=user_id,
            queue_name=job.queue_name,
            timeout_seconds=job.timeout_seconds,
            max_retries=job.max_retries,
            retry_interval_seconds=self.settings.RQ_RETRY_INTERVAL_SECONDS,
            result_ttl_seconds=self.settings.RQ_RESULT_TTL_SECONDS,
            failure_ttl_seconds=self.settings.RQ_FAILURE_TTL_SECONDS,
        )
        if rq_job_id != job.rq_job_id:
            await self.repository.update_rq_job_id(job, rq_job_id)
            await self.repository.commit()

    async def _mark_enqueue_failed(self, job: Any) -> None:
        try:
            await self.repository.mark_job_failed(
                job,
                error_code="queue_unavailable",
                error_message="Background job queue is temporarily unavailable.",
                result_summary={"stage": "enqueue"},
            )
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()

    async def _get_forecast_run(self, *, user_id: UUID, run_id: UUID) -> Any:
        run = await self.repository.get_forecast_run_for_user(
            user_id=user_id,
            run_id=run_id,
        )
        if run is None:
            raise ForecastRunNotFoundError()
        return run

    async def _validate_forecast_inputs(self, *, user_id: UUID) -> None:
        validate_minimum_data(
            active_product_count=await self.repository.count_user_active_products(
                user_id=user_id,
            ),
            sales_transaction_count=await self.repository.count_user_sales_transactions(
                user_id=user_id,
            ),
        )

    async def _reconcile_job_status(self, job: Any) -> None:
        if job.status in {"finished", "failed", "cancelled"}:
            return
        try:
            rq_status = self.dispatcher.get_job_status(rq_job_id=job.rq_job_id)
        except QueueUnavailableError:
            return
        mapped_status = map_rq_status_to_job_status(rq_status)
        if mapped_status is None or mapped_status == job.status:
            return
        try:
            if mapped_status == JobStatus.CANCELLED.value:
                await self.repository.mark_job_cancelled(job)
            elif mapped_status == JobStatus.FAILED.value:
                await self.repository.mark_job_failed(
                    job,
                    error_code=job.error_code or "rq_job_failed",
                    error_message=job.error_message or "Background job failed in RQ.",
                )
            elif mapped_status == JobStatus.FINISHED.value:
                await self.repository.mark_job_finished(
                    job,
                    result_summary=sanitize_result_summary(
                        job.result_summary or {"reconciled_from_rq": True}
                    ),
                )
            elif mapped_status == JobStatus.STARTED.value:
                await self.repository.update_job_status(job, status=mapped_status)
            await self.repository.commit()
        except Exception:
            await self.repository.rollback()
            raise

    def _enqueue_payload(self, job: Any, *, forecast_run_id: UUID) -> dict[str, Any]:
        return {
            "job": job,
            "job_id": job.id,
            "rq_job_id": job.rq_job_id,
            "forecast_run_id": forecast_run_id,
            "status": job.status,
            "queue_name": job.queue_name,
            "enqueued_at": job.enqueued_at,
            "status_url": f"{self.settings.API_V1_PREFIX}/jobs/{job.id}",
        }


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
