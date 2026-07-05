from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.products.application.service import ProductService
from app.modules.products.domain.catalog import (
    ensure_product_sort_field,
    normalize_category_key,
    normalize_category_name,
    normalize_sku,
    validate_price,
    validate_unit,
)
from app.modules.products.domain.exceptions import (
    DuplicateProductCategoryError,
    DuplicateProductSkuError,
    InvalidProductPriceError,
    InvalidProductSkuError,
    InvalidProductSortFieldError,
    InvalidProductUnitError,
    ProductCategoryHasActiveProductsError,
)


def test_sku_normalization() -> None:
    assert normalize_sku(" inv  001 ") == "INV-001"


def test_sku_validation_rejects_unsafe_characters() -> None:
    with pytest.raises(InvalidProductSkuError):
        normalize_sku("sku/001")


def test_category_name_normalization() -> None:
    assert normalize_category_name("  Fresh   Food ") == "Fresh Food"
    assert normalize_category_key("  Fresh   Food ") == "fresh food"


def test_unit_validation_uses_allowed_units() -> None:
    assert validate_unit(" KG ") == "kg"

    with pytest.raises(InvalidProductUnitError):
        validate_unit("carton")


def test_price_validation_rejects_negative_values() -> None:
    assert validate_price("12.50", field_name="selling_price") == Decimal("12.50")

    with pytest.raises(InvalidProductPriceError):
        validate_price("-1.00", field_name="selling_price")


@pytest.mark.asyncio
async def test_duplicate_sku_handling(product_repository) -> None:
    user_id = uuid4()
    service = ProductService(repository=product_repository)

    await service.create_product(
        user_id=user_id,
        values={"name": "Milk", "sku": "milk-1", "unit": "liter"},
    )

    with pytest.raises(DuplicateProductSkuError):
        await service.create_product(
            user_id=user_id,
            values={"name": "Milk Two", "sku": " MILK 1 ", "unit": "liter"},
        )


@pytest.mark.asyncio
async def test_duplicate_category_handling(product_repository) -> None:
    user_id = uuid4()
    service = ProductService(repository=product_repository)

    await service.create_category(user_id=user_id, values={"name": "Beverages"})

    with pytest.raises(DuplicateProductCategoryError):
        await service.create_category(user_id=user_id, values={"name": " beverages "})


@pytest.mark.asyncio
async def test_archive_category_with_active_products_rule(product_repository) -> None:
    user_id = uuid4()
    service = ProductService(repository=product_repository)
    category = await service.create_category(user_id=user_id, values={"name": "Dairy"})
    await service.create_product(
        user_id=user_id,
        values={
            "name": "Milk",
            "sku": "milk-1",
            "unit": "liter",
            "category_id": category.id,
        },
    )

    with pytest.raises(ProductCategoryHasActiveProductsError):
        await service.archive_category(user_id=user_id, category_id=category.id)


def test_safe_sort_field_validation() -> None:
    assert ensure_product_sort_field("sku") == "sku"

    with pytest.raises(InvalidProductSortFieldError):
        ensure_product_sort_field("user_id")
