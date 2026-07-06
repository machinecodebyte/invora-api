from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.sales.domain.exceptions import (
    DuplicateSalesUploadError,
    SalesTransactionAlreadyDeletedError,
    SalesTransactionNotFoundError,
    SalesTransactionProductNotFoundError,
    SalesUploadNotFoundError,
)
from app.modules.sales.domain.transactions import (
    ensure_transaction_sort_field,
    normalize_optional_text,
    normalize_sort_order,
    normalize_transaction_create_values,
    normalize_transaction_update_values,
    validate_date_range,
    validate_source,
    validate_trend_interval,
)
from app.modules.sales.domain.upload import (
    RejectedSalesRow,
    ValidSalesRow,
    calculate_upload_status,
    collect_normalized_skus,
    parse_sales_csv,
    upload_template,
    validate_sales_row,
    validate_upload_file,
)
from app.shared.utils import utc_now


class SalesUploadService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def upload_sales_csv(
        self,
        *,
        user_id: UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> Any:
        safe_filename, file_hash = validate_upload_file(
            filename=filename,
            content_type=content_type,
            content=content,
        )
        if await self.repository.file_hash_exists_for_user(
            user_id=user_id,
            file_hash=file_hash,
        ):
            raise DuplicateSalesUploadError()

        parsed_rows = parse_sales_csv(content)
        products_by_sku = await self.repository.get_products_by_sku_for_user(
            user_id=user_id,
            normalized_skus=collect_normalized_skus(parsed_rows),
        )
        known_skus = set(products_by_sku)

        accepted: list[ValidSalesRow] = []
        rejected: list[RejectedSalesRow] = []
        for row in parsed_rows:
            result = validate_sales_row(row, known_skus=known_skus)
            if isinstance(result, ValidSalesRow):
                accepted.append(result)
            else:
                rejected.append(result)

        now = utc_now()
        try:
            batch = await self.repository.create_upload_batch(
                user_id=user_id,
                values={
                    "original_filename": safe_filename,
                    "file_hash": file_hash,
                    "status": "processing",
                    "total_rows": len(parsed_rows),
                    "accepted_rows": 0,
                    "rejected_rows": 0,
                    "started_at": now,
                    "completed_at": None,
                    "failure_reason": None,
                },
            )
            if accepted:
                await self.repository.create_sales_transactions_bulk(
                    user_id=user_id,
                    upload_batch_id=batch.id,
                    rows=[
                        _transaction_values(row, products_by_sku[row.product_sku].id)
                        for row in accepted
                    ],
                )
            if rejected:
                await self.repository.create_rejected_rows_bulk(
                    user_id=user_id,
                    upload_batch_id=batch.id,
                    rows=[_rejected_row_values(row) for row in rejected],
                )

            status = calculate_upload_status(
                accepted_rows=len(accepted),
                rejected_rows=len(rejected),
            )
            batch = await self.repository.update_upload_batch_status(
                batch,
                {
                    "status": status,
                    "total_rows": len(parsed_rows),
                    "accepted_rows": len(accepted),
                    "rejected_rows": len(rejected),
                    "completed_at": utc_now(),
                    "failure_reason": (
                        "No valid sales rows were accepted."
                        if len(accepted) == 0
                        else None
                    ),
                },
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return batch

    async def list_upload_batches(
        self,
        *,
        user_id: UUID,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        sort_order: str,
    ) -> tuple[list[Any], int]:
        return await self.repository.list_upload_batches_for_user(
            user_id=user_id,
            status=_normalize_status_filter(status),
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            sort_order=_normalize_sort_order(sort_order),
        )

    async def get_upload_batch(self, *, user_id: UUID, upload_id: UUID) -> Any:
        batch = await self.repository.get_upload_batch_for_user(
            user_id=user_id,
            upload_id=upload_id,
        )
        if batch is None:
            raise SalesUploadNotFoundError()
        return batch

    async def list_rejected_rows(
        self,
        *,
        user_id: UUID,
        upload_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        await self.get_upload_batch(user_id=user_id, upload_id=upload_id)
        return await self.repository.list_rejected_rows_for_user(
            user_id=user_id,
            upload_batch_id=upload_id,
            limit=limit,
            offset=offset,
        )

    async def get_upload_template(self) -> dict[str, Any]:
        return upload_template()


def _transaction_values(row: ValidSalesRow, product_id: UUID) -> dict[str, Any]:
    return {
        "product_id": product_id,
        "sale_date": row.sale_date,
        "quantity": row.quantity,
        "unit_price": row.unit_price,
        "total_amount": row.total_amount,
        "customer_name": row.customer_name,
        "channel": row.channel,
        "notes": row.notes,
        "source": "csv_upload",
    }


def _rejected_row_values(row: RejectedSalesRow) -> dict[str, Any]:
    return {
        "row_number": row.row_number,
        "raw_data": row.raw_data,
        "error_code": row.error_code,
        "error_message": row.error_message,
    }


def _normalize_sort_order(sort_order: str) -> str:
    normalized = sort_order.strip().lower()
    if normalized not in {"asc", "desc"}:
        return "desc"
    return normalized


def _normalize_status_filter(status: str | None) -> str | None:
    if status is None:
        return None
    return status.strip().lower() or None


class SalesTransactionService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def create_transaction(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        normalized = normalize_transaction_create_values(values)
        await self._get_product(
            user_id=user_id,
            product_id=normalized["product_id"],
        )

        try:
            transaction = await self.repository.create_transaction(
                user_id=user_id,
                values=normalized,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        return transaction

    async def list_transactions(
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
    ) -> tuple[list[Any], int]:
        validate_date_range(date_from, date_to)
        if product_id is not None:
            await self._get_product(user_id=user_id, product_id=product_id)

        return await self.repository.list_transactions_for_user(
            user_id=user_id,
            product_id=product_id,
            category_id=category_id,
            source=validate_source(source),
            channel=normalize_optional_text(channel, 64),
            date_from=date_from,
            date_to=date_to,
            include_deleted=include_deleted,
            search=normalize_optional_text(search, 255),
            limit=limit,
            offset=offset,
            sort_by=ensure_transaction_sort_field(sort_by),
            sort_order=normalize_sort_order(sort_order),
        )

    async def get_transaction(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
    ) -> Any:
        transaction = await self.repository.get_transaction_for_user(
            user_id=user_id,
            transaction_id=transaction_id,
        )
        if transaction is None:
            raise SalesTransactionNotFoundError()
        return transaction

    async def update_transaction(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        transaction = await self.repository.get_transaction_for_user(
            user_id=user_id,
            transaction_id=transaction_id,
            include_deleted=True,
        )
        if transaction is None:
            raise SalesTransactionNotFoundError()
        if transaction.deleted_at is not None:
            raise SalesTransactionAlreadyDeletedError()

        if "product_id" in values and values["product_id"] != transaction.product_id:
            await self._get_product(user_id=user_id, product_id=values["product_id"])

        normalized = normalize_transaction_update_values(
            values,
            current_quantity=transaction.quantity,
            current_unit_price=transaction.unit_price,
            current_total_amount=transaction.total_amount,
        )
        try:
            transaction = await self.repository.update_transaction(
                transaction,
                normalized,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        return transaction

    async def delete_transaction(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        deleted_reason: str | None,
    ) -> Any:
        transaction = await self.repository.get_transaction_for_user(
            user_id=user_id,
            transaction_id=transaction_id,
            include_deleted=True,
        )
        if transaction is None:
            raise SalesTransactionNotFoundError()
        if transaction.deleted_at is not None:
            raise SalesTransactionAlreadyDeletedError()

        try:
            transaction = await self.repository.soft_delete_transaction(
                transaction,
                deleted_reason=normalize_optional_text(deleted_reason, 1000),
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        return transaction

    async def get_summary(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, Any]:
        validate_date_range(date_from, date_to)
        return await self.repository.get_sales_summary_for_user(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def get_trends(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
        interval: str,
    ) -> list[dict[str, Any]]:
        validate_date_range(date_from, date_to)
        return await self.repository.get_sales_trends_for_user(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
            interval=validate_trend_interval(interval),
        )

    async def get_by_product_summary(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, Any]]:
        validate_date_range(date_from, date_to)
        return await self.repository.get_product_sales_summary_for_user(
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

    async def _get_product(self, *, user_id: UUID, product_id: UUID) -> Any:
        product = await self.repository.get_product_for_user(
            user_id=user_id,
            product_id=product_id,
        )
        if product is None:
            raise SalesTransactionProductNotFoundError()
        return product
