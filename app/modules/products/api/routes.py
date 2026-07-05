from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.modules.auth.api.dependencies import get_current_user
from app.modules.products.api.dependencies import get_product_service
from app.modules.products.api.schemas import (
    MessageData,
    MessageResponse,
    ProductCategoryCreateRequest,
    ProductCategoryData,
    ProductCategoryListData,
    ProductCategoryListResponse,
    ProductCategoryPublic,
    ProductCategoryResponse,
    ProductCategoryUpdateRequest,
    ProductCreateRequest,
    ProductData,
    ProductListData,
    ProductListResponse,
    ProductPublic,
    ProductResponse,
    ProductUnitData,
    ProductUnitResponse,
    ProductUpdateRequest,
)
from app.modules.products.application.service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "/categories",
    response_model=ProductCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product category",
    description=(
        "Requires a Bearer access token and creates a category for the current user."
    ),
)
async def create_category(
    payload: ProductCategoryCreateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductCategoryResponse:
    category = await product_service.create_category(
        user_id=current_user.id,
        values=payload.create_values(),
    )
    return _category_response(category)


@router.get(
    "/categories",
    response_model=ProductCategoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List product categories",
    description=(
        "Requires a Bearer access token and returns only current user's categories."
    ),
)
async def list_categories(
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
) -> ProductCategoryListResponse:
    categories, total = await product_service.list_categories(
        user_id=current_user.id,
        is_active=is_active,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ProductCategoryListResponse(
        data=ProductCategoryListData(
            categories=[
                ProductCategoryPublic.model_validate(category)
                for category in categories
            ],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.patch(
    "/categories/{category_id}",
    response_model=ProductCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update product category",
    description="Requires a Bearer access token and updates an owned product category.",
)
async def update_category(
    category_id: UUID,
    payload: ProductCategoryUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductCategoryResponse:
    category = await product_service.update_category(
        user_id=current_user.id,
        category_id=category_id,
        values=payload.update_values(),
    )
    return _category_response(category)


@router.delete(
    "/categories/{category_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive product category",
    description=(
        "Requires a Bearer access token and soft archives an owned category. "
        "Categories with active products cannot be archived."
    ),
)
async def archive_category(
    category_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> MessageResponse:
    await product_service.archive_category(
        user_id=current_user.id,
        category_id=category_id,
    )
    return MessageResponse(data=MessageData(message="Product category archived."))


@router.get(
    "/units",
    response_model=ProductUnitResponse,
    status_code=status.HTTP_200_OK,
    summary="List product units",
    description="Requires a Bearer access token and returns allowed product units.",
)
async def list_units(
    _: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductUnitResponse:
    units = await product_service.list_units()
    return ProductUnitResponse(data=ProductUnitData(units=units))


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product",
    description=(
        "Requires a Bearer access token and creates a catalog product for the "
        "current user."
    ),
)
async def create_product(
    payload: ProductCreateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponse:
    product = await product_service.create_product(
        user_id=current_user.id,
        values=payload.create_values(),
    )
    return _product_response(product)


@router.get(
    "",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    summary="List products",
    description=(
        "Requires a Bearer access token and returns paginated products owned by "
        "the current user with optional search, filters, and safe sorting."
    ),
)
async def list_products(
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
    search: str | None = Query(default=None, max_length=255),
    category_id: UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
) -> ProductListResponse:
    products, total = await product_service.list_products(
        user_id=current_user.id,
        search=search,
        category_id=category_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return ProductListResponse(
        data=ProductListData(
            products=[ProductPublic.model_validate(product) for product in products],
            total=total,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product",
    description="Requires a Bearer access token and returns an owned product by id.",
)
async def get_product(
    product_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponse:
    product = await product_service.get_product(
        user_id=current_user.id,
        product_id=product_id,
    )
    return _product_response(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update product",
    description=(
        "Requires a Bearer access token and partially updates an owned product."
    ),
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductResponse:
    product = await product_service.update_product(
        user_id=current_user.id,
        product_id=product_id,
        values=payload.update_values(),
    )
    return _product_response(product)


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive product",
    description="Requires a Bearer access token and soft archives an owned product.",
)
async def archive_product(
    product_id: UUID,
    current_user: Annotated[object, Depends(get_current_user)],
    product_service: Annotated[ProductService, Depends(get_product_service)],
) -> MessageResponse:
    await product_service.archive_product(
        user_id=current_user.id,
        product_id=product_id,
    )
    return MessageResponse(data=MessageData(message="Product archived."))


def _product_response(product: object) -> ProductResponse:
    return ProductResponse(
        data=ProductData(product=ProductPublic.model_validate(product)),
    )


def _category_response(category: object) -> ProductCategoryResponse:
    return ProductCategoryResponse(
        data=ProductCategoryData(
            category=ProductCategoryPublic.model_validate(category),
        ),
    )
