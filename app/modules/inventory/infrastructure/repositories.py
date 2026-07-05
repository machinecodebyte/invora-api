from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.inventory.domain.exceptions import InventoryItemAlreadyExistsError
from app.modules.inventory.infrastructure.models import (
    InventoryItemModel,
    InventoryStockMovementModel,
)
from app.modules.products.infrastructure.models import ProductModel
from app.shared.utils import utc_now

ITEM_SORT_COLUMNS = {
    "product_name": ProductModel.normalized_name,
    "sku": ProductModel.normalized_sku,
    "current_stock": InventoryItemModel.current_stock,
    "minimum_stock": InventoryItemModel.minimum_stock,
    "safety_stock": InventoryItemModel.safety_stock,
    "created_at": InventoryItemModel.created_at,
    "updated_at": InventoryItemModel.updated_at,
    "is_active": InventoryItemModel.is_active,
}
MOVEMENT_SORT_COLUMNS = {
    "occurred_at": InventoryStockMovementModel.occurred_at,
    "created_at": InventoryStockMovementModel.created_at,
}


class InventoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_product_for_user(
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

    async def create_inventory_item(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        values: dict[str, Any],
    ) -> InventoryItemModel:
        item = InventoryItemModel(user_id=user_id, product_id=product_id, **values)
        self.session.add(item)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise InventoryItemAlreadyExistsError() from exc
        await self.session.refresh(item, attribute_names=["product"])
        return item

    async def get_inventory_item_by_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        for_update: bool = False,
    ) -> InventoryItemModel | None:
        statement = (
            select(InventoryItemModel)
            .options(selectinload(InventoryItemModel.product))
            .where(
                InventoryItemModel.user_id == user_id,
                InventoryItemModel.product_id == product_id,
            )
        )
        if for_update:
            statement = statement.with_for_update()

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_inventory_items_for_user(
        self,
        *,
        user_id: UUID,
        search: str | None,
        product_id: UUID | None,
        category_id: UUID | None,
        is_active: bool | None,
        stock_status: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[InventoryItemModel], int]:
        filters = self._item_filters(
            user_id=user_id,
            search=search,
            product_id=product_id,
            category_id=category_id,
            is_active=is_active,
            stock_status=stock_status,
        )

        total_result = await self.session.execute(
            select(func.count())
            .select_from(InventoryItemModel)
            .join(ProductModel, ProductModel.id == InventoryItemModel.product_id)
            .where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = ITEM_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(InventoryItemModel)
            .join(ProductModel, ProductModel.id == InventoryItemModel.product_id)
            .options(selectinload(InventoryItemModel.product))
            .where(*filters)
            .order_by(sort_expression, desc(InventoryItemModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def update_inventory_item(
        self,
        item: InventoryItemModel,
        values: dict[str, Any],
    ) -> InventoryItemModel:
        for field, value in values.items():
            setattr(item, field, value)
        item.updated_at = utc_now()
        await self.session.flush()
        return item

    async def create_stock_movement(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        inventory_item_id: UUID,
        values: dict[str, Any],
    ) -> InventoryStockMovementModel:
        movement = InventoryStockMovementModel(
            user_id=user_id,
            product_id=product_id,
            inventory_item_id=inventory_item_id,
            **values,
        )
        self.session.add(movement)
        await self.session.flush()
        return movement

    async def list_stock_movements_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID | None,
        movement_type: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[InventoryStockMovementModel], int]:
        filters = [InventoryStockMovementModel.user_id == user_id]
        if product_id is not None:
            filters.append(InventoryStockMovementModel.product_id == product_id)
        if movement_type is not None:
            filters.append(InventoryStockMovementModel.movement_type == movement_type)
        if date_from is not None:
            filters.append(InventoryStockMovementModel.occurred_at >= date_from)
        if date_to is not None:
            filters.append(InventoryStockMovementModel.occurred_at <= date_to)

        total_result = await self.session.execute(
            select(func.count())
            .select_from(InventoryStockMovementModel)
            .where(*filters)
        )
        total = int(total_result.scalar_one())

        sort_column = MOVEMENT_SORT_COLUMNS[sort_by]
        sort_expression = asc(sort_column) if sort_order == "asc" else desc(sort_column)
        result = await self.session.execute(
            select(InventoryStockMovementModel)
            .where(*filters)
            .order_by(sort_expression, desc(InventoryStockMovementModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def list_low_stock_items_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[InventoryItemModel], int]:
        filters = [
            InventoryItemModel.user_id == user_id,
            InventoryItemModel.is_active.is_(True),
            InventoryItemModel.current_stock <= InventoryItemModel.minimum_stock,
        ]
        total_result = await self.session.execute(
            select(func.count()).select_from(InventoryItemModel).where(*filters)
        )
        total = int(total_result.scalar_one())
        result = await self.session.execute(
            select(InventoryItemModel)
            .options(selectinload(InventoryItemModel.product))
            .where(*filters)
            .order_by(asc(InventoryItemModel.current_stock))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def get_inventory_summary_for_user(self, *, user_id: UUID) -> dict[str, Any]:
        low_stock_count = await self.count_low_stock_for_user(user_id=user_id)
        out_of_stock_count = await self.count_out_of_stock_for_user(user_id=user_id)
        item_count_result = await self.session.execute(
            select(func.count())
            .select_from(InventoryItemModel)
            .where(InventoryItemModel.user_id == user_id)
        )
        products_tracked_result = await self.session.execute(
            select(func.count(func.distinct(InventoryItemModel.product_id))).where(
                InventoryItemModel.user_id == user_id,
            )
        )
        stock_sum_result = await self.session.execute(
            select(func.coalesce(func.sum(InventoryItemModel.current_stock), 0)).where(
                InventoryItemModel.user_id == user_id,
            )
        )
        recent_since = utc_now() - timedelta(days=7)
        recent_movement_result = await self.session.execute(
            select(func.count())
            .select_from(InventoryStockMovementModel)
            .where(
                InventoryStockMovementModel.user_id == user_id,
                InventoryStockMovementModel.occurred_at >= recent_since,
            )
        )
        return {
            "total_inventory_items": int(item_count_result.scalar_one()),
            "total_products_tracked": int(products_tracked_result.scalar_one()),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "total_stock_quantity": Decimal(str(stock_sum_result.scalar_one())),
            "recent_movement_count": int(recent_movement_result.scalar_one()),
        }

    async def count_low_stock_for_user(self, *, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(InventoryItemModel)
            .where(
                InventoryItemModel.user_id == user_id,
                InventoryItemModel.is_active.is_(True),
                InventoryItemModel.current_stock <= InventoryItemModel.minimum_stock,
            )
        )
        return int(result.scalar_one())

    async def count_out_of_stock_for_user(self, *, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(InventoryItemModel)
            .where(
                InventoryItemModel.user_id == user_id,
                InventoryItemModel.is_active.is_(True),
                InventoryItemModel.current_stock == 0,
            )
        )
        return int(result.scalar_one())

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    def _item_filters(
        self,
        *,
        user_id: UUID,
        search: str | None,
        product_id: UUID | None,
        category_id: UUID | None,
        is_active: bool | None,
        stock_status: str | None,
    ) -> list[Any]:
        filters = [InventoryItemModel.user_id == user_id]
        if search:
            search_pattern = f"%{search.strip()}%"
            sku_pattern = f"%{search.strip().upper()}%"
            filters.append(
                or_(
                    ProductModel.name.ilike(search_pattern),
                    ProductModel.normalized_sku.ilike(sku_pattern),
                )
            )
        if product_id is not None:
            filters.append(InventoryItemModel.product_id == product_id)
        if category_id is not None:
            filters.append(ProductModel.category_id == category_id)
        if is_active is not None:
            filters.append(InventoryItemModel.is_active == is_active)
        if stock_status == "inactive":
            filters.append(InventoryItemModel.is_active.is_(False))
        elif stock_status == "out_of_stock":
            filters.extend(
                [
                    InventoryItemModel.is_active.is_(True),
                    InventoryItemModel.current_stock == 0,
                ]
            )
        elif stock_status == "low_stock":
            filters.extend(
                [
                    InventoryItemModel.is_active.is_(True),
                    InventoryItemModel.current_stock
                    <= InventoryItemModel.minimum_stock,
                ]
            )
        elif stock_status == "in_stock":
            filters.extend(
                [
                    InventoryItemModel.is_active.is_(True),
                    InventoryItemModel.current_stock
                    > InventoryItemModel.minimum_stock,
                ]
            )
        return filters
