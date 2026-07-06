from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.sales.api.dependencies import get_sales_upload_service
from app.modules.sales.api.schemas import (
    SalesRejectedRowListData,
    SalesRejectedRowListResponse,
    SalesRejectedRowPublic,
    SalesUploadBatchListResponse,
    SalesUploadBatchPublic,
    SalesUploadBatchResponse,
    SalesUploadData,
    SalesUploadListData,
    SalesUploadResponse,
    SalesUploadTemplateData,
    SalesUploadTemplateResponse,
)
from app.modules.sales.application.service import SalesUploadService

router = APIRouter(prefix="/sales", tags=["Sales Upload"])


@router.post(
    "/uploads",
    response_model=SalesUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload sales CSV",
    description=(
        "Requires a Bearer access token and uploads historical sales demand "
        "data. Accepted rows are stored as sales transactions; invalid rows are "
        "stored as rejected rows. This endpoint does not update inventory stock."
    ),
)
async def upload_sales_csv(
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[SalesUploadService, Depends(get_sales_upload_service)],
    file: UploadFile = File(...),
) -> SalesUploadResponse:
    content = await file.read()
    upload = await sales_service.upload_sales_csv(
        user_id=current_user.id,
        filename=file.filename or "sales_upload.csv",
        content_type=file.content_type,
        content=content,
    )
    return SalesUploadResponse(data=SalesUploadData(upload=upload))


@router.get(
    "/uploads",
    response_model=SalesUploadBatchListResponse,
    status_code=status.HTTP_200_OK,
    summary="List sales uploads",
    description=(
        "Requires a Bearer access token and returns upload batches owned by "
        "the current user."
    ),
)
async def list_upload_batches(
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[SalesUploadService, Depends(get_sales_upload_service)],
    status_filter: str | None = Query(default=None, alias="status"),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_order: str = Query(default="desc"),
) -> SalesUploadBatchListResponse:
    uploads, total = await sales_service.list_upload_batches(
        user_id=current_user.id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        sort_order=sort_order,
    )
    return SalesUploadBatchListResponse(
        data=SalesUploadListData(
            uploads=[
                SalesUploadBatchPublic.model_validate(upload) for upload in uploads
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/uploads/template",
    response_model=SalesUploadTemplateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sales upload template",
    description=(
        "Requires a Bearer access token and returns the supported CSV columns "
        "and an example row."
    ),
)
async def get_upload_template(
    _: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[SalesUploadService, Depends(get_sales_upload_service)],
) -> SalesUploadTemplateResponse:
    return SalesUploadTemplateResponse(
        data=SalesUploadTemplateData(**await sales_service.get_upload_template())
    )


@router.get(
    "/uploads/{upload_id}",
    response_model=SalesUploadBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sales upload detail",
    description=(
        "Requires a Bearer access token and returns an owned upload batch "
        "summary."
    ),
)
async def get_upload_batch(
    upload_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[SalesUploadService, Depends(get_sales_upload_service)],
) -> SalesUploadBatchResponse:
    upload = await sales_service.get_upload_batch(
        user_id=current_user.id,
        upload_id=upload_id,
    )
    return SalesUploadBatchResponse(data=SalesUploadData(upload=upload))


@router.get(
    "/uploads/{upload_id}/rejected-rows",
    response_model=SalesRejectedRowListResponse,
    status_code=status.HTTP_200_OK,
    summary="List rejected sales upload rows",
    description=(
        "Requires a Bearer access token and returns rejected rows for an owned "
        "upload batch."
    ),
)
async def list_rejected_rows(
    upload_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[SalesUploadService, Depends(get_sales_upload_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> SalesRejectedRowListResponse:
    rejected_rows, total = await sales_service.list_rejected_rows(
        user_id=current_user.id,
        upload_id=upload_id,
        limit=limit,
        offset=offset,
    )
    return SalesRejectedRowListResponse(
        data=SalesRejectedRowListData(
            rejected_rows=[
                SalesRejectedRowPublic.model_validate(row) for row in rejected_rows
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    )
