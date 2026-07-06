from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
