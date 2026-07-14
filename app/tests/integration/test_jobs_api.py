from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.modules.jobs.domain.enums import JobEntityType, JobType
from app.modules.jobs.domain.exceptions import QueueUnavailableError
from app.shared.utils import utc_now

OWNER_PAYLOAD = {
    "email": "jobs-owner@example.com",
    "password": "StrongPass1!",
    "full_name": "Jobs Owner",
}
SECOND_OWNER_PAYLOAD = {
    "email": "jobs-second@example.com",
    "password": "StrongPass1!",
    "full_name": "Second Jobs Owner",
}


@dataclass(slots=True)
class FakeBackgroundJob:
    id: UUID
    rq_job_id: str
    user_id: UUID
    job_type: str
    entity_type: str | None
    entity_id: UUID | None
    queue_name: str
    status: str
    attempts: int
    max_retries: int
    timeout_seconds: int
    enqueued_at: object
    started_at: object | None
    completed_at: object | None
    failed_at: object | None
    cancelled_at: object | None
    error_code: str | None
    error_message: str | None
    result_summary: dict | None
    job_metadata: dict | None
    created_at: object
    updated_at: object


class FakeBackgroundJobRepository:
    def __init__(self, forecast_repository) -> None:
        self.forecast_repository = forecast_repository
        self.jobs_by_id: dict[UUID, FakeBackgroundJob] = {}

    async def create_background_job(self, *, values: dict) -> FakeBackgroundJob:
        now = utc_now()
        job = FakeBackgroundJob(
            id=values["id"],
            rq_job_id=values["rq_job_id"],
            user_id=values["user_id"],
            job_type=values["job_type"],
            entity_type=values.get("entity_type"),
            entity_id=values.get("entity_id"),
            queue_name=values["queue_name"],
            status=values["status"],
            attempts=values.get("attempts", 0),
            max_retries=values.get("max_retries", 3),
            timeout_seconds=values["timeout_seconds"],
            enqueued_at=values["enqueued_at"],
            started_at=None,
            completed_at=None,
            failed_at=None,
            cancelled_at=None,
            error_code=None,
            error_message=None,
            result_summary=None,
            job_metadata=values.get("job_metadata"),
            created_at=values.get("created_at", now),
            updated_at=values.get("updated_at", now),
        )
        self.jobs_by_id[job.id] = job
        return job

    async def get_job_for_user(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
    ) -> FakeBackgroundJob | None:
        job = self.jobs_by_id.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    async def get_job_by_id(self, *, job_id: UUID) -> FakeBackgroundJob | None:
        return self.jobs_by_id.get(job_id)

    async def get_active_job_for_entity(
        self,
        *,
        user_id: UUID,
        job_type: str,
        entity_type: str,
        entity_id: UUID,
    ) -> FakeBackgroundJob | None:
        for job in self.jobs_by_id.values():
            if (
                job.user_id == user_id
                and job.job_type == job_type
                and job.entity_type == entity_type
                and job.entity_id == entity_id
                and job.status in {"queued", "started", "retrying"}
            ):
                return job
        return None

    async def list_jobs_for_user(
        self,
        *,
        user_id: UUID,
        job_type: str | None,
        status: str | None,
        entity_id: UUID | None,
        queue_name: str | None,
        date_from,
        date_to,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[FakeBackgroundJob], int]:
        jobs = [job for job in self.jobs_by_id.values() if job.user_id == user_id]
        if job_type is not None:
            jobs = [job for job in jobs if job.job_type == job_type]
        if status is not None:
            jobs = [job for job in jobs if job.status == status]
        if entity_id is not None:
            jobs = [job for job in jobs if job.entity_id == entity_id]
        if queue_name is not None:
            jobs = [job for job in jobs if job.queue_name == queue_name]
        if date_from is not None:
            jobs = [job for job in jobs if job.created_at >= date_from]
        if date_to is not None:
            jobs = [job for job in jobs if job.created_at <= date_to]
        jobs.sort(key=lambda job: getattr(job, sort_by), reverse=sort_order == "desc")
        total = len(jobs)
        return jobs[offset : offset + limit], total

    async def mark_job_failed(
        self,
        job: FakeBackgroundJob,
        *,
        error_code: str,
        error_message: str,
        result_summary: dict | None = None,
    ) -> FakeBackgroundJob:
        job.status = "failed"
        job.failed_at = utc_now()
        job.error_code = error_code
        job.error_message = error_message
        job.result_summary = result_summary
        job.updated_at = utc_now()
        return job

    async def mark_job_cancelled(
        self,
        job: FakeBackgroundJob,
    ) -> FakeBackgroundJob:
        job.status = "cancelled"
        job.cancelled_at = utc_now()
        job.updated_at = utc_now()
        return job

    async def update_rq_job_id(
        self,
        job: FakeBackgroundJob,
        rq_job_id: str,
    ) -> FakeBackgroundJob:
        job.rq_job_id = rq_job_id
        return job

    async def get_forecast_run_for_user(self, *, user_id: UUID, run_id: UUID):
        return await self.forecast_repository.get_forecast_run_for_user(
            user_id=user_id,
            run_id=run_id,
        )

    async def count_user_active_products(self, *, user_id: UUID) -> int:
        return await self.forecast_repository.count_user_active_products(
            user_id=user_id,
        )

    async def count_user_sales_transactions(self, *, user_id: UUID) -> int:
        return await self.forecast_repository.count_user_sales_transactions(
            user_id=user_id,
        )

    async def update_forecast_run_status(self, run, values: dict):
        return await self.forecast_repository.update_forecast_run_status(run, values)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeForecastJobDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[str] = []
        self.cancelled: list[str] = []
        self.raise_unavailable = False

    def enqueue_forecast_processing(self, **kwargs) -> str:
        if self.raise_unavailable:
            raise QueueUnavailableError()
        self.enqueued.append(kwargs["rq_job_id"])
        return kwargs["rq_job_id"]

    def get_job_status(self, *, rq_job_id: str) -> str | None:
        return "queued"

    def cancel_job(self, *, rq_job_id: str) -> bool:
        self.cancelled.append(rq_job_id)
        return True

    def get_queue_health(self, *, queue_names: list[str]) -> dict:
        if self.raise_unavailable:
            raise QueueUnavailableError()
        return {
            "redis_available": True,
            "queues_available": True,
            "queues": [
                {
                    "name": queue_name,
                    "queued_job_count": 0,
                    "started_job_count": 0,
                    "failed_job_count": 0,
                }
                for queue_name in queue_names
            ],
            "active_worker_count": 1,
            "worker_names": ["invora-worker-test"],
        }


@pytest.fixture
def jobs_repository(forecast_repository) -> FakeBackgroundJobRepository:
    return FakeBackgroundJobRepository(forecast_repository)


@pytest.fixture
def jobs_dispatcher() -> FakeForecastJobDispatcher:
    return FakeForecastJobDispatcher()


@pytest.fixture
async def jobs_client(
    app,
    auth_repository,
    product_repository,
    sales_repository,
    forecast_repository,
    jobs_repository,
    jobs_dispatcher,
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.forecasting.api.dependencies import get_forecast_run_service
    from app.modules.forecasting.application.service import ForecastRunService
    from app.modules.jobs.api.dependencies import get_background_job_service
    from app.modules.jobs.application.services import BackgroundJobService
    from app.modules.products.api.dependencies import get_product_service
    from app.modules.products.application.service import ProductService
    from app.modules.sales.api.dependencies import get_sales_transaction_service
    from app.modules.sales.application.service import SalesTransactionService
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    async def override_product_service() -> ProductService:
        return ProductService(repository=product_repository)

    async def override_sales_transaction_service() -> SalesTransactionService:
        return SalesTransactionService(repository=sales_repository)

    async def override_forecast_run_service() -> ForecastRunService:
        return ForecastRunService(repository=forecast_repository)

    async def override_jobs_service() -> BackgroundJobService:
        return BackgroundJobService(
            repository=jobs_repository,
            dispatcher=jobs_dispatcher,
            settings=get_settings(),
        )

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    app.dependency_overrides[get_product_service] = override_product_service
    app.dependency_overrides[get_sales_transaction_service] = (
        override_sales_transaction_service
    )
    app.dependency_overrides[get_forecast_run_service] = override_forecast_run_service
    app.dependency_overrides[get_background_job_service] = override_jobs_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


async def _register(client, payload: dict = OWNER_PAYLOAD) -> str:
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()["data"]["tokens"]["access_token"]


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _create_forecast_ready_run(client, access_token: str) -> dict:
    product_response = await client.post(
        "/api/v1/products",
        headers=_auth_headers(access_token),
        json={
            "name": f"Job Product {uuid4().hex[:6]}",
            "sku": f"JOB-{uuid4().hex[:8]}",
            "unit": "pcs",
            "selling_price": "10.00",
        },
    )
    assert product_response.status_code == 201
    product = product_response.json()["data"]["product"]
    sales_response = await client.post(
        "/api/v1/sales/transactions",
        headers=_auth_headers(access_token),
        json={
            "product_id": product["id"],
            "sale_date": "2026-07-01",
            "quantity": "2.000",
            "unit_price": "10.00",
        },
    )
    assert sales_response.status_code == 201
    run_response = await client.post(
        "/api/v1/forecast-runs",
        headers=_auth_headers(access_token),
        json={"horizon_days": 7},
    )
    assert run_response.status_code == 201
    return run_response.json()["data"]["run"]


def _create_job_record(
    repository: FakeBackgroundJobRepository,
    *,
    user_id: UUID,
    run_id: UUID | None = None,
    status: str = "queued",
    attempts: int = 0,
    max_retries: int = 3,
) -> FakeBackgroundJob:
    now = utc_now()
    job_id = uuid4()
    job = FakeBackgroundJob(
        id=job_id,
        rq_job_id=f"forecast-processing:{job_id}",
        user_id=user_id,
        job_type=JobType.FORECAST_PROCESSING.value,
        entity_type=JobEntityType.FORECAST_RUN.value,
        entity_id=run_id or uuid4(),
        queue_name="invora-forecasting",
        status=status,
        attempts=attempts,
        max_retries=max_retries,
        timeout_seconds=1800,
        enqueued_at=now,
        started_at=None,
        completed_at=now if status == "finished" else None,
        failed_at=now if status == "failed" else None,
        cancelled_at=None,
        error_code="failed" if status == "failed" else None,
        error_message="Failed." if status == "failed" else None,
        result_summary=None,
        job_metadata=None,
        created_at=now,
        updated_at=now,
    )
    repository.jobs_by_id[job.id] = job
    return job


@pytest.mark.asyncio
async def test_enqueue_forecast_job_requires_auth(jobs_client) -> None:
    response = await jobs_client.post(f"/api/v1/jobs/forecast-runs/{uuid4()}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_access_token"


@pytest.mark.asyncio
async def test_enqueue_forecast_job_succeeds_and_is_idempotent(
    jobs_client,
    jobs_repository,
    jobs_dispatcher,
) -> None:
    access_token = await _register(jobs_client)
    run = await _create_forecast_ready_run(jobs_client, access_token)

    first = await jobs_client.post(
        f"/api/v1/jobs/forecast-runs/{run['id']}",
        headers=_auth_headers(access_token),
    )
    second = await jobs_client.post(
        f"/api/v1/jobs/forecast-runs/{run['id']}",
        headers=_auth_headers(access_token),
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["job_id"] == second.json()["data"]["job_id"]
    assert first.json()["data"]["queue_name"] == "invora-forecasting"
    assert len(jobs_repository.jobs_by_id) == 1
    assert len(jobs_dispatcher.enqueued) == 1


@pytest.mark.asyncio
async def test_enqueue_forecast_job_enforces_run_ownership(jobs_client) -> None:
    first_token = await _register(jobs_client)
    second_token = await _register(jobs_client, SECOND_OWNER_PAYLOAD)
    run = await _create_forecast_ready_run(jobs_client, first_token)

    response = await jobs_client.post(
        f"/api/v1/jobs/forecast-runs/{run['id']}",
        headers=_auth_headers(second_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "forecast_run_not_found"


@pytest.mark.asyncio
async def test_completed_or_cancelled_runs_cannot_be_enqueued(
    jobs_client,
    forecast_repository,
) -> None:
    access_token = await _register(jobs_client)
    completed = await _create_forecast_ready_run(jobs_client, access_token)
    cancelled = await _create_forecast_ready_run(jobs_client, access_token)
    forecast_repository.runs_by_id[UUID(completed["id"])].status = "completed"
    forecast_repository.runs_by_id[UUID(cancelled["id"])].status = "cancelled"

    completed_response = await jobs_client.post(
        f"/api/v1/jobs/forecast-runs/{completed['id']}",
        headers=_auth_headers(access_token),
    )
    cancelled_response = await jobs_client.post(
        f"/api/v1/jobs/forecast-runs/{cancelled['id']}",
        headers=_auth_headers(access_token),
    )

    assert completed_response.status_code == 409
    assert completed_response.json()["error"]["code"] == (
        "forecast_run_not_processable_for_job"
    )
    assert cancelled_response.status_code == 409


@pytest.mark.asyncio
async def test_job_list_filters_and_scopes_to_current_user(
    jobs_client,
    auth_repository,
    jobs_repository,
) -> None:
    first_token = await _register(jobs_client)
    second_token = await _register(jobs_client, SECOND_OWNER_PAYLOAD)
    first_user = auth_repository.users_by_email[OWNER_PAYLOAD["email"]]
    second_user = auth_repository.users_by_email[SECOND_OWNER_PAYLOAD["email"]]
    _create_job_record(jobs_repository, user_id=first_user.id, status="queued")
    _create_job_record(jobs_repository, user_id=first_user.id, status="failed")
    _create_job_record(jobs_repository, user_id=second_user.id, status="queued")

    response = await jobs_client.get(
        "/api/v1/jobs?status=queued&job_type=forecast_processing",
        headers=_auth_headers(first_token),
    )

    assert second_token
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["jobs"][0]["status"] == "queued"


@pytest.mark.asyncio
async def test_get_job_detail_is_user_scoped(
    jobs_client,
    auth_repository,
    jobs_repository,
) -> None:
    first_token = await _register(jobs_client)
    second_token = await _register(jobs_client, SECOND_OWNER_PAYLOAD)
    user = auth_repository.users_by_email[OWNER_PAYLOAD["email"]]
    job = _create_job_record(jobs_repository, user_id=user.id)

    own_response = await jobs_client.get(
        f"/api/v1/jobs/{job.id}",
        headers=_auth_headers(first_token),
    )
    other_response = await jobs_client.get(
        f"/api/v1/jobs/{job.id}",
        headers=_auth_headers(second_token),
    )

    assert own_response.status_code == 200
    assert own_response.json()["data"]["job"]["job_id"] == str(job.id)
    assert other_response.status_code == 404


@pytest.mark.asyncio
async def test_queued_job_can_be_cancelled(
    jobs_client,
    jobs_dispatcher,
    forecast_repository,
) -> None:
    access_token = await _register(jobs_client)
    run = await _create_forecast_ready_run(jobs_client, access_token)
    enqueue = await jobs_client.post(
        f"/api/v1/jobs/forecast-runs/{run['id']}",
        headers=_auth_headers(access_token),
    )
    job_id = enqueue.json()["data"]["job_id"]

    response = await jobs_client.post(
        f"/api/v1/jobs/{job_id}/cancel",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 200
    assert response.json()["data"]["job"]["status"] == "cancelled"
    assert jobs_dispatcher.cancelled
    assert forecast_repository.runs_by_id[UUID(run["id"])].status == "cancelled"


@pytest.mark.asyncio
async def test_finished_job_cannot_be_cancelled(
    jobs_client,
    auth_repository,
    jobs_repository,
) -> None:
    access_token = await _register(jobs_client)
    user = auth_repository.users_by_email[OWNER_PAYLOAD["email"]]
    job = _create_job_record(jobs_repository, user_id=user.id, status="finished")

    response = await jobs_client.post(
        f"/api/v1/jobs/{job.id}/cancel",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "job_not_cancellable"


@pytest.mark.asyncio
async def test_failed_job_can_be_retried_and_limit_is_enforced(
    jobs_client,
    auth_repository,
    jobs_repository,
    forecast_repository,
) -> None:
    access_token = await _register(jobs_client)
    run = await _create_forecast_ready_run(jobs_client, access_token)
    forecast_repository.runs_by_id[UUID(run["id"])].status = "failed"
    user = auth_repository.users_by_email[OWNER_PAYLOAD["email"]]
    failed_job = _create_job_record(
        jobs_repository,
        user_id=user.id,
        run_id=UUID(run["id"]),
        status="failed",
        attempts=1,
    )

    response = await jobs_client.post(
        f"/api/v1/jobs/{failed_job.id}/retry",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 202
    assert response.json()["data"]["retry_of_job_id"] == str(failed_job.id)
    assert response.json()["data"]["job_id"] != str(failed_job.id)
    assert len(jobs_repository.jobs_by_id) == 2

    limit_job = _create_job_record(
        jobs_repository,
        user_id=user.id,
        run_id=UUID(run["id"]),
        status="failed",
        attempts=3,
        max_retries=3,
    )
    limit_response = await jobs_client.post(
        f"/api/v1/jobs/{limit_job.id}/retry",
        headers=_auth_headers(access_token),
    )

    assert limit_response.status_code == 409
    assert limit_response.json()["error"]["code"] == "job_retry_limit_exceeded"


@pytest.mark.asyncio
async def test_redis_unavailable_returns_safe_503(
    jobs_client,
    jobs_dispatcher,
) -> None:
    access_token = await _register(jobs_client)
    run = await _create_forecast_ready_run(jobs_client, access_token)
    jobs_dispatcher.raise_unavailable = True

    response = await jobs_client.post(
        f"/api/v1/jobs/forecast-runs/{run['id']}",
        headers=_auth_headers(access_token),
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "queue_unavailable"


@pytest.mark.asyncio
async def test_jobs_health_and_options_return_expected_shape(jobs_client) -> None:
    access_token = await _register(jobs_client)

    health = await jobs_client.get(
        "/api/v1/jobs/health",
        headers=_auth_headers(access_token),
    )
    options = await jobs_client.get(
        "/api/v1/jobs/options",
        headers=_auth_headers(access_token),
    )

    assert health.status_code == 200
    assert health.json()["data"]["redis_available"] is True
    assert health.json()["data"]["queues"][0]["name"] == "invora-forecasting"
    assert options.status_code == 200
    assert options.json()["data"]["supported_job_types"] == ["forecast_processing"]
    assert "failed" in options.json()["data"]["supported_statuses"]
