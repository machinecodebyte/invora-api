from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.jobs.domain.exceptions import JobEnqueueError, QueueUnavailableError


class ForecastJobDispatcher:
    def __init__(self, *, queue_factory: Any) -> None:
        self.queue_factory = queue_factory

    def enqueue_forecast_processing(
        self,
        *,
        background_job_id: UUID,
        rq_job_id: str,
        forecast_run_id: UUID,
        user_id: UUID,
        queue_name: str,
        timeout_seconds: int,
        max_retries: int,
        retry_interval_seconds: int,
        result_ttl_seconds: int,
        failure_ttl_seconds: int,
    ) -> str:
        try:
            from rq import Retry

            from app.modules.jobs.tasks import process_forecast_run_job

            retry = None
            if max_retries > 1:
                retry = Retry(max=max_retries - 1, interval=retry_interval_seconds)
            queue = self.queue_factory.get_queue(queue_name)
            job = queue.enqueue(
                process_forecast_run_job,
                str(background_job_id),
                str(forecast_run_id),
                str(user_id),
                job_id=rq_job_id,
                job_timeout=timeout_seconds,
                result_ttl=result_ttl_seconds,
                failure_ttl=failure_ttl_seconds,
                retry=retry,
            )
            return str(job.id)
        except QueueUnavailableError:
            raise
        except Exception as exc:
            raise JobEnqueueError() from exc

    def get_job_status(self, *, rq_job_id: str) -> str | None:
        try:
            from rq.exceptions import NoSuchJobError
            from rq.job import Job

            job = Job.fetch(rq_job_id, connection=self.queue_factory.get_connection())
            status = job.get_status(refresh=True)
            return getattr(status, "value", str(status))
        except NoSuchJobError:
            return None
        except Exception as exc:
            raise QueueUnavailableError() from exc

    def cancel_job(self, *, rq_job_id: str) -> bool:
        try:
            from rq.exceptions import NoSuchJobError
            from rq.job import Job

            job = Job.fetch(rq_job_id, connection=self.queue_factory.get_connection())
            job.cancel()
            return True
        except NoSuchJobError:
            return True
        except Exception as exc:
            raise QueueUnavailableError() from exc

    def get_queue_health(self, *, queue_names: list[str]) -> dict[str, Any]:
        return self.queue_factory.get_health(queue_names)
