from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.domain.exceptions import (
    DuplicateProductCategoryError,
    DuplicateProductSkuError,
)
from app.modules.products.infrastructure.models import (
    ProductCategoryModel,
    ProductModel,
)
from app.shared.utils import utc_now

PRODUCT_SORT_COLUMNS = {
    "name": ProductModel.normalized_name,
    "sku": ProductModel.normalized_sku,
    "selling_price": ProductModel.selling_price,
    "cost_price": ProductModel.cost_price,
    "created_at": ProductModel.created_at,
    "updated_at": ProductModel.updated_at,
    "is_active": ProductModel.is_active,
}
CATEGORY_SORT_COLUMNS = {
    "name": ProductCategoryModel.normalized_name,
    "created_at": ProductCategoryModel.created_at,
    "updated_at": ProductCategoryModel.updated_at,
    "is_active": ProductCategoryModel.is_active,
}


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_product(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> ProductModel:
        product = ProductModel(user_id=user_id, **values)
        self.session.add(product)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateProductSkuError() from exc
        return product

    async def get_product_by_id_for_user(
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

    async def get_product_by_sku_for_user(
        self,
        *,
        user_id: UUID,
        normalized_sku: str,
    ) -> ProductModel | None:
        result = await self.session.execute(
            select(ProductModel).where(
                ProductModel.user_id == user_id,
                ProductModel.normalized_sku == normalized_sku,
            )
        )
        return result.scalar_one_or_none()

    async def list_products_for_user(
        self,
        *,
        user_id: UUID,
        search: str | None,
        category_id: UUID | None,
        is_active: bool | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[ProductModel], int]:
        filters = [ProductModel.user_id == user_id]
        if search:
            search_pattern = f"%{search.strip()}%"
            sku_pattern = f"%{search.strip().upper()}%"
            filters.append(
                or_(
                    ProductModel.name.ilike(search_pattern),
                    ProductModel.normalized_sku.ilike(sku_pattern),
                )
            )
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        if is_active is not None:
            filters.append(ProductModel.is_active == is_active)

        total_result = await self.session.execute(
            select(func.count()).select_from(ProductModel).where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = PRODUCT_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(ProductModel)
            .where(*filters)
            .order_by(sort_expression, desc(ProductModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update_product(
        self,
        product: ProductModel,
        values: dict[str, Any],
    ) -> ProductModel:
        for field, value in values.items():
            setattr(product, field, value)
        product.updated_at = utc_now()
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateProductSkuError() from exc
        return product

    async def archive_product(self, product: ProductModel) -> ProductModel:
        product.is_active = False
        product.updated_at = utc_now()
        await self.session.flush()
        return product

    async def create_category(
        self,
        *,
        user_id: UUID,
        values: dict[str, Any],
    ) -> ProductCategoryModel:
        category = ProductCategoryModel(user_id=user_id, **values)
        self.session.add(category)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateProductCategoryError() from exc
        return category

    async def get_category_by_id_for_user(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> ProductCategoryModel | None:
        result = await self.session.execute(
            select(ProductCategoryModel).where(
                ProductCategoryModel.id == category_id,
                ProductCategoryModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_category_by_name_for_user(
        self,
        *,
        user_id: UUID,
        normalized_name: str,
    ) -> ProductCategoryModel | None:
        result = await self.session.execute(
            select(ProductCategoryModel).where(
                ProductCategoryModel.user_id == user_id,
                ProductCategoryModel.normalized_name == normalized_name,
            )
        )
        return result.scalar_one_or_none()

    async def list_categories_for_user(
        self,
        *,
        user_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[ProductCategoryModel], int]:
        filters = [ProductCategoryModel.user_id == user_id]
        if is_active is not None:
            filters.append(ProductCategoryModel.is_active == is_active)

        total_result = await self.session.execute(
            select(func.count()).select_from(ProductCategoryModel).where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = CATEGORY_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(ProductCategoryModel)
            .where(*filters)
            .order_by(sort_expression, desc(ProductCategoryModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update_category(
        self,
        category: ProductCategoryModel,
        values: dict[str, Any],
    ) -> ProductCategoryModel:
        for field, value in values.items():
            setattr(category, field, value)
        category.updated_at = utc_now()
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise DuplicateProductCategoryError() from exc
        return category

    async def archive_category(
        self,
        category: ProductCategoryModel,
    ) -> ProductCategoryModel:
        category.is_active = False
        category.updated_at = utc_now()
        await self.session.flush()
        return category

    async def count_active_products_by_category(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(ProductModel)
            .where(
                ProductModel.user_id == user_id,
                ProductModel.category_id == category_id,
                ProductModel.is_active.is_(True),
            )
        )
        return int(result.scalar_one())

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
