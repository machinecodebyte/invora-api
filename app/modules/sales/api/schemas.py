from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.sales.domain.transactions import (
    ALLOWED_TRANSACTION_SOURCES,
    ALLOWED_TRANSACTION_UPDATE_FIELDS,
    ensure_no_unsupported_transaction_fields,
)


class SalesUploadBatchPublic(BaseModel):
    id: UUID
    original_filename: str
    status: Literal["processing", "completed", "completed_with_errors", "failed"]
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    started_at: datetime
    completed_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesUploadData(BaseModel):
    upload: SalesUploadBatchPublic


class SalesUploadListData(BaseModel):
    uploads: list[SalesUploadBatchPublic]
    total: int
    limit: int
    offset: int


class SalesUploadResponse(BaseModel):
    success: Literal[True] = True
    data: SalesUploadData


class SalesUploadBatchResponse(BaseModel):
    success: Literal[True] = True
    data: SalesUploadData


class SalesUploadBatchListResponse(BaseModel):
    success: Literal[True] = True
    data: SalesUploadListData


class SalesRejectedRowPublic(BaseModel):
    id: UUID
    upload_batch_id: UUID
    row_number: int
    raw_data: dict[str, Any]
    error_code: str
    error_message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesRejectedRowListData(BaseModel):
    rejected_rows: list[SalesRejectedRowPublic]
    total: int
    limit: int
    offset: int


class SalesRejectedRowListResponse(BaseModel):
    success: Literal[True] = True
    data: SalesRejectedRowListData


class SalesUploadTemplateData(BaseModel):
    required_columns: list[str]
    optional_columns: list[str]
    example_rows: list[dict[str, str]]
    notes: str


class SalesUploadTemplateResponse(BaseModel):
    success: Literal[True] = True
    data: SalesUploadTemplateData


class SalesTransactionCreateRequest(BaseModel):
    product_id: UUID
    sale_date: date
    quantity: Decimal
    unit_price: Decimal | None = None
    total_amount: Decimal | None = None
    customer_name: str | None = Field(default=None, max_length=255)
    channel: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="allow")

    def create_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_unsupported_transaction_fields(
            extra_fields=extra_fields,
            allowed_fields=ALLOWED_TRANSACTION_UPDATE_FIELDS,
        )
        return {
            "product_id": self.product_id,
            "sale_date": self.sale_date,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_amount": self.total_amount,
            "customer_name": self.customer_name,
            "channel": self.channel,
            "notes": self.notes,
        }


class SalesTransactionUpdateRequest(BaseModel):
    sale_date: date | None = None
    product_id: UUID | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_amount: Decimal | None = None
    customer_name: str | None = Field(default=None, max_length=255)
    channel: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(extra="allow")

    def update_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_unsupported_transaction_fields(
            extra_fields=extra_fields,
            allowed_fields=ALLOWED_TRANSACTION_UPDATE_FIELDS,
        )
        return {
            field: getattr(self, field)
            for field in ALLOWED_TRANSACTION_UPDATE_FIELDS
            if field in self.model_fields_set
        }


class SalesTransactionDeleteRequest(BaseModel):
    deleted_reason: str | None = Field(default=None, max_length=1000)


class SalesTransactionProductPublic(BaseModel):
    id: UUID
    name: str
    sku: str
    category_id: UUID | None
    unit: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class SalesTransactionPublic(BaseModel):
    id: UUID
    product_id: UUID
    product: SalesTransactionProductPublic
    upload_batch_id: UUID | None
    sale_date: date
    quantity: Decimal
    unit_price: Decimal | None
    total_amount: Decimal | None
    customer_name: str | None
    channel: str | None
    notes: str | None
    source: Literal["csv_upload", "manual", "api"]
    deleted_at: datetime | None
    deleted_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SalesTransactionData(BaseModel):
    transaction: SalesTransactionPublic


class SalesTransactionListData(BaseModel):
    transactions: list[SalesTransactionPublic]
    total: int
    limit: int
    offset: int


class SalesTransactionResponse(BaseModel):
    success: Literal[True] = True
    data: SalesTransactionData


class SalesTransactionListResponse(BaseModel):
    success: Literal[True] = True
    data: SalesTransactionListData


class SalesTransactionDeleteResponse(BaseModel):
    success: Literal[True] = True
    data: SalesTransactionData


class SalesTransactionSummaryData(BaseModel):
    total_transactions: int
    total_quantity_sold: Decimal
    total_sales_amount: Decimal
    unique_products_sold: int
    average_transaction_amount: Decimal
    date_from: date | None
    date_to: date | None


class SalesTransactionSummaryResponse(BaseModel):
    success: Literal[True] = True
    data: SalesTransactionSummaryData


class SalesTrendPointResponse(BaseModel):
    period_start: date
    total_quantity: Decimal
    total_amount: Decimal
    transaction_count: int


class SalesTrendListData(BaseModel):
    trends: list[SalesTrendPointResponse]


class SalesTrendListResponse(BaseModel):
    success: Literal[True] = True
    data: SalesTrendListData


class ProductSalesSummaryResponse(BaseModel):
    product_id: UUID
    product_name: str
    sku: str
    total_quantity: Decimal
    total_amount: Decimal
    transaction_count: int


class ProductSalesSummaryListData(BaseModel):
    products: list[ProductSalesSummaryResponse]


class ProductSalesSummaryListResponse(BaseModel):
    success: Literal[True] = True
    data: ProductSalesSummaryListData


def allowed_sales_transaction_sources() -> tuple[str, ...]:
    return ALLOWED_TRANSACTION_SOURCES
