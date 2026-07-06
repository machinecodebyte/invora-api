from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.infrastructure.models import ProductModel
from app.modules.sales.infrastructure.models import (
    SalesTransactionModel,
    SalesUploadBatchModel,
    SalesUploadRejectedRowModel,
)
from app.shared.utils import utc_now


class SalesUploadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_upload_batch(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> SalesUploadBatchModel:
        batch = SalesUploadBatchModel(user_id=user_id, **values)
        self.session.add(batch)
        await self.session.flush()
        return batch

    async def update_upload_batch_status(
        self,
        batch: SalesUploadBatchModel,
        values: dict[str, Any],
    ) -> SalesUploadBatchModel:
        for field, value in values.items():
            setattr(batch, field, value)
        batch.updated_at = utc_now()
        await self.session.flush()
        return batch

    async def create_sales_transactions_bulk(
        self,
        *,
        user_id: UUID,
        upload_batch_id: UUID,
        rows: list[dict[str, Any]],
    ) -> list[SalesTransactionModel]:
        transactions = [
            SalesTransactionModel(
                user_id=user_id,
                upload_batch_id=upload_batch_id,
                **row,
            )
            for row in rows
        ]
        self.session.add_all(transactions)
        await self.session.flush()
        return transactions

    async def create_rejected_rows_bulk(
        self,
        *,
        user_id: UUID,
        upload_batch_id: UUID,
        rows: list[dict[str, Any]],
    ) -> list[SalesUploadRejectedRowModel]:
        rejected_rows = [
            SalesUploadRejectedRowModel(
                user_id=user_id,
                upload_batch_id=upload_batch_id,
                **row,
            )
            for row in rows
        ]
        self.session.add_all(rejected_rows)
        await self.session.flush()
        return rejected_rows

    async def list_upload_batches_for_user(
        self,
        *,
        user_id: UUID,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        sort_order: str,
    ) -> tuple[list[SalesUploadBatchModel], int]:
        filters = [SalesUploadBatchModel.user_id == user_id]
        if status is not None:
            filters.append(SalesUploadBatchModel.status == status)
        if date_from is not None:
            filters.append(SalesUploadBatchModel.started_at >= date_from)
        if date_to is not None:
            filters.append(SalesUploadBatchModel.started_at <= date_to)

        total_result = await self.session.execute(
            select(func.count()).select_from(SalesUploadBatchModel).where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_expression = (
            asc(SalesUploadBatchModel.started_at)
            if sort_order == "asc"
            else desc(SalesUploadBatchModel.started_at)
        )
        result = await self.session.execute(
            select(SalesUploadBatchModel)
            .where(*filters)
            .order_by(sort_expression)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_upload_batch_for_user(
        self,
        *,
        user_id: UUID,
        upload_id: UUID,
    ) -> SalesUploadBatchModel | None:
        result = await self.session.execute(
            select(SalesUploadBatchModel).where(
                SalesUploadBatchModel.user_id == user_id,
                SalesUploadBatchModel.id == upload_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_rejected_rows_for_user(
        self,
        *,
        user_id: UUID,
        upload_batch_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[SalesUploadRejectedRowModel], int]:
        filters = [
            SalesUploadRejectedRowModel.user_id == user_id,
            SalesUploadRejectedRowModel.upload_batch_id == upload_batch_id,
        ]
        total_result = await self.session.execute(
            select(func.count()).select_from(SalesUploadRejectedRowModel).where(*filters)
        )
        total = int(total_result.scalar_one())
        result = await self.session.execute(
            select(SalesUploadRejectedRowModel)
            .where(*filters)
            .order_by(asc(SalesUploadRejectedRowModel.row_number))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_products_by_sku_for_user(
        self,
        *,
        user_id: UUID,
        normalized_skus: set[str],
    ) -> dict[str, ProductModel]:
        if not normalized_skus:
            return {}
        result = await self.session.execute(
            select(ProductModel).where(
                ProductModel.user_id == user_id,
                ProductModel.normalized_sku.in_(normalized_skus),
            )
        )
        return {product.normalized_sku: product for product in result.scalars().all()}

    async def file_hash_exists_for_user(self, *, user_id: UUID, file_hash: str) -> bool:
        result = await self.session.execute(
            select(SalesUploadBatchModel.id)
            .where(
                SalesUploadBatchModel.user_id == user_id,
                SalesUploadBatchModel.file_hash == file_hash,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
