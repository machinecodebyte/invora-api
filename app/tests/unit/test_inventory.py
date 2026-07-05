from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.inventory.application.service import InventoryService
from app.modules.inventory.domain.exceptions import (
    InsufficientStockError,
    InvalidInventoryMovementTypeError,
    InvalidInventorySortFieldError,
    InvalidInventoryThresholdError,
)
from app.modules.inventory.domain.stock import (
    calculate_movement,
    calculate_stock_status,
    ensure_item_sort_field,
    normalize_threshold,
    validate_public_movement_type,
)


def test_stock_in_calculation() -> None:
    delta, after = calculate_movement(
        movement_type="stock_in",
        current_stock=Decimal("10.000"),
        quantity=Decimal("2.500"),
    )

    assert delta == Decimal("2.500")
    assert after == Decimal("12.500")


def test_stock_out_calculation() -> None:
    delta, after = calculate_movement(
        movement_type="stock_out",
        current_stock=Decimal("10.000"),
        quantity=Decimal("2.000"),
    )

    assert delta == Decimal("-2.000")
    assert after == Decimal("8.000")


def test_adjustment_delta_calculation() -> None:
    delta, after = calculate_movement(
        movement_type="adjustment",
        current_stock=Decimal("10.000"),
        quantity=Decimal("4.250"),
    )

    assert delta == Decimal("-5.750")
    assert after == Decimal("4.250")


def test_negative_stock_prevention() -> None:
    with pytest.raises(InsufficientStockError):
        calculate_movement(
            movement_type="stock_out",
            current_stock=Decimal("1.000"),
            quantity=Decimal("2.000"),
        )


def test_low_and_out_of_stock_status_calculation() -> None:
    assert (
        calculate_stock_status(
            current_stock=Decimal("0.000"),
            minimum_stock=Decimal("5.000"),
            is_active=True,
        )
        == "out_of_stock"
    )
    assert (
        calculate_stock_status(
            current_stock=Decimal("3.000"),
            minimum_stock=Decimal("5.000"),
            is_active=True,
        )
        == "low_stock"
    )


def test_threshold_validation() -> None:
    assert normalize_threshold("2.500", field_name="minimum_stock") == Decimal("2.500")

    with pytest.raises(InvalidInventoryThresholdError):
        normalize_threshold("-1", field_name="minimum_stock")


def test_movement_type_validation() -> None:
    assert validate_public_movement_type("stock_in") == "stock_in"

    with pytest.raises(InvalidInventoryMovementTypeError):
        validate_public_movement_type("opening_stock")


def test_safe_sort_field_validation() -> None:
    assert ensure_item_sort_field("current_stock") == "current_stock"

    with pytest.raises(InvalidInventorySortFieldError):
        ensure_item_sort_field("user_id")


@pytest.mark.asyncio
async def test_stock_movement_service_updates_balance_and_creates_ledger(
    product_repository,
    inventory_repository,
) -> None:
    user_id = uuid4()
    product = await product_repository.create_product(
        user_id=user_id,
        values={
            "name": "Milk",
            "normalized_name": "milk",
            "sku": "MILK-1",
            "normalized_sku": "MILK-1",
            "description": None,
            "unit": "liter",
            "selling_price": Decimal("10.00"),
            "cost_price": None,
        },
    )
    service = InventoryService(repository=inventory_repository)
    await service.create_inventory_item(
        user_id=user_id,
        product_id=product.id,
        values={"opening_stock": Decimal("5.000")},
    )

    movement = await service.create_stock_movement(
        user_id=user_id,
        product_id=product.id,
        movement_type="stock_in",
        quantity=Decimal("3.000"),
        reason="Received",
        reference_type=None,
        reference_id=None,
        occurred_at=None,
    )
    item = await service.get_inventory_item(user_id=user_id, product_id=product.id)

    assert item.current_stock == Decimal("8.000")
    assert movement.quantity_delta == Decimal("3.000")
    assert len(inventory_repository.movements_by_id) == 2
