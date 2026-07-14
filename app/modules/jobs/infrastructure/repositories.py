from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.forecasting.infrastructure.models import ForecastRunModel
from app.modules.jobs.domain.rules import ACTIVE_JOB_STATUSES
from app.modules.jobs.infrastructure.models import BackgroundJobModel
from app.modules.products.infrastructure.models import ProductModel
from app.modules.sales.infrastructure.models import SalesTransactionModel
from app.shared.utils import utc_now

JOB_SORT_COLUMNS = {
    "created_at": BackgroundJobModel.created_at,
    "updated_at": BackgroundJobModel.updated_at,
    "enqueued_at": BackgroundJobModel.enqueued_at,
    "started_at": BackgroundJobModel.started_at,
    "completed_at": BackgroundJobModel.completed_at,
    "failed_at": BackgroundJobModel.failed_at,
    "cancelled_at": BackgroundJobModel.cancelled_at,
    "status": BackgroundJobModel.status,
    "job_type": BackgroundJobModel.job_type,
    "queue_name": BackgroundJobModel.queue_name,
}


class BackgroundJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_background_job(
        self,
        *,
        values: dict[str, Any],
    ) -> BackgroundJobModel:
        job = BackgroundJobModel(**values)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job_for_user(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
    ) -> BackgroundJobModel | None:
        result = await self.session.execute(
            select(BackgroundJobModel).where(
                BackgroundJobModel.id == job_id,
                BackgroundJobModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_job_by_id(
        self,
        *,
        job_id: UUID,
    ) -> BackgroundJobModel | None:
        result = await self.session.execute(
            select(BackgroundJobModel).where(BackgroundJobModel.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_job_by_rq_id(
        self,
        *,
        rq_job_id: str,
    ) -> BackgroundJobModel | None:
        result = await self.session.execute(
            select(BackgroundJobModel).where(
                BackgroundJobModel.rq_job_id == rq_job_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_job_for_entity(
        self,
        *,
        user_id: UUID,
        job_type: str,
        entity_type: str,
        entity_id: UUID,
    ) -> BackgroundJobModel | None:
        result = await self.session.execute(
            select(BackgroundJobModel)
            .where(
                BackgroundJobModel.user_id == user_id,
                BackgroundJobModel.job_type == job_type,
                BackgroundJobModel.entity_type == entity_type,
                BackgroundJobModel.entity_id == entity_id,
                BackgroundJobModel.status.in_(ACTIVE_JOB_STATUSES),
            )
            .order_by(desc(BackgroundJobModel.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_jobs_for_user(
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
    ) -> tuple[list[BackgroundJobModel], int]:
        filters = [BackgroundJobModel.user_id == user_id]
        if job_type is not None:
            filters.append(BackgroundJobModel.job_type == job_type)
        if status is not None:
            filters.append(BackgroundJobModel.status == status)
        if entity_id is not None:
            filters.append(BackgroundJobModel.entity_id == entity_id)
        if queue_name is not None:
            filters.append(BackgroundJobModel.queue_name == queue_name)
        if date_from is not None:
            filters.append(BackgroundJobModel.created_at >= date_from)
        if date_to is not None:
            filters.append(BackgroundJobModel.created_at <= date_to)

        total_result = await self.session.execute(
            select(func.count()).select_from(BackgroundJobModel).where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = JOB_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(BackgroundJobModel)
            .where(*filters)
            .order_by(sort_expression, desc(BackgroundJobModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update_rq_job_id(
        self,
        job: BackgroundJobModel,
        rq_job_id: str,
    ) -> BackgroundJobModel:
        job.rq_job_id = rq_job_id
        job.updated_at = utc_now()
        await self.session.flush()
        return job

    async def update_job_status(
        self,
        job: BackgroundJobModel,
        *,
        status: str,
        values: dict[str, Any] | None = None,
    ) -> BackgroundJobModel:
        job.status = status
        for field, value in (values or {}).items():
            setattr(job, field, value)
        job.updated_at = utc_now()
        await self.session.flush()
        return job

    async def increment_attempts(self, job: BackgroundJobModel) -> BackgroundJobModel:
        job.attempts += 1
        job.updated_at = utc_now()
        await self.session.flush()
        return job

    async def mark_job_started(self, job: BackgroundJobModel) -> BackgroundJobModel:
        now = utc_now()
        job.status = "started"
        job.started_at = now
        job.error_code = None
        job.error_message = None
        job.attempts += 1
        job.updated_at = now
        await self.session.flush()
        return job

    async def mark_job_finished(
        self,
        job: BackgroundJobModel,
        *,
        result_summary: dict[str, Any] | None,
    ) -> BackgroundJobModel:
        now = utc_now()
        job.status = "finished"
        job.completed_at = now
        job.failed_at = None
        job.error_code = None
        job.error_message = None
        job.result_summary = result_summary
        job.updated_at = now
        await self.session.flush()
        return job

    async def mark_job_retrying(
        self,
        job: BackgroundJobModel,
        *,
        error_code: str,
        error_message: str,
    ) -> BackgroundJobModel:
        now = utc_now()
        job.status = "retrying"
        job.error_code = error_code
        job.error_message = error_message
        job.updated_at = now
        await self.session.flush()
        return job

    async def mark_job_failed(
        self,
        job: BackgroundJobModel,
        *,
        error_code: str,
        error_message: str,
        result_summary: dict[str, Any] | None = None,
    ) -> BackgroundJobModel:
        now = utc_now()
        job.status = "failed"
        job.failed_at = now
        job.error_code = error_code
        job.error_message = error_message
        job.result_summary = result_summary
        job.updated_at = now
        await self.session.flush()
        return job

    async def mark_job_cancelled(self, job: BackgroundJobModel) -> BackgroundJobModel:
        now = utc_now()
        job.status = "cancelled"
        job.cancelled_at = now
        job.updated_at = now
        await self.session.flush()
        return job

    async def count_jobs_by_status(
        self,
        *,
        user_id: UUID,
    ) -> dict[str, int]:
        result = await self.session.execute(
            select(BackgroundJobModel.status, func.count(BackgroundJobModel.id))
            .where(BackgroundJobModel.user_id == user_id)
            .group_by(BackgroundJobModel.status)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def get_forecast_run_for_user(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> ForecastRunModel | None:
        result = await self.session.execute(
            select(ForecastRunModel).where(
                ForecastRunModel.id == run_id,
                ForecastRunModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_user_active_products(self, *, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ProductModel)
            .where(
                ProductModel.user_id == user_id,
                ProductModel.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def count_user_sales_transactions(self, *, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(SalesTransactionModel)
            .where(
                SalesTransactionModel.user_id == user_id,
                SalesTransactionModel.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def update_forecast_run_status(
        self,
        run: ForecastRunModel,
        values: dict[str, Any],
    ) -> ForecastRunModel:
        for field, value in values.items():
            setattr(run, field, value)
        run.updated_at = utc_now()
        await self.session.flush()
        return run

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
