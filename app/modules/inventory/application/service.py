from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.exceptions import AppError
from app.modules.inventory.domain.exceptions import (
    InventoryItemAlreadyExistsError,
    InventoryItemNotFoundError,
    InventoryProductNotFoundError,
)
from app.modules.inventory.domain.stock import (
    calculate_movement,
    ensure_item_sort_field,
    ensure_movement_sort_field,
    normalize_item_create_values,
    normalize_item_update_values,
    normalize_sort_order,
    normalize_stock_status_filter,
    validate_public_movement_type,
)
from app.shared.utils import utc_now


class InventoryService:
    def __init__(self, *, repository: Any) -> None:
        self.repository = repository

    async def create_inventory_item(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        await self._get_product(user_id=user_id, product_id=product_id)
        existing_item = await self.repository.get_inventory_item_by_product_for_user(
            user_id=user_id,
            product_id=product_id,
        )
        if existing_item is not None:
            raise InventoryItemAlreadyExistsError()

        normalized = normalize_item_create_values(values)
        opening_stock = normalized.pop("opening_stock")
        item_values = {"current_stock": opening_stock, **normalized}

        try:
            item = await self.repository.create_inventory_item(
                user_id=user_id,
                product_id=product_id,
                values=item_values,
            )
            if opening_stock > 0:
                await self.repository.create_stock_movement(
                    user_id=user_id,
                    product_id=product_id,
                    inventory_item_id=item.id,
                    values={
                        "movement_type": "opening_stock",
                        "quantity_delta": opening_stock,
                        "quantity_before": 0,
                        "quantity_after": opening_stock,
                        "reason": values.get("reason") or "Opening stock",
                        "reference_type": values.get("reference_type"),
                        "reference_id": values.get("reference_id"),
                        "occurred_at": values.get("occurred_at") or utc_now(),
                    },
                )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return item

    async def list_inventory_items(
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
    ) -> tuple[list[Any], int]:
        if product_id is not None:
            await self._get_product(user_id=user_id, product_id=product_id)

        return await self.repository.list_inventory_items_for_user(
            user_id=user_id,
            search=search,
            product_id=product_id,
            category_id=category_id,
            is_active=is_active,
            stock_status=normalize_stock_status_filter(stock_status),
            limit=limit,
            offset=offset,
            sort_by=ensure_item_sort_field(sort_by),
            sort_order=normalize_sort_order(sort_order),
        )

    async def get_inventory_item(self, *, user_id: UUID, product_id: UUID) -> Any:
        await self._get_product(user_id=user_id, product_id=product_id)
        return await self._get_inventory_item(user_id=user_id, product_id=product_id)

    async def update_inventory_thresholds(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        values: dict[str, Any],
    ) -> Any:
        await self._get_product(user_id=user_id, product_id=product_id)
        item = await self._get_inventory_item(user_id=user_id, product_id=product_id)
        normalized = normalize_item_update_values(values)

        try:
            item = await self.repository.update_inventory_item(item, normalized)
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return item

    async def create_stock_movement(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        movement_type: str,
        quantity: Any,
        reason: str | None,
        reference_type: str | None,
        reference_id: str | None,
        occurred_at: datetime | None,
    ) -> Any:
        await self._get_product(user_id=user_id, product_id=product_id)
        movement_type = validate_public_movement_type(movement_type)
        item = await self._get_inventory_item(
            user_id=user_id,
            product_id=product_id,
            for_update=True,
        )
        quantity_before = item.current_stock
        quantity_delta, quantity_after = calculate_movement(
            movement_type=movement_type,
            current_stock=quantity_before,
            quantity=quantity,
        )

        try:
            await self.repository.update_inventory_item(
                item,
                {"current_stock": quantity_after},
            )
            movement = await self.repository.create_stock_movement(
                user_id=user_id,
                product_id=product_id,
                inventory_item_id=item.id,
                values={
                    "movement_type": movement_type,
                    "quantity_delta": quantity_delta,
                    "quantity_before": quantity_before,
                    "quantity_after": quantity_after,
                    "reason": _normalize_optional_text(reason),
                    "reference_type": _normalize_optional_text(reference_type),
                    "reference_id": _normalize_optional_text(reference_id),
                    "occurred_at": occurred_at or utc_now(),
                },
            )
            await self.repository.commit()
        except AppError:
            await self.repository.rollback()
            raise

        return movement

    async def list_stock_movements(
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
    ) -> tuple[list[Any], int]:
        if product_id is not None:
            await self._get_product(user_id=user_id, product_id=product_id)
        if movement_type is not None:
            movement_type = validate_public_movement_type(movement_type)

        return await self.repository.list_stock_movements_for_user(
            user_id=user_id,
            product_id=product_id,
            movement_type=movement_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
            sort_by=ensure_movement_sort_field(sort_by),
            sort_order=normalize_sort_order(sort_order),
        )

    async def list_low_stock_items(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        return await self.repository.list_low_stock_items_for_user(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    async def get_inventory_summary(self, *, user_id: UUID) -> dict[str, Any]:
        return await self.repository.get_inventory_summary_for_user(user_id=user_id)

    async def _get_product(self, *, user_id: UUID, product_id: UUID) -> Any:
        product = await self.repository.get_product_for_user(
            user_id=user_id,
            product_id=product_id,
        )
        if product is None:
            raise InventoryProductNotFoundError()
        return product

    async def _get_inventory_item(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        for_update: bool = False,
    ) -> Any:
        item = await self.repository.get_inventory_item_by_product_for_user(
            user_id=user_id,
            product_id=product_id,
            for_update=for_update,
        )
        if item is None:
            raise InventoryItemNotFoundError()
        return item


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None
