from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Date as SqlDate
from sqlalchemy import asc, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.products.infrastructure.models import ProductModel
from app.modules.sales.infrastructure.models import (
    SalesTransactionModel,
    SalesUploadBatchModel,
    SalesUploadRejectedRowModel,
)
from app.shared.utils import utc_now

TRANSACTION_SORT_COLUMNS = {
    "sale_date": SalesTransactionModel.sale_date,
    "quantity": SalesTransactionModel.quantity,
    "unit_price": SalesTransactionModel.unit_price,
    "total_amount": SalesTransactionModel.total_amount,
    "source": SalesTransactionModel.source,
    "channel": SalesTransactionModel.channel,
    "created_at": SalesTransactionModel.created_at,
    "updated_at": SalesTransactionModel.updated_at,
    "product_name": ProductModel.normalized_name,
    "sku": ProductModel.normalized_sku,
}


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


class SalesTransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> ProductModel | None:
        result = await self.session.execute(
            select(ProductModel).where(
                ProductModel.id == product_id,
                ProductModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_transaction(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> SalesTransactionModel:
        transaction = SalesTransactionModel(user_id=user_id, **values)
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction, attribute_names=["product"])
        return transaction

    async def get_transaction_for_user(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        include_deleted: bool = False,
    ) -> SalesTransactionModel | None:
        filters = [
            SalesTransactionModel.id == transaction_id,
            SalesTransactionModel.user_id == user_id,
        ]
        if not include_deleted:
            filters.append(SalesTransactionModel.deleted_at.is_(None))

        result = await self.session.execute(
            select(SalesTransactionModel)
            .options(selectinload(SalesTransactionModel.product))
            .where(*filters)
        )
        return result.scalar_one_or_none()

    async def list_transactions_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        source: str | None,
        channel: str | None,
        date_from: date | None,
        date_to: date | None,
        include_deleted: bool,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[SalesTransactionModel], int]:
        filters = self._transaction_filters(
            user_id=user_id,
            product_id=product_id,
            category_id=category_id,
            source=source,
            channel=channel,
            date_from=date_from,
            date_to=date_to,
            include_deleted=include_deleted,
            search=search,
        )
        total_result = await self.session.execute(
            select(func.count())
            .select_from(SalesTransactionModel)
            .join(ProductModel, ProductModel.id == SalesTransactionModel.product_id)
            .where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = TRANSACTION_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(SalesTransactionModel)
            .join(ProductModel, ProductModel.id == SalesTransactionModel.product_id)
            .options(selectinload(SalesTransactionModel.product))
            .where(*filters)
            .order_by(sort_expression, desc(SalesTransactionModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update_transaction(
        self,
        transaction: SalesTransactionModel,
        values: dict[str, Any],
    ) -> SalesTransactionModel:
        for field, value in values.items():
            setattr(transaction, field, value)
        transaction.updated_at = utc_now()
        await self.session.flush()
        if "product_id" in values:
            await self.session.refresh(transaction, attribute_names=["product"])
        return transaction

    async def soft_delete_transaction(
        self,
        transaction: SalesTransactionModel,
        *,
        deleted_reason: str | None,
    ) -> SalesTransactionModel:
        now = utc_now()
        transaction.deleted_at = now
        transaction.deleted_reason = deleted_reason
        transaction.updated_at = now
        await self.session.flush()
        return transaction

    async def get_sales_summary_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        filters = self._aggregate_filters(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.session.execute(
            select(
                func.count(SalesTransactionModel.id),
                func.coalesce(func.sum(SalesTransactionModel.quantity), 0),
                func.coalesce(func.sum(SalesTransactionModel.total_amount), 0),
                func.count(func.distinct(SalesTransactionModel.product_id)),
                func.coalesce(func.avg(SalesTransactionModel.total_amount), 0),
            ).where(*filters)
        )
        (
            total_transactions,
            total_quantity_sold,
            total_sales_amount,
            unique_products_sold,
            average_transaction_amount,
        ) = result.one()
        return {
            "total_transactions": int(total_transactions),
            "total_quantity_sold": Decimal(str(total_quantity_sold)),
            "total_sales_amount": Decimal(str(total_sales_amount)),
            "unique_products_sold": int(unique_products_sold),
            "average_transaction_amount": Decimal(str(average_transaction_amount)),
            "date_from": date_from,
            "date_to": date_to,
        }

    async def get_sales_trends_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
        interval: str,
    ) -> list[dict[str, Any]]:
        filters = self._aggregate_filters(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        period_start = cast(
            func.date_trunc(interval, SalesTransactionModel.sale_date),
            SqlDate,
        ).label("period_start")
        result = await self.session.execute(
            select(
                period_start,
                func.coalesce(func.sum(SalesTransactionModel.quantity), 0),
                func.coalesce(func.sum(SalesTransactionModel.total_amount), 0),
                func.count(SalesTransactionModel.id),
            )
            .where(*filters)
            .group_by(period_start)
            .order_by(period_start)
        )
        return [
            {
                "period_start": row[0],
                "total_quantity": Decimal(str(row[1])),
                "total_amount": Decimal(str(row[2])),
                "transaction_count": int(row[3]),
            }
            for row in result.all()
        ]

    async def get_product_sales_summary_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, Any]]:
        filters = self._aggregate_filters(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await self.session.execute(
            select(
                ProductModel.id,
                ProductModel.name,
                ProductModel.sku,
                func.coalesce(func.sum(SalesTransactionModel.quantity), 0),
                func.coalesce(func.sum(SalesTransactionModel.total_amount), 0),
                func.count(SalesTransactionModel.id),
            )
            .join(ProductModel, ProductModel.id == SalesTransactionModel.product_id)
            .where(*filters)
            .group_by(ProductModel.id, ProductModel.name, ProductModel.sku)
            .order_by(desc(func.coalesce(func.sum(SalesTransactionModel.quantity), 0)))
        )
        return [
            {
                "product_id": row[0],
                "product_name": row[1],
                "sku": row[2],
                "total_quantity": Decimal(str(row[3])),
                "total_amount": Decimal(str(row[4])),
                "transaction_count": int(row[5]),
            }
            for row in result.all()
        ]

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    def _transaction_filters(
        self,
        *,
        user_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        source: str | None,
        channel: str | None,
        date_from: date | None,
        date_to: date | None,
        include_deleted: bool,
        search: str | None,
    ) -> list[Any]:
        filters = [SalesTransactionModel.user_id == user_id]
        if not include_deleted:
            filters.append(SalesTransactionModel.deleted_at.is_(None))
        if product_id is not None:
            filters.append(SalesTransactionModel.product_id == product_id)
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        if source is not None:
            filters.append(SalesTransactionModel.source == source)
        if channel is not None:
            filters.append(SalesTransactionModel.channel == channel)
        if date_from is not None:
            filters.append(SalesTransactionModel.sale_date >= date_from)
        if date_to is not None:
            filters.append(SalesTransactionModel.sale_date <= date_to)
        if search:
            search_value = search.strip()
            search_pattern = f"%{search_value}%"
            sku_pattern = f"%{search_value.upper()}%"
            filters.append(
                or_(
                    ProductModel.name.ilike(search_pattern),
                    ProductModel.normalized_sku.ilike(sku_pattern),
                    SalesTransactionModel.customer_name.ilike(search_pattern),
                    SalesTransactionModel.channel.ilike(search_pattern),
                    SalesTransactionModel.notes.ilike(search_pattern),
                )
            )
        return filters

    def _aggregate_filters(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> list[Any]:
        filters = [
            SalesTransactionModel.user_id == user_id,
            SalesTransactionModel.deleted_at.is_(None),
        ]
        if date_from is not None:
            filters.append(SalesTransactionModel.sale_date >= date_from)
        if date_to is not None:
            filters.append(SalesTransactionModel.sale_date <= date_to)
        return filters
