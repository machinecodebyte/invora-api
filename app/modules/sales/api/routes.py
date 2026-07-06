from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.sales.api.dependencies import (
    get_sales_transaction_service,
    get_sales_upload_service,
)
from app.modules.sales.api.schemas import (
    ProductSalesSummaryListData,
    ProductSalesSummaryListResponse,
    ProductSalesSummaryResponse,
    SalesRejectedRowListData,
    SalesRejectedRowListResponse,
    SalesRejectedRowPublic,
    SalesTransactionCreateRequest,
    SalesTransactionData,
    SalesTransactionDeleteRequest,
    SalesTransactionDeleteResponse,
    SalesTransactionListData,
    SalesTransactionListResponse,
    SalesTransactionPublic,
    SalesTransactionResponse,
    SalesTransactionSummaryData,
    SalesTransactionSummaryResponse,
    SalesTransactionUpdateRequest,
    SalesTrendListData,
    SalesTrendListResponse,
    SalesTrendPointResponse,
    SalesUploadBatchListResponse,
    SalesUploadBatchPublic,
    SalesUploadBatchResponse,
    SalesUploadData,
    SalesUploadListData,
    SalesUploadResponse,
    SalesUploadTemplateData,
    SalesUploadTemplateResponse,
)
from app.modules.sales.application.service import (
    SalesTransactionService,
    SalesUploadService,
)

router = APIRouter(prefix="/sales")


@router.post(
    "/uploads",
    response_model=SalesUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Sales Upload"],
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
    tags=["Sales Upload"],
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
    tags=["Sales Upload"],
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


@router.post(
    "/transactions",
    response_model=SalesTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Sales Transactions"],
    summary="Create manual sales transaction",
    description=(
        "Requires a Bearer access token and creates a manual historical sales "
        "transaction. This endpoint stores demand data only and does not update "
        "inventory stock."
    ),
)
async def create_sales_transaction(
    request: SalesTransactionCreateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
) -> SalesTransactionResponse:
    transaction = await sales_service.create_transaction(
        user_id=current_user.id,
        values=request.create_values(),
    )
    return SalesTransactionResponse(
        data=SalesTransactionData(
            transaction=SalesTransactionPublic.model_validate(transaction),
        )
    )


@router.get(
    "/transactions",
    response_model=SalesTransactionListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Transactions"],
    summary="List sales transactions",
    description=(
        "Requires a Bearer access token and returns the current user's "
        "historical sales transactions. Deleted transactions are excluded by "
        "default."
    ),
)
async def list_sales_transactions(
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    source: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="sale_date"),
    sort_order: str = Query(default="desc"),
) -> SalesTransactionListResponse:
    transactions, total = await sales_service.list_transactions(
        user_id=current_user.id,
        product_id=product_id,
        category_id=category_id,
        source=source,
        channel=channel,
        date_from=date_from,
        date_to=date_to,
        include_deleted=include_deleted,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return SalesTransactionListResponse(
        data=SalesTransactionListData(
            transactions=[
                SalesTransactionPublic.model_validate(transaction)
                for transaction in transactions
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/transactions/summary",
    response_model=SalesTransactionSummaryResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Transactions"],
    summary="Get sales transaction summary",
    description=(
        "Requires a Bearer access token and returns aggregate sales metrics for "
        "non-deleted transactions."
    ),
)
async def get_sales_transaction_summary(
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> SalesTransactionSummaryResponse:
    summary = await sales_service.get_summary(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
    )
    return SalesTransactionSummaryResponse(
        data=SalesTransactionSummaryData(**summary)
    )


@router.get(
    "/transactions/trends",
    response_model=SalesTrendListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Transactions"],
    summary="Get sales transaction trends",
    description=(
        "Requires a Bearer access token and returns date-wise quantity and "
        "amount aggregates for non-deleted transactions."
    ),
)
async def get_sales_transaction_trends(
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    interval: str = Query(default="day"),
) -> SalesTrendListResponse:
    trends = await sales_service.get_trends(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        interval=interval,
    )
    return SalesTrendListResponse(
        data=SalesTrendListData(
            trends=[SalesTrendPointResponse(**point) for point in trends]
        )
    )


@router.get(
    "/transactions/by-product",
    response_model=ProductSalesSummaryListResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Transactions"],
    summary="Get product-wise sales summary",
    description=(
        "Requires a Bearer access token and returns product-wise sales "
        "aggregates for non-deleted transactions."
    ),
)
async def get_sales_by_product_summary(
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> ProductSalesSummaryListResponse:
    products = await sales_service.get_by_product_summary(
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
    )
    return ProductSalesSummaryListResponse(
        data=ProductSalesSummaryListData(
            products=[ProductSalesSummaryResponse(**product) for product in products]
        )
    )


@router.get(
    "/uploads/{upload_id}",
    response_model=SalesUploadBatchResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Upload"],
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
    tags=["Sales Upload"],
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


@router.get(
    "/transactions/{transaction_id}",
    response_model=SalesTransactionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Transactions"],
    summary="Get sales transaction detail",
    description=(
        "Requires a Bearer access token and returns a non-deleted transaction "
        "only when it belongs to the current user."
    ),
)
async def get_sales_transaction(
    transaction_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
) -> SalesTransactionResponse:
    transaction = await sales_service.get_transaction(
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
    return SalesTransactionResponse(
        data=SalesTransactionData(
            transaction=SalesTransactionPublic.model_validate(transaction),
        )
    )


@router.patch(
    "/transactions/{transaction_id}",
    response_model=SalesTransactionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Transactions"],
    summary="Update sales transaction",
    description=(
        "Requires a Bearer access token and partially updates an owned "
        "non-deleted sales transaction. Protected metadata fields cannot be "
        "updated."
    ),
)
async def update_sales_transaction(
    transaction_id: UUID,
    request: SalesTransactionUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
) -> SalesTransactionResponse:
    transaction = await sales_service.update_transaction(
        user_id=current_user.id,
        transaction_id=transaction_id,
        values=request.update_values(),
    )
    return SalesTransactionResponse(
        data=SalesTransactionData(
            transaction=SalesTransactionPublic.model_validate(transaction),
        )
    )


@router.delete(
    "/transactions/{transaction_id}",
    response_model=SalesTransactionDeleteResponse,
    status_code=status.HTTP_200_OK,
    tags=["Sales Transactions"],
    summary="Delete sales transaction",
    description=(
        "Requires a Bearer access token and soft deletes an owned sales "
        "transaction. The row is retained and excluded from default sales "
        "queries and aggregates."
    ),
)
async def delete_sales_transaction(
    transaction_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    sales_service: Annotated[
        SalesTransactionService,
        Depends(get_sales_transaction_service),
    ],
    request: SalesTransactionDeleteRequest | None = Body(default=None),
) -> SalesTransactionDeleteResponse:
    transaction = await sales_service.delete_transaction(
        user_id=current_user.id,
        transaction_id=transaction_id,
        deleted_reason=request.deleted_reason if request is not None else None,
    )
    return SalesTransactionDeleteResponse(
        data=SalesTransactionData(
            transaction=SalesTransactionPublic.model_validate(transaction),
        )
    )
