from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.sales.domain.exceptions import (
    DuplicateSalesUploadError,
    SalesUploadNotFoundError,
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
