from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.inventory.api.dependencies import get_inventory_service
from app.modules.inventory.api.schemas import (
    InventoryItemCreateRequest,
    InventoryItemData,
    InventoryItemListData,
    InventoryItemListResponse,
    InventoryItemResponse,
    InventoryItemUpdateRequest,
    InventorySummaryData,
    InventorySummaryResponse,
    LowStockItemListData,
    LowStockItemResponse,
    StockMovementCreateRequest,
    StockMovementData,
    StockMovementListData,
    StockMovementListResponse,
    StockMovementPublic,
    StockMovementResponse,
    inventory_item_public,
    low_stock_item_public,
)
from app.modules.inventory.application.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post(
    "/items",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create inventory item",
    description=(
        "Requires a Bearer access token, validates product ownership, creates "
        "one inventory balance per product, and records opening stock as a "
        "ledger movement when opening stock is greater than zero."
    ),
)
async def create_inventory_item(
    payload: InventoryItemCreateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponse:
    item = await inventory_service.create_inventory_item(
        user_id=current_user.id,
        product_id=payload.product_id,
        values=payload.create_values(),
    )
    return _item_response(item)


@router.get(
    "/items",
    response_model=InventoryItemListResponse,
    status_code=status.HTTP_200_OK,
    summary="List inventory items",
    description=(
        "Requires a Bearer access token and returns paginated inventory balances "
        "owned by the current user with optional filters and safe sorting."
    ),
)
async def list_inventory_items(
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
    search: str | None = Query(default=None, max_length=255),
    product_id: UUID | None = Query(default=None),
    category_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    stock_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc"),
) -> InventoryItemListResponse:
    items, total = await inventory_service.list_inventory_items(
        user_id=current_user.id,
        search=search,
        product_id=product_id,
        category_id=category_id,
        is_active=is_active,
        stock_status=stock_status,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return InventoryItemListResponse(
        data=InventoryItemListData(
            items=[inventory_item_public(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/items/{product_id}",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Get inventory item",
    description=(
        "Requires a Bearer access token and returns the inventory balance for "
        "an owned product."
    ),
)
async def get_inventory_item(
    product_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponse:
    item = await inventory_service.get_inventory_item(
        user_id=current_user.id,
        product_id=product_id,
    )
    return _item_response(item)


@router.patch(
    "/items/{product_id}",
    response_model=InventoryItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Update inventory thresholds",
    description=(
        "Requires a Bearer access token and updates thresholds or active status "
        "only. Stock quantities must be changed through movement ledger APIs."
    ),
)
async def update_inventory_thresholds(
    product_id: UUID,
    payload: InventoryItemUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventoryItemResponse:
    item = await inventory_service.update_inventory_thresholds(
        user_id=current_user.id,
        product_id=product_id,
        values=payload.update_values(),
    )
    return _item_response(item)


@router.post(
    "/movements",
    response_model=StockMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create stock movement",
    description=(
        "Requires a Bearer access token and changes stock by recording an "
        "immutable movement row in the inventory ledger."
    ),
)
async def create_stock_movement(
    payload: StockMovementCreateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> StockMovementResponse:
    movement = await inventory_service.create_stock_movement(
        user_id=current_user.id,
        product_id=payload.product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reason=payload.reason,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        occurred_at=payload.occurred_at,
    )
    return StockMovementResponse(
        data=StockMovementData(
            movement=StockMovementPublic.model_validate(movement),
        )
    )


@router.get(
    "/movements",
    response_model=StockMovementListResponse,
    status_code=status.HTTP_200_OK,
    summary="List stock movements",
    description=(
        "Requires a Bearer access token and returns movement ledger rows owned "
        "by the current user."
    ),
)
async def list_stock_movements(
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
    product_id: UUID | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="occurred_at"),
    sort_order: str = Query(default="desc"),
) -> StockMovementListResponse:
    movements, total = await inventory_service.list_stock_movements(
        user_id=current_user.id,
        product_id=product_id,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return StockMovementListResponse(
        data=StockMovementListData(
            movements=[
                StockMovementPublic.model_validate(movement)
                for movement in movements
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/low-stock",
    response_model=LowStockItemResponse,
    status_code=status.HTTP_200_OK,
    summary="List low-stock inventory",
    description=(
        "Requires a Bearer access token and returns active inventory items where "
        "current stock is less than or equal to minimum stock."
    ),
)
async def list_low_stock_items(
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> LowStockItemResponse:
    items, total = await inventory_service.list_low_stock_items(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return LowStockItemResponse(
        data=LowStockItemListData(
            items=[low_stock_item_public(item) for item in items],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/summary",
    response_model=InventorySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get inventory summary",
    description=(
        "Requires a Bearer access token and returns inventory counts, low-stock "
        "counts, total quantity, and recent movement count."
    ),
)
async def get_inventory_summary(
    current_user: Annotated[object, Depends(get_current_user)],
    inventory_service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> InventorySummaryResponse:
    summary = await inventory_service.get_inventory_summary(user_id=current_user.id)
    return InventorySummaryResponse(data=InventorySummaryData(**summary))


def _item_response(item: object) -> InventoryItemResponse:
    return InventoryItemResponse(
        data=InventoryItemData(item=inventory_item_public(item)),
    )
