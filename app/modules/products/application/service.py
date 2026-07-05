from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.products.domain.catalog import (
    ALLOWED_PRODUCT_UNITS,
    ensure_category_sort_field,
    ensure_product_sort_field,
    normalize_category_values,
    normalize_product_values,
    normalize_sort_order,
)
from app.modules.products.domain.exceptions import (
    DuplicateProductCategoryError,
    DuplicateProductSkuError,
    ProductCategoryHasActiveProductsError,
    ProductCategoryNotFoundError,
    ProductNotFoundError,
)


class ProductService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def create_product(self, *, user_id: UUID, values: dict[str, Any]) -> Any:
        normalized = normalize_product_values(values, partial=False)
        await self._ensure_category_can_be_used(
            user_id=user_id,
            category_id=normalized.get("category_id"),
        )
        await self._ensure_sku_available(
            user_id=user_id,
            normalized_sku=normalized["normalized_sku"],
        )

        try:
            product = await self.repository.create_product(
                user_id=user_id,
                values=normalized,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return product

    async def list_products(
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
    ) -> tuple[list[Any], int]:
        if category_id is not None:
            await self._get_category(user_id=user_id, category_id=category_id)

        return await self.repository.list_products_for_user(
            user_id=user_id,
            search=search,
            category_id=category_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
            sort_by=ensure_product_sort_field(sort_by),
            sort_order=normalize_sort_order(sort_order),
        )

    async def get_product(self, *, user_id: UUID, product_id: UUID) -> Any:
        return await self._get_product(user_id=user_id, product_id=product_id)

    async def update_product(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        product = await self._get_product(user_id=user_id, product_id=product_id)
        normalized = normalize_product_values(values, partial=True)

        if "category_id" in normalized:
            await self._ensure_category_can_be_used(
                user_id=user_id,
                category_id=normalized["category_id"],
            )
        if (
            "normalized_sku" in normalized
            and normalized["normalized_sku"] != product.normalized_sku
        ):
            await self._ensure_sku_available(
                user_id=user_id,
                normalized_sku=normalized["normalized_sku"],
                current_product_id=product.id,
            )

        try:
            product = await self.repository.update_product(product, normalized)
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return product

    async def archive_product(self, *, user_id: UUID, product_id: UUID) -> Any:
        product = await self._get_product(user_id=user_id, product_id=product_id)
        try:
            product = await self.repository.archive_product(product)
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise
        return product

    async def create_category(self, *, user_id: UUID, values: dict[str, Any]) -> Any:
        normalized = normalize_category_values(values, partial=False)
        await self._ensure_category_name_available(
            user_id=user_id,
            normalized_name=normalized["normalized_name"],
        )

        try:
            category = await self.repository.create_category(
                user_id=user_id,
                values=normalized,
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return category

    async def list_categories(
        self,
        *,
        user_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[Any], int]:
        return await self.repository.list_categories_for_user(
            user_id=user_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
            sort_by=ensure_category_sort_field(sort_by),
            sort_order=normalize_sort_order(sort_order),
        )

    async def update_category(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        category = await self._get_category(user_id=user_id, category_id=category_id)
        normalized = normalize_category_values(values, partial=True)

        if (
            "normalized_name" in normalized
            and normalized["normalized_name"] != category.normalized_name
        ):
            await self._ensure_category_name_available(
                user_id=user_id,
                normalized_name=normalized["normalized_name"],
                current_category_id=category.id,
            )
        if normalized.get("is_active") is False:
            await self._ensure_category_has_no_active_products(
                user_id=user_id,
                category_id=category.id,
            )

        try:
            category = await self.repository.update_category(category, normalized)
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return category

    async def archive_category(self, *, user_id: UUID, category_id: UUID) -> Any:
        category = await self._get_category(user_id=user_id, category_id=category_id)
        await self._ensure_category_has_no_active_products(
            user_id=user_id,
            category_id=category.id,
        )

        try:
            category = await self.repository.archive_category(category)
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return category

    async def list_units(self) -> tuple[str, ...]:
        return ALLOWED_PRODUCT_UNITS

    async def _get_product(self, *, user_id: UUID, product_id: UUID) -> Any:
        product = await self.repository.get_product_by_id_for_user(
            user_id=user_id,
            product_id=product_id,
        )
        if product is None:
            raise ProductNotFoundError()
        return product

    async def _get_category(self, *, user_id: UUID, category_id: UUID) -> Any:
        category = await self.repository.get_category_by_id_for_user(
            user_id=user_id,
            category_id=category_id,
        )
        if category is None:
            raise ProductCategoryNotFoundError()
        return category

    async def _ensure_category_can_be_used(
        self,
        *,
        user_id: UUID,
        category_id: UUID | None,
    ) -> None:
        if category_id is None:
            return
        category = await self._get_category(user_id=user_id, category_id=category_id)
        if not category.is_active:
            raise ProductCategoryNotFoundError()

    async def _ensure_sku_available(
        self,
        *,
        user_id: UUID,
        normalized_sku: str,
        current_product_id: UUID | None = None,
    ) -> None:
        existing_product = await self.repository.get_product_by_sku_for_user(
            user_id=user_id,
            normalized_sku=normalized_sku,
        )
        if existing_product is not None and existing_product.id != current_product_id:
            raise DuplicateProductSkuError()

    async def _ensure_category_name_available(
        self,
        *,
        user_id: UUID,
        normalized_name: str,
        current_category_id: UUID | None = None,
    ) -> None:
        existing_category = await self.repository.get_category_by_name_for_user(
            user_id=user_id,
            normalized_name=normalized_name,
        )
        if (
            existing_category is not None
            and existing_category.id != current_category_id
        ):
            raise DuplicateProductCategoryError()

    async def _ensure_category_has_no_active_products(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        active_count = await self.repository.count_active_products_by_category(
            user_id=user_id,
            category_id=category_id,
        )
        if active_count > 0:
            raise ProductCategoryHasActiveProductsError()
