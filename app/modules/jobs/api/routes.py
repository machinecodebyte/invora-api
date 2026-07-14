from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.jobs.api.dependencies import get_background_job_service
from app.modules.jobs.api.schemas import (
    BackgroundJobCancelData,
    BackgroundJobCancelResponse,
    BackgroundJobData,
    BackgroundJobListData,
    BackgroundJobListResponse,
    BackgroundJobOptionsData,
    BackgroundJobOptionsResponse,
    BackgroundJobPublic,
    BackgroundJobResponse,
    BackgroundJobRetryData,
    BackgroundJobRetryResponse,
    ForecastJobEnqueueData,
    ForecastJobEnqueueResponse,
    JobQueueHealthData,
    JobQueueHealthResponse,
)
from app.modules.jobs.application.services import BackgroundJobService

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


@router.post(
    "/forecast-runs/{run_id}",
    response_model=ForecastJobEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue forecast run processing",
    description=(
        "Requires a Bearer access token and enqueues asynchronous ML forecast "
        "processing for an owned pending or failed forecast run. The response "
        "is accepted immediately; clients should poll the returned status URL."
    ),
    responses={401: {"description": "Missing or invalid access token"}},
)
async def enqueue_forecast_run_job(
    run_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    jobs_service: Annotated[
        BackgroundJobService,
        Depends(get_background_job_service),
    ],
) -> ForecastJobEnqueueResponse:
    result = await jobs_service.enqueue_forecast_run(
        user_id=current_user.id,
        run_id=run_id,
    )
    return ForecastJobEnqueueResponse(data=ForecastJobEnqueueData(**result))


@router.get(
    "",
    response_model=BackgroundJobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List background jobs",
    description=(
        "Requires a Bearer access token and returns only the current user's "
        "background jobs with safe filters and sorting."
    ),
)
async def list_background_jobs(
    current_user: Annotated[object, Depends(get_current_user)],
    jobs_service: Annotated[
        BackgroundJobService,
        Depends(get_background_job_service),
    ],
    job_type: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    entity_id: UUID | None = Query(default=None),
    queue_name: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
) -> BackgroundJobListResponse:
    jobs, total = await jobs_service.list_jobs(
        user_id=current_user.id,
        job_type=job_type,
        status=status_filter,
        entity_id=entity_id,
        queue_name=queue_name,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return BackgroundJobListResponse(
        data=BackgroundJobListData(
            jobs=[BackgroundJobPublic.model_validate(job) for job in jobs],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/health",
    response_model=JobQueueHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get background job queue health",
    description=(
        "Requires a Bearer access token and returns safe Redis, queue, and "
        "worker health information without exposing credentials."
    ),
    responses={503: {"description": "Redis or RQ queue is unavailable"}},
)
async def get_background_jobs_health(
    _: Annotated[object, Depends(get_current_user)],
    jobs_service: Annotated[
        BackgroundJobService,
        Depends(get_background_job_service),
    ],
) -> JobQueueHealthResponse:
    return JobQueueHealthResponse(
        data=JobQueueHealthData(**await jobs_service.get_queue_health())
    )


@router.get(
    "/options",
    response_model=BackgroundJobOptionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get background job options",
    description=(
        "Requires a Bearer access token and returns supported job types, "
        "statuses, queues, retry policy, and cancellation policy."
    ),
)
async def get_background_job_options(
    _: Annotated[object, Depends(get_current_user)],
    jobs_service: Annotated[
        BackgroundJobService,
        Depends(get_background_job_service),
    ],
) -> BackgroundJobOptionsResponse:
    return BackgroundJobOptionsResponse(
        data=BackgroundJobOptionsData(**await jobs_service.get_options())
    )


@router.get(
    "/{job_id}",
    response_model=BackgroundJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get background job detail",
    description=(
        "Requires a Bearer access token and returns durable job status for an "
        "owned background job. RQ status is reconciled where safe."
    ),
)
async def get_background_job(
    job_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    jobs_service: Annotated[
        BackgroundJobService,
        Depends(get_background_job_service),
    ],
) -> BackgroundJobResponse:
    job = await jobs_service.get_job(user_id=current_user.id, job_id=job_id)
    return BackgroundJobResponse(
        data=BackgroundJobData(job=BackgroundJobPublic.model_validate(job))
    )


@router.post(
    "/{job_id}/cancel",
    response_model=BackgroundJobCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel queued background job",
    description=(
        "Requires a Bearer access token and cancels an owned queued job. "
        "Started jobs are not forcefully terminated and return a conflict."
    ),
)
async def cancel_background_job(
    job_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    jobs_service: Annotated[
        BackgroundJobService,
        Depends(get_background_job_service),
    ],
) -> BackgroundJobCancelResponse:
    job = await jobs_service.cancel_job(user_id=current_user.id, job_id=job_id)
    return BackgroundJobCancelResponse(
        data=BackgroundJobCancelData(
            job=BackgroundJobPublic.model_validate(job),
            message="Background job cancelled.",
        )
    )


@router.post(
    "/{job_id}/retry",
    response_model=BackgroundJobRetryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry failed background job",
    description=(
        "Requires a Bearer access token and creates a new queued attempt for an "
        "owned failed background job when the retry limit allows it."
    ),
)
async def retry_background_job(
    job_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    jobs_service: Annotated[
        BackgroundJobService,
        Depends(get_background_job_service),
    ],
) -> BackgroundJobRetryResponse:
    result = await jobs_service.retry_job(user_id=current_user.id, job_id=job_id)
    return BackgroundJobRetryResponse(
        data=BackgroundJobRetryData(**result, retry_of_job_id=job_id)
    )
