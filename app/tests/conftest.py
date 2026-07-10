import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient


def pytest_configure() -> None:
    os.environ["APP_NAME"] = "Invora Backend Test"
    os.environ["APP_ENV"] = "test"
    os.environ["DEBUG"] = "false"
    os.environ["API_V1_PREFIX"] = "/api/v1"
    os.environ["DATABASE_URL"] = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/invora_test"
    )
    os.environ["REDIS_URL"] = "redis://localhost:56379/1"
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-foundation"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
    os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "14"


@pytest.fixture
def app():
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    return create_app()


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    from app.db.session import close_database_engine

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    await close_database_engine()


@dataclass(slots=True)
class FakeUser:
    id: UUID
    email: str
    full_name: str | None
    hashed_password: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    phone_number: str | None = None
    avatar_url: str | None = None
    timezone: str | None = None
    locale: str | None = None


@dataclass(slots=True)
class FakeRefreshToken:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    replaced_by_token_id: UUID | None
    user_agent: str | None
    ip_address: str | None


@dataclass(slots=True)
class FakeProductCategory:
    id: UUID
    user_id: UUID
    name: str
    normalized_name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class FakeProduct:
    id: UUID
    user_id: UUID
    category_id: UUID | None
    name: str
    normalized_name: str
    sku: str
    normalized_sku: str
    description: str | None
    unit: str
    selling_price: Decimal
    cost_price: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class FakeInventoryItem:
    id: UUID
    user_id: UUID
    product_id: UUID
    product: FakeProduct
    current_stock: Decimal
    minimum_stock: Decimal
    safety_stock: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class FakeStockMovement:
    id: UUID
    user_id: UUID
    product_id: UUID
    inventory_item_id: UUID
    movement_type: str
    quantity_delta: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    reason: str | None
    reference_type: str | None
    reference_id: str | None
    occurred_at: datetime
    created_at: datetime


@dataclass(slots=True)
class FakeSalesUploadBatch:
    id: UUID
    user_id: UUID
    original_filename: str
    file_hash: str | None
    status: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    started_at: datetime
    completed_at: datetime | None
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class FakeSalesTransaction:
    id: UUID
    user_id: UUID
    product_id: UUID
    product: FakeProduct
    upload_batch_id: UUID | None
    sale_date: date
    quantity: Decimal
    unit_price: Decimal | None
    total_amount: Decimal | None
    customer_name: str | None
    channel: str | None
    notes: str | None
    source: str
    deleted_at: datetime | None
    deleted_reason: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class FakeSalesRejectedRow:
    id: UUID
    user_id: UUID
    upload_batch_id: UUID
    row_number: int
    raw_data: dict[str, str]
    error_code: str
    error_message: str
    created_at: datetime


@dataclass(slots=True)
class FakeForecastRun:
    id: UUID
    user_id: UUID
    horizon_days: int
    status: str
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    failure_reason: str | None
    total_products: int
    total_sales_records: int
    run_metadata: dict[str, object] | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class FakeForecastPrediction:
    id: UUID
    user_id: UUID
    forecast_run_id: UUID
    product_id: UUID
    forecast_date: date
    predicted_demand: Decimal
    model_name: str
    created_at: datetime


@dataclass(slots=True)
class FakeForecastMetric:
    id: UUID
    user_id: UUID
    forecast_run_id: UUID
    model_name: str
    mae: Decimal | None
    rmse: Decimal | None
    mape: Decimal | None
    training_rows: int
    validation_rows: int
    total_products: int
    fallback_products: int
    created_at: datetime


@dataclass(slots=True)
class FakeReorderRecommendation:
    id: UUID
    user_id: UUID
    forecast_run_id: UUID
    product_id: UUID
    predicted_demand: Decimal
    current_stock: Decimal
    minimum_stock: Decimal
    safety_stock: Decimal
    required_stock: Decimal
    reorder_quantity: Decimal
    stock_gap: Decimal
    risk_level: str
    recommended_action: str
    reason: str | None
    status: str
    generated_at: datetime
    acknowledged_at: datetime | None
    dismissed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FakeAuthRepository:
    def __init__(self) -> None:
        self.users_by_email: dict[str, FakeUser] = {}
        self.users_by_id: dict[UUID, FakeUser] = {}
        self.refresh_tokens_by_hash: dict[str, FakeRefreshToken] = {}

    async def create_user(
        self,
        *,
        email: str,
        full_name: str | None,
        hashed_password: str,
    ) -> FakeUser:
        from app.modules.auth.domain.exceptions import DuplicateEmailError
        from app.shared.utils import utc_now

        if email in self.users_by_email:
            raise DuplicateEmailError()

        now = utc_now()
        user = FakeUser(
            id=uuid4(),
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            created_at=now,
            updated_at=now,
        )
        self.users_by_email[user.email] = user
        self.users_by_id[user.id] = user
        return user

    async def get_user_by_email(self, email: str) -> FakeUser | None:
        return self.users_by_email.get(email)

    async def get_user_by_id(self, user_id: UUID) -> FakeUser | None:
        return self.users_by_id.get(user_id)

    async def email_exists(self, email: str) -> bool:
        return email in self.users_by_email

    async def create_refresh_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> FakeRefreshToken:
        from app.shared.utils import utc_now

        refresh_token = FakeRefreshToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            created_at=utc_now(),
            replaced_by_token_id=None,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        self.refresh_tokens_by_hash[token_hash] = refresh_token
        return refresh_token

    async def get_refresh_token_by_hash(
        self,
        token_hash: str,
    ) -> FakeRefreshToken | None:
        return self.refresh_tokens_by_hash.get(token_hash)

    async def revoke_refresh_token(
        self,
        refresh_token: FakeRefreshToken,
        *,
        revoked_at: datetime,
        replaced_by_token_id: UUID | None = None,
    ) -> None:
        refresh_token.revoked_at = revoked_at
        refresh_token.replaced_by_token_id = replaced_by_token_id

    async def rotate_refresh_token(
        self,
        refresh_token: FakeRefreshToken,
        *,
        new_token_hash: str,
        expires_at: datetime,
        revoked_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> FakeRefreshToken:
        new_refresh_token = await self.create_refresh_token(
            user_id=refresh_token.user_id,
            token_hash=new_token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.revoke_refresh_token(
            refresh_token,
            revoked_at=revoked_at,
            replaced_by_token_id=new_refresh_token.id,
        )
        return new_refresh_token

    async def update_user_profile(
        self,
        user: FakeUser,
        values: dict[str, object],
    ) -> FakeUser:
        from app.shared.utils import utc_now

        for field, value in values.items():
            setattr(user, field, value)
        user.updated_at = utc_now()
        return user

    async def update_password_hash(
        self,
        user: FakeUser,
        hashed_password: str,
    ) -> FakeUser:
        from app.shared.utils import utc_now

        user.hashed_password = hashed_password
        user.updated_at = utc_now()
        return user

    async def revoke_user_refresh_tokens(self, user_id: UUID) -> None:
        from app.shared.utils import utc_now

        revoked_at = utc_now()
        for refresh_token in self.refresh_tokens_by_hash.values():
            if refresh_token.user_id == user_id and refresh_token.revoked_at is None:
                refresh_token.revoked_at = revoked_at

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeProductRepository:
    def __init__(self) -> None:
        self.products_by_id: dict[UUID, FakeProduct] = {}
        self.categories_by_id: dict[UUID, FakeProductCategory] = {}

    async def create_product(
        self,
        *,
        user_id: UUID,
        values: dict[str, object],
    ) -> FakeProduct:
        from app.modules.products.domain.exceptions import DuplicateProductSkuError
        from app.shared.utils import utc_now

        if await self.get_product_by_sku_for_user(
            user_id=user_id,
            normalized_sku=str(values["normalized_sku"]),
        ):
            raise DuplicateProductSkuError()

        now = utc_now()
        product = FakeProduct(
            id=uuid4(),
            user_id=user_id,
            category_id=values.get("category_id"),
            name=str(values["name"]),
            normalized_name=str(values["normalized_name"]),
            sku=str(values["sku"]),
            normalized_sku=str(values["normalized_sku"]),
            description=values.get("description"),
            unit=str(values["unit"]),
            selling_price=values.get("selling_price", Decimal("0.00")),
            cost_price=values.get("cost_price"),
            is_active=bool(values.get("is_active", True)),
            created_at=now,
            updated_at=now,
        )
        self.products_by_id[product.id] = product
        return product

    async def get_product_by_id_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> FakeProduct | None:
        product = self.products_by_id.get(product_id)
        if product is None or product.user_id != user_id:
            return None
        return product

    async def get_product_by_sku_for_user(
        self,
        *,
        user_id: UUID,
        normalized_sku: str,
    ) -> FakeProduct | None:
        for product in self.products_by_id.values():
            if product.user_id == user_id and product.normalized_sku == normalized_sku:
                return product
        return None

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
    ) -> tuple[list[FakeProduct], int]:
        products = [
            product
            for product in self.products_by_id.values()
            if product.user_id == user_id
        ]
        if search:
            search_value = search.strip().casefold()
            products = [
                product
                for product in products
                if search_value in product.name.casefold()
                or search_value in product.normalized_sku.casefold()
            ]
        if category_id is not None:
            products = [
                product for product in products if product.category_id == category_id
            ]
        if is_active is not None:
            products = [
                product for product in products if product.is_active == is_active
            ]

        total = len(products)
        products.sort(
            key=lambda product: _product_sort_value(product, sort_by),
            reverse=sort_order == "desc",
        )
        return products[offset : offset + limit], total

    async def update_product(
        self,
        product: FakeProduct,
        values: dict[str, object],
    ) -> FakeProduct:
        from app.modules.products.domain.exceptions import DuplicateProductSkuError
        from app.shared.utils import utc_now

        normalized_sku = values.get("normalized_sku")
        if normalized_sku is not None:
            existing = await self.get_product_by_sku_for_user(
                user_id=product.user_id,
                normalized_sku=str(normalized_sku),
            )
            if existing is not None and existing.id != product.id:
                raise DuplicateProductSkuError()

        for field, value in values.items():
            setattr(product, field, value)
        product.updated_at = utc_now()
        return product

    async def archive_product(self, product: FakeProduct) -> FakeProduct:
        from app.shared.utils import utc_now

        product.is_active = False
        product.updated_at = utc_now()
        return product

    async def create_category(
        self,
        *,
        user_id: UUID,
        values: dict[str, object],
    ) -> FakeProductCategory:
        from app.modules.products.domain.exceptions import DuplicateProductCategoryError
        from app.shared.utils import utc_now

        if await self.get_category_by_name_for_user(
            user_id=user_id,
            normalized_name=str(values["normalized_name"]),
        ):
            raise DuplicateProductCategoryError()

        now = utc_now()
        category = FakeProductCategory(
            id=uuid4(),
            user_id=user_id,
            name=str(values["name"]),
            normalized_name=str(values["normalized_name"]),
            description=values.get("description"),
            is_active=bool(values.get("is_active", True)),
            created_at=now,
            updated_at=now,
        )
        self.categories_by_id[category.id] = category
        return category

    async def get_category_by_id_for_user(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> FakeProductCategory | None:
        category = self.categories_by_id.get(category_id)
        if category is None or category.user_id != user_id:
            return None
        return category

    async def get_category_by_name_for_user(
        self,
        *,
        user_id: UUID,
        normalized_name: str,
    ) -> FakeProductCategory | None:
        for category in self.categories_by_id.values():
            if (
                category.user_id == user_id
                and category.normalized_name == normalized_name
            ):
                return category
        return None

    async def list_categories_for_user(
        self,
        *,
        user_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[FakeProductCategory], int]:
        categories = [
            category
            for category in self.categories_by_id.values()
            if category.user_id == user_id
        ]
        if is_active is not None:
            categories = [
                category for category in categories if category.is_active == is_active
            ]

        total = len(categories)
        categories.sort(
            key=lambda category: _category_sort_value(category, sort_by),
            reverse=sort_order == "desc",
        )
        return categories[offset : offset + limit], total

    async def update_category(
        self,
        category: FakeProductCategory,
        values: dict[str, object],
    ) -> FakeProductCategory:
        from app.modules.products.domain.exceptions import DuplicateProductCategoryError
        from app.shared.utils import utc_now

        normalized_name = values.get("normalized_name")
        if normalized_name is not None:
            existing = await self.get_category_by_name_for_user(
                user_id=category.user_id,
                normalized_name=str(normalized_name),
            )
            if existing is not None and existing.id != category.id:
                raise DuplicateProductCategoryError()

        for field, value in values.items():
            setattr(category, field, value)
        category.updated_at = utc_now()
        return category

    async def archive_category(
        self,
        category: FakeProductCategory,
    ) -> FakeProductCategory:
        from app.shared.utils import utc_now

        category.is_active = False
        category.updated_at = utc_now()
        return category

    async def count_active_products_by_category(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> int:
        return sum(
            1
            for product in self.products_by_id.values()
            if product.user_id == user_id
            and product.category_id == category_id
            and product.is_active
        )

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeInventoryRepository:
    def __init__(self, product_repository: FakeProductRepository) -> None:
        self.product_repository = product_repository
        self.items_by_id: dict[UUID, FakeInventoryItem] = {}
        self.movements_by_id: dict[UUID, FakeStockMovement] = {}

    async def get_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> FakeProduct | None:
        return await self.product_repository.get_product_by_id_for_user(
            user_id=user_id,
            product_id=product_id,
        )

    async def create_inventory_item(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        values: dict[str, object],
    ) -> FakeInventoryItem:
        from app.modules.inventory.domain.exceptions import (
            InventoryItemAlreadyExistsError,
        )
        from app.shared.utils import utc_now

        if await self.get_inventory_item_by_product_for_user(
            user_id=user_id,
            product_id=product_id,
        ):
            raise InventoryItemAlreadyExistsError()

        product = await self.get_product_for_user(
            user_id=user_id,
            product_id=product_id,
        )
        now = utc_now()
        item = FakeInventoryItem(
            id=uuid4(),
            user_id=user_id,
            product_id=product_id,
            product=product,
            current_stock=_decimal_value(values.get("current_stock", "0")),
            minimum_stock=_decimal_value(values.get("minimum_stock", "0")),
            safety_stock=_decimal_value(values.get("safety_stock", "0")),
            is_active=bool(values.get("is_active", True)),
            created_at=now,
            updated_at=now,
        )
        self.items_by_id[item.id] = item
        return item

    async def get_inventory_item_by_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        for_update: bool = False,
    ) -> FakeInventoryItem | None:
        _ = for_update
        for item in self.items_by_id.values():
            if item.user_id == user_id and item.product_id == product_id:
                return item
        return None

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
    ) -> tuple[list[FakeInventoryItem], int]:
        from app.modules.inventory.domain.stock import calculate_stock_status

        items = [item for item in self.items_by_id.values() if item.user_id == user_id]
        if search:
            search_value = search.strip().casefold()
            items = [
                item
                for item in items
                if search_value in item.product.name.casefold()
                or search_value in item.product.normalized_sku.casefold()
            ]
        if product_id is not None:
            items = [item for item in items if item.product_id == product_id]
        if category_id is not None:
            items = [
                item for item in items if item.product.category_id == category_id
            ]
        if is_active is not None:
            items = [item for item in items if item.is_active == is_active]
        if stock_status is not None:
            items = [
                item
                for item in items
                if calculate_stock_status(
                    current_stock=item.current_stock,
                    minimum_stock=item.minimum_stock,
                    is_active=item.is_active,
                )
                == stock_status
            ]

        total = len(items)
        items.sort(
            key=lambda item: _inventory_item_sort_value(item, sort_by),
            reverse=sort_order == "desc",
        )
        return items[offset : offset + limit], total

    async def update_inventory_item(
        self,
        item: FakeInventoryItem,
        values: dict[str, object],
    ) -> FakeInventoryItem:
        from app.shared.utils import utc_now

        for field, value in values.items():
            setattr(item, field, _decimal_value(value) if "stock" in field else value)
        item.updated_at = utc_now()
        return item

    async def create_stock_movement(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
        inventory_item_id: UUID,
        values: dict[str, object],
    ) -> FakeStockMovement:
        from app.shared.utils import utc_now

        movement = FakeStockMovement(
            id=uuid4(),
            user_id=user_id,
            product_id=product_id,
            inventory_item_id=inventory_item_id,
            movement_type=str(values["movement_type"]),
            quantity_delta=_decimal_value(values["quantity_delta"]),
            quantity_before=_decimal_value(values["quantity_before"]),
            quantity_after=_decimal_value(values["quantity_after"]),
            reason=values.get("reason"),
            reference_type=values.get("reference_type"),
            reference_id=values.get("reference_id"),
            occurred_at=values.get("occurred_at") or utc_now(),
            created_at=utc_now(),
        )
        self.movements_by_id[movement.id] = movement
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
    ) -> tuple[list[FakeStockMovement], int]:
        movements = [
            movement
            for movement in self.movements_by_id.values()
            if movement.user_id == user_id
        ]
        if product_id is not None:
            movements = [
                movement
                for movement in movements
                if movement.product_id == product_id
            ]
        if movement_type is not None:
            movements = [
                movement
                for movement in movements
                if movement.movement_type == movement_type
            ]
        if date_from is not None:
            movements = [
                movement
                for movement in movements
                if movement.occurred_at >= date_from
            ]
        if date_to is not None:
            movements = [
                movement for movement in movements if movement.occurred_at <= date_to
            ]

        total = len(movements)
        movements.sort(
            key=lambda movement: getattr(movement, sort_by),
            reverse=sort_order == "desc",
        )
        return movements[offset : offset + limit], total

    async def list_low_stock_items_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[FakeInventoryItem], int]:
        items = [
            item
            for item in self.items_by_id.values()
            if item.user_id == user_id
            and item.is_active
            and item.current_stock <= item.minimum_stock
        ]
        total = len(items)
        items.sort(key=lambda item: item.current_stock)
        return items[offset : offset + limit], total

    async def get_inventory_summary_for_user(
        self,
        *,
        user_id: UUID,
    ) -> dict[str, object]:
        items = [item for item in self.items_by_id.values() if item.user_id == user_id]
        movements = [
            movement
            for movement in self.movements_by_id.values()
            if movement.user_id == user_id
        ]
        return {
            "total_inventory_items": len(items),
            "total_products_tracked": len({item.product_id for item in items}),
            "low_stock_count": await self.count_low_stock_for_user(user_id=user_id),
            "out_of_stock_count": await self.count_out_of_stock_for_user(
                user_id=user_id,
            ),
            "total_stock_quantity": sum(
                (item.current_stock for item in items),
                Decimal("0.000"),
            ),
            "recent_movement_count": len(movements),
        }

    async def count_low_stock_for_user(self, *, user_id: UUID) -> int:
        return sum(
            1
            for item in self.items_by_id.values()
            if item.user_id == user_id
            and item.is_active
            and item.current_stock <= item.minimum_stock
        )

    async def count_out_of_stock_for_user(self, *, user_id: UUID) -> int:
        return sum(
            1
            for item in self.items_by_id.values()
            if item.user_id == user_id
            and item.is_active
            and item.current_stock == Decimal("0.000")
        )

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeSalesRepository:
    def __init__(self, product_repository: FakeProductRepository) -> None:
        self.product_repository = product_repository
        self.batches_by_id: dict[UUID, FakeSalesUploadBatch] = {}
        self.transactions_by_id: dict[UUID, FakeSalesTransaction] = {}
        self.rejected_rows_by_id: dict[UUID, FakeSalesRejectedRow] = {}

    async def create_upload_batch(
        self,
        *,
        user_id: UUID,
        values: dict[str, object],
    ) -> FakeSalesUploadBatch:
        from app.shared.utils import utc_now

        now = utc_now()
        batch = FakeSalesUploadBatch(
            id=uuid4(),
            user_id=user_id,
            original_filename=str(values["original_filename"]),
            file_hash=values.get("file_hash"),
            status=str(values["status"]),
            total_rows=int(values.get("total_rows", 0)),
            accepted_rows=int(values.get("accepted_rows", 0)),
            rejected_rows=int(values.get("rejected_rows", 0)),
            started_at=values.get("started_at") or now,
            completed_at=values.get("completed_at"),
            failure_reason=values.get("failure_reason"),
            created_at=now,
            updated_at=now,
        )
        self.batches_by_id[batch.id] = batch
        return batch

    async def update_upload_batch_status(
        self,
        batch: FakeSalesUploadBatch,
        values: dict[str, object],
    ) -> FakeSalesUploadBatch:
        from app.shared.utils import utc_now

        for field, value in values.items():
            setattr(batch, field, value)
        batch.updated_at = utc_now()
        return batch

    async def get_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> FakeProduct | None:
        return await self.product_repository.get_product_by_id_for_user(
            user_id=user_id,
            product_id=product_id,
        )

    async def create_transaction(
        self,
        *,
        user_id: UUID,
        values: dict[str, object],
    ) -> FakeSalesTransaction:
        from app.shared.utils import utc_now

        product = await self.get_product_for_user(
            user_id=user_id,
            product_id=values["product_id"],
        )
        now = utc_now()
        transaction = FakeSalesTransaction(
            id=uuid4(),
            user_id=user_id,
            product_id=values["product_id"],
            product=product,
            upload_batch_id=values.get("upload_batch_id"),
            sale_date=values["sale_date"],
            quantity=_decimal_value(values["quantity"]),
            unit_price=(
                None
                if values.get("unit_price") is None
                else _decimal_value(values["unit_price"])
            ),
            total_amount=(
                None
                if values.get("total_amount") is None
                else _decimal_value(values["total_amount"])
            ),
            customer_name=values.get("customer_name"),
            channel=values.get("channel"),
            notes=values.get("notes"),
            source=str(values.get("source", "manual")),
            deleted_at=None,
            deleted_reason=None,
            created_at=now,
            updated_at=now,
        )
        self.transactions_by_id[transaction.id] = transaction
        return transaction

    async def create_sales_transactions_bulk(
        self,
        *,
        user_id: UUID,
        upload_batch_id: UUID,
        rows: list[dict[str, object]],
    ) -> list[FakeSalesTransaction]:
        from app.shared.utils import utc_now

        transactions: list[FakeSalesTransaction] = []
        for row in rows:
            now = utc_now()
            product = await self.get_product_for_user(
                user_id=user_id,
                product_id=row["product_id"],
            )
            transaction = FakeSalesTransaction(
                id=uuid4(),
                user_id=user_id,
                product_id=row["product_id"],
                product=product,
                upload_batch_id=upload_batch_id,
                sale_date=row["sale_date"],
                quantity=_decimal_value(row["quantity"]),
                unit_price=(
                    None
                    if row.get("unit_price") is None
                    else _decimal_value(row["unit_price"])
                ),
                total_amount=(
                    None
                    if row.get("total_amount") is None
                    else _decimal_value(row["total_amount"])
                ),
                customer_name=row.get("customer_name"),
                channel=row.get("channel"),
                notes=row.get("notes"),
                source=str(row["source"]),
                deleted_at=None,
                deleted_reason=None,
                created_at=now,
                updated_at=now,
            )
            self.transactions_by_id[transaction.id] = transaction
            transactions.append(transaction)
        return transactions

    async def create_rejected_rows_bulk(
        self,
        *,
        user_id: UUID,
        upload_batch_id: UUID,
        rows: list[dict[str, object]],
    ) -> list[FakeSalesRejectedRow]:
        from app.shared.utils import utc_now

        rejected_rows: list[FakeSalesRejectedRow] = []
        for row in rows:
            rejected = FakeSalesRejectedRow(
                id=uuid4(),
                user_id=user_id,
                upload_batch_id=upload_batch_id,
                row_number=int(row["row_number"]),
                raw_data=row["raw_data"],
                error_code=str(row["error_code"]),
                error_message=str(row["error_message"]),
                created_at=utc_now(),
            )
            self.rejected_rows_by_id[rejected.id] = rejected
            rejected_rows.append(rejected)
        return rejected_rows

    async def list_upload_batches_for_user(
        self,
        *,
        user_id: UUID,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        sort_order: str,
    ) -> tuple[list[FakeSalesUploadBatch], int]:
        batches = [
            batch for batch in self.batches_by_id.values() if batch.user_id == user_id
        ]
        if status is not None:
            batches = [batch for batch in batches if batch.status == status]
        if date_from is not None:
            batches = [batch for batch in batches if batch.started_at >= date_from]
        if date_to is not None:
            batches = [batch for batch in batches if batch.started_at <= date_to]
        batches.sort(key=lambda batch: batch.started_at, reverse=sort_order == "desc")
        total = len(batches)
        return batches[offset : offset + limit], total

    async def get_upload_batch_for_user(
        self,
        *,
        user_id: UUID,
        upload_id: UUID,
    ) -> FakeSalesUploadBatch | None:
        batch = self.batches_by_id.get(upload_id)
        if batch is None or batch.user_id != user_id:
            return None
        return batch

    async def list_rejected_rows_for_user(
        self,
        *,
        user_id: UUID,
        upload_batch_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[FakeSalesRejectedRow], int]:
        rows = [
            row
            for row in self.rejected_rows_by_id.values()
            if row.user_id == user_id and row.upload_batch_id == upload_batch_id
        ]
        rows.sort(key=lambda row: row.row_number)
        total = len(rows)
        return rows[offset : offset + limit], total

    async def get_transaction_for_user(
        self,
        *,
        user_id: UUID,
        transaction_id: UUID,
        include_deleted: bool = False,
    ) -> FakeSalesTransaction | None:
        transaction = self.transactions_by_id.get(transaction_id)
        if transaction is None or transaction.user_id != user_id:
            return None
        if not include_deleted and transaction.deleted_at is not None:
            return None
        return transaction

    async def list_transactions_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        source: str | None,
        channel: str | None,
        date_from: date | None,
        date_to: date | None,
        include_deleted: bool,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[FakeSalesTransaction], int]:
        transactions = [
            transaction
            for transaction in self.transactions_by_id.values()
            if transaction.user_id == user_id
        ]
        if not include_deleted:
            transactions = [
                transaction
                for transaction in transactions
                if transaction.deleted_at is None
            ]
        if product_id is not None:
            transactions = [
                transaction
                for transaction in transactions
                if transaction.product_id == product_id
            ]
        if category_id is not None:
            transactions = [
                transaction
                for transaction in transactions
                if transaction.product.category_id == category_id
            ]
        if source is not None:
            transactions = [
                transaction
                for transaction in transactions
                if transaction.source == source
            ]
        if channel is not None:
            transactions = [
                transaction
                for transaction in transactions
                if transaction.channel == channel
            ]
        if date_from is not None:
            transactions = [
                transaction
                for transaction in transactions
                if transaction.sale_date >= date_from
            ]
        if date_to is not None:
            transactions = [
                transaction
                for transaction in transactions
                if transaction.sale_date <= date_to
            ]
        if search:
            search_value = search.casefold()
            transactions = [
                transaction
                for transaction in transactions
                if search_value in transaction.product.name.casefold()
                or search_value in transaction.product.normalized_sku.casefold()
                or search_value in (transaction.customer_name or "").casefold()
                or search_value in (transaction.channel or "").casefold()
                or search_value in (transaction.notes or "").casefold()
            ]

        total = len(transactions)
        transactions.sort(
            key=lambda transaction: _sales_transaction_sort_value(
                transaction,
                sort_by,
            ),
            reverse=sort_order == "desc",
        )
        return transactions[offset : offset + limit], total

    async def update_transaction(
        self,
        transaction: FakeSalesTransaction,
        values: dict[str, object],
    ) -> FakeSalesTransaction:
        from app.shared.utils import utc_now

        for field, value in values.items():
            if field in {"quantity", "unit_price", "total_amount"}:
                value = None if value is None else _decimal_value(value)
            setattr(transaction, field, value)
        if "product_id" in values:
            transaction.product = await self.get_product_for_user(
                user_id=transaction.user_id,
                product_id=transaction.product_id,
            )
        transaction.updated_at = utc_now()
        return transaction

    async def soft_delete_transaction(
        self,
        transaction: FakeSalesTransaction,
        *,
        deleted_reason: str | None,
    ) -> FakeSalesTransaction:
        from app.shared.utils import utc_now

        now = utc_now()
        transaction.deleted_at = now
        transaction.deleted_reason = deleted_reason
        transaction.updated_at = now
        return transaction

    async def get_sales_summary_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> dict[str, object]:
        transactions = _sales_transactions_for_aggregate(
            self.transactions_by_id.values(),
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        total_transactions = len(transactions)
        total_quantity = sum(
            (transaction.quantity for transaction in transactions),
            Decimal("0.000"),
        )
        total_amount = sum(
            (
                transaction.total_amount or Decimal("0.00")
                for transaction in transactions
            ),
            Decimal("0.00"),
        )
        average_amount = (
            total_amount / Decimal(total_transactions)
            if total_transactions
            else Decimal("0.00")
        )
        return {
            "total_transactions": total_transactions,
            "total_quantity_sold": total_quantity,
            "total_sales_amount": total_amount,
            "unique_products_sold": len(
                {transaction.product_id for transaction in transactions}
            ),
            "average_transaction_amount": average_amount,
            "date_from": date_from,
            "date_to": date_to,
        }

    async def get_sales_trends_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
        interval: str,
    ) -> list[dict[str, object]]:
        transactions = _sales_transactions_for_aggregate(
            self.transactions_by_id.values(),
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        grouped: dict[date, list[FakeSalesTransaction]] = {}
        for transaction in transactions:
            grouped.setdefault(
                _sales_period_start(transaction.sale_date, interval),
                [],
            ).append(transaction)

        points: list[dict[str, object]] = []
        for period_start, period_transactions in sorted(grouped.items()):
            points.append(
                {
                    "period_start": period_start,
                    "total_quantity": sum(
                        (
                            transaction.quantity
                            for transaction in period_transactions
                        ),
                        Decimal("0.000"),
                    ),
                    "total_amount": sum(
                        (
                            transaction.total_amount or Decimal("0.00")
                            for transaction in period_transactions
                        ),
                        Decimal("0.00"),
                    ),
                    "transaction_count": len(period_transactions),
                }
            )
        return points

    async def get_product_sales_summary_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date | None,
        date_to: date | None,
    ) -> list[dict[str, object]]:
        transactions = _sales_transactions_for_aggregate(
            self.transactions_by_id.values(),
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )
        grouped: dict[UUID, list[FakeSalesTransaction]] = {}
        for transaction in transactions:
            grouped.setdefault(transaction.product_id, []).append(transaction)

        summaries: list[dict[str, object]] = []
        for product_id, product_transactions in grouped.items():
            product = product_transactions[0].product
            summaries.append(
                {
                    "product_id": product_id,
                    "product_name": product.name,
                    "sku": product.sku,
                    "total_quantity": sum(
                        (
                            transaction.quantity
                            for transaction in product_transactions
                        ),
                        Decimal("0.000"),
                    ),
                    "total_amount": sum(
                        (
                            transaction.total_amount or Decimal("0.00")
                            for transaction in product_transactions
                        ),
                        Decimal("0.00"),
                    ),
                    "transaction_count": len(product_transactions),
                }
            )
        summaries.sort(key=lambda summary: summary["total_quantity"], reverse=True)
        return summaries

    async def get_products_by_sku_for_user(
        self,
        *,
        user_id: UUID,
        normalized_skus: set[str],
    ) -> dict[str, FakeProduct]:
        products: dict[str, FakeProduct] = {}
        for sku in normalized_skus:
            product = await self.product_repository.get_product_by_sku_for_user(
                user_id=user_id,
                normalized_sku=sku,
            )
            if product is not None:
                products[sku] = product
        return products

    async def file_hash_exists_for_user(self, *, user_id: UUID, file_hash: str) -> bool:
        return any(
            batch.user_id == user_id and batch.file_hash == file_hash
            for batch in self.batches_by_id.values()
        )

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeForecastRunRepository:
    def __init__(
        self,
        *,
        product_repository: FakeProductRepository,
        sales_repository: FakeSalesRepository,
        inventory_repository: FakeInventoryRepository | None = None,
    ) -> None:
        self.product_repository = product_repository
        self.sales_repository = sales_repository
        self.inventory_repository = inventory_repository
        self.runs_by_id: dict[UUID, FakeForecastRun] = {}
        self.predictions_by_id: dict[UUID, FakeForecastPrediction] = {}
        self.metrics_by_id: dict[UUID, FakeForecastMetric] = {}

    async def create_forecast_run(
        self,
        *,
        user_id: UUID,
        values: dict[str, object],
    ) -> FakeForecastRun:
        from app.shared.utils import utc_now

        now = utc_now()
        run = FakeForecastRun(
            id=uuid4(),
            user_id=user_id,
            horizon_days=int(values["horizon_days"]),
            status=str(values["status"]),
            requested_at=values.get("requested_at") or now,
            started_at=values.get("started_at"),
            completed_at=values.get("completed_at"),
            failed_at=values.get("failed_at"),
            cancelled_at=values.get("cancelled_at"),
            failure_reason=values.get("failure_reason"),
            total_products=int(values.get("total_products", 0)),
            total_sales_records=int(values.get("total_sales_records", 0)),
            run_metadata=values.get("run_metadata"),
            created_at=now,
            updated_at=now,
        )
        self.runs_by_id[run.id] = run
        return run

    async def get_forecast_run_for_user(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> FakeForecastRun | None:
        run = self.runs_by_id.get(run_id)
        if run is None or run.user_id != user_id:
            return None
        return run

    async def list_forecast_runs_for_user(
        self,
        *,
        user_id: UUID,
        status: str | None,
        horizon_days: int | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[FakeForecastRun], int]:
        runs = [run for run in self.runs_by_id.values() if run.user_id == user_id]
        if status is not None:
            runs = [run for run in runs if run.status == status]
        if horizon_days is not None:
            runs = [run for run in runs if run.horizon_days == horizon_days]
        if date_from is not None:
            runs = [run for run in runs if run.requested_at >= date_from]
        if date_to is not None:
            runs = [run for run in runs if run.requested_at <= date_to]
        runs.sort(
            key=lambda run: getattr(run, sort_by),
            reverse=sort_order == "desc",
        )
        total = len(runs)
        return runs[offset : offset + limit], total

    async def update_forecast_run_status(
        self,
        run: FakeForecastRun,
        values: dict[str, object],
    ) -> FakeForecastRun:
        from app.shared.utils import utc_now

        for field, value in values.items():
            setattr(run, field, value)
        run.updated_at = utc_now()
        return run

    async def count_user_active_products(self, *, user_id: UUID) -> int:
        return sum(
            1
            for product in self.product_repository.products_by_id.values()
            if product.user_id == user_id and product.is_active
        )

    async def count_user_sales_transactions(self, *, user_id: UUID) -> int:
        return sum(
            1
            for transaction in self.sales_repository.transactions_by_id.values()
            if transaction.user_id == user_id and transaction.deleted_at is None
        )

    async def get_user_sales_date_span(
        self,
        *,
        user_id: UUID,
    ) -> tuple[date | None, date | None]:
        dates = [
            transaction.sale_date
            for transaction in self.sales_repository.transactions_by_id.values()
            if transaction.user_id == user_id and transaction.deleted_at is None
        ]
        if not dates:
            return None, None
        return min(dates), max(dates)

    async def get_active_products_for_user(self, *, user_id: UUID) -> list[FakeProduct]:
        products = [
            product
            for product in self.product_repository.products_by_id.values()
            if product.user_id == user_id and product.is_active
        ]
        products.sort(key=lambda product: product.normalized_sku)
        return products

    async def get_sales_transactions_for_forecasting(
        self,
        *,
        user_id: UUID,
    ) -> list[FakeSalesTransaction]:
        transactions = [
            transaction
            for transaction in self.sales_repository.transactions_by_id.values()
            if transaction.user_id == user_id and transaction.deleted_at is None
        ]
        transactions.sort(key=lambda row: (row.sale_date, str(row.product_id)))
        return transactions

    async def delete_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> None:
        self.predictions_by_id = {
            prediction_id: prediction
            for prediction_id, prediction in self.predictions_by_id.items()
            if not (
                prediction.user_id == user_id
                and prediction.forecast_run_id == forecast_run_id
            )
        }
        self.metrics_by_id = {
            metric_id: metric
            for metric_id, metric in self.metrics_by_id.items()
            if not (
                metric.user_id == user_id and metric.forecast_run_id == forecast_run_id
            )
        }

    async def bulk_create_forecast_predictions(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        rows: list[dict[str, object]],
    ) -> list[FakeForecastPrediction]:
        from app.shared.utils import utc_now

        now = utc_now()
        predictions: list[FakeForecastPrediction] = []
        for row in rows:
            prediction = FakeForecastPrediction(
                id=uuid4(),
                user_id=user_id,
                forecast_run_id=forecast_run_id,
                product_id=row["product_id"],
                forecast_date=row["forecast_date"],
                predicted_demand=row["predicted_demand"],
                model_name=str(row["model_name"]),
                created_at=now,
            )
            self.predictions_by_id[prediction.id] = prediction
            predictions.append(prediction)
        return predictions

    async def create_forecast_metrics(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        values: dict[str, object],
    ) -> FakeForecastMetric:
        from app.shared.utils import utc_now

        metric = FakeForecastMetric(
            id=uuid4(),
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            model_name=str(values["model_name"]),
            mae=values["mae"],
            rmse=values["rmse"],
            mape=values["mape"],
            training_rows=int(values["training_rows"]),
            validation_rows=int(values["validation_rows"]),
            total_products=int(values["total_products"]),
            fallback_products=int(values["fallback_products"]),
            created_at=utc_now(),
        )
        self.metrics_by_id[metric.id] = metric
        return metric

    async def count_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> int:
        return sum(
            1
            for prediction in self.predictions_by_id.values()
            if prediction.user_id == user_id
            and prediction.forecast_run_id == forecast_run_id
        )

    async def get_prediction_date_range(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> tuple[date | None, date | None]:
        dates = [
            prediction.forecast_date
            for prediction in self.predictions_by_id.values()
            if prediction.user_id == user_id
            and prediction.forecast_run_id == forecast_run_id
        ]
        if not dates:
            return None, None
        return min(dates), max(dates)

    async def get_total_predicted_demand(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> Decimal:
        return sum(
            (
                prediction.predicted_demand
                for prediction in self.predictions_by_id.values()
                if prediction.user_id == user_id
                and prediction.forecast_run_id == forecast_run_id
            ),
            Decimal("0.000"),
        )

    async def list_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[dict[str, object]], int]:
        rows = [
            self._prediction_to_result_row(prediction)
            for prediction in self._filtered_predictions(
                user_id=user_id,
                forecast_run_id=forecast_run_id,
                product_id=product_id,
                category_id=category_id,
                date_from=date_from,
                date_to=date_to,
                search=search,
            )
        ]
        rows.sort(
            key=lambda row: self._result_sort_value(row, sort_by),
            reverse=sort_order == "desc",
        )
        total = len(rows)
        return rows[offset : offset + limit], total

    async def get_metrics_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> FakeForecastMetric | None:
        metrics = [
            metric
            for metric in self.metrics_by_id.values()
            if metric.user_id == user_id and metric.forecast_run_id == forecast_run_id
        ]
        if not metrics:
            return None
        metrics.sort(key=lambda metric: metric.created_at, reverse=True)
        return metrics[0]

    async def get_chart_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        interval: str,
    ) -> list[dict[str, object]]:
        totals: dict[date, Decimal] = {}
        for prediction in self._filtered_predictions(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=None,
            date_from=date_from,
            date_to=date_to,
            search=None,
        ):
            period_start = _sales_period_start(prediction.forecast_date, interval)
            totals[period_start] = totals.get(period_start, Decimal("0.000")) + (
                prediction.predicted_demand
            )
        return [
            {"period_start": period, "predicted_demand": total}
            for period, total in sorted(totals.items())
        ]

    async def get_actual_sales_for_forecast_dates(
        self,
        *,
        user_id: UUID,
        product_id: UUID | None,
        date_from: date,
        date_to: date,
        interval: str,
    ) -> list[dict[str, object]]:
        totals: dict[date, Decimal] = {}
        for transaction in self.sales_repository.transactions_by_id.values():
            if transaction.user_id != user_id or transaction.deleted_at is not None:
                continue
            if product_id is not None and transaction.product_id != product_id:
                continue
            if transaction.sale_date < date_from or transaction.sale_date > date_to:
                continue
            period_start = _sales_period_start(transaction.sale_date, interval)
            totals[period_start] = totals.get(period_start, Decimal("0.000")) + (
                transaction.quantity
            )
        return [
            {"period_start": period, "actual_quantity": total}
            for period, total in sorted(totals.items())
        ]

    async def get_product_forecast_detail(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID,
    ) -> list[dict[str, object]]:
        rows, _ = await self.list_predictions_for_run(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=None,
            date_from=None,
            date_to=None,
            search=None,
            limit=1000,
            offset=0,
            sort_by="forecast_date",
            sort_order="asc",
        )
        return rows

    async def get_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> FakeProduct | None:
        product = self.product_repository.products_by_id.get(product_id)
        if product is None or product.user_id != user_id:
            return None
        return product

    async def get_inventory_snapshot_for_products(
        self,
        *,
        user_id: UUID,
        product_ids: set[UUID],
    ) -> dict[UUID, FakeInventoryItem]:
        if self.inventory_repository is None:
            return {}
        return {
            item.product_id: item
            for item in self.inventory_repository.items_by_id.values()
            if item.user_id == user_id and item.product_id in product_ids
        }

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def _filtered_predictions(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        category_id: UUID | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
    ) -> list[FakeForecastPrediction]:
        predictions = [
            prediction
            for prediction in self.predictions_by_id.values()
            if prediction.user_id == user_id
            and prediction.forecast_run_id == forecast_run_id
        ]
        if product_id is not None:
            predictions = [
                prediction
                for prediction in predictions
                if prediction.product_id == product_id
            ]
        if date_from is not None:
            predictions = [
                prediction
                for prediction in predictions
                if prediction.forecast_date >= date_from
            ]
        if date_to is not None:
            predictions = [
                prediction
                for prediction in predictions
                if prediction.forecast_date <= date_to
            ]
        if category_id is not None:
            predictions = [
                prediction
                for prediction in predictions
                if self.product_repository.products_by_id[
                    prediction.product_id
                ].category_id
                == category_id
            ]
        if search:
            needle = search.strip().lower()
            if needle:
                predictions = [
                    prediction
                    for prediction in predictions
                    if self._prediction_matches_search(prediction, needle)
                ]
        return predictions

    def _prediction_matches_search(
        self,
        prediction: FakeForecastPrediction,
        needle: str,
    ) -> bool:
        product = self.product_repository.products_by_id[prediction.product_id]
        return (
            needle in product.name.lower()
            or needle in product.sku.lower()
            or needle in product.normalized_sku.lower()
            or needle in prediction.model_name.lower()
        )

    def _prediction_to_result_row(
        self,
        prediction: FakeForecastPrediction,
    ) -> dict[str, object]:
        product = self.product_repository.products_by_id[prediction.product_id]
        category = (
            self.product_repository.categories_by_id.get(product.category_id)
            if product.category_id is not None
            else None
        )
        inventory_item = None
        if self.inventory_repository is not None:
            inventory_item = next(
                (
                    item
                    for item in self.inventory_repository.items_by_id.values()
                    if item.user_id == prediction.user_id
                    and item.product_id == prediction.product_id
                ),
                None,
            )
        return {
            "product_id": prediction.product_id,
            "product_name": product.name,
            "sku": product.sku,
            "category_id": product.category_id,
            "category_name": category.name if category else None,
            "unit": product.unit,
            "current_stock": inventory_item.current_stock if inventory_item else None,
            "minimum_stock": inventory_item.minimum_stock if inventory_item else None,
            "safety_stock": inventory_item.safety_stock if inventory_item else None,
            "forecast_date": prediction.forecast_date,
            "predicted_demand": prediction.predicted_demand,
            "model_name": prediction.model_name,
        }

    def _result_sort_value(self, row: dict[str, object], sort_by: str) -> object:
        if sort_by == "product_name":
            return str(row["product_name"]).lower()
        if sort_by == "sku":
            return str(row["sku"]).upper()
        return row[sort_by]


class FakeReorderRecommendationRepository:
    def __init__(
        self,
        *,
        product_repository: FakeProductRepository,
        inventory_repository: FakeInventoryRepository,
        forecast_repository: FakeForecastRunRepository,
    ) -> None:
        self.product_repository = product_repository
        self.inventory_repository = inventory_repository
        self.forecast_repository = forecast_repository
        self.recommendations_by_id: dict[UUID, FakeReorderRecommendation] = {}

    async def get_forecast_run_for_user(
        self,
        *,
        user_id: UUID,
        run_id: UUID,
    ) -> FakeForecastRun | None:
        return await self.forecast_repository.get_forecast_run_for_user(
            user_id=user_id,
            run_id=run_id,
        )

    async def count_predictions_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> int:
        return await self.forecast_repository.count_predictions_for_run(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        )

    async def get_predictions_grouped_by_product_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> list[dict[str, object]]:
        totals: dict[UUID, Decimal] = {}
        for prediction in self.forecast_repository.predictions_by_id.values():
            if (
                prediction.user_id == user_id
                and prediction.forecast_run_id == forecast_run_id
            ):
                totals[prediction.product_id] = totals.get(
                    prediction.product_id,
                    Decimal("0.000"),
                ) + _decimal_value(prediction.predicted_demand)
        return [
            {"product_id": product_id, "predicted_demand": predicted_demand}
            for product_id, predicted_demand in sorted(
                totals.items(),
                key=lambda row: str(row[0]),
            )
        ]

    async def get_inventory_items_for_products(
        self,
        *,
        user_id: UUID,
        product_ids: set[UUID],
    ) -> dict[UUID, FakeInventoryItem]:
        return {
            item.product_id: item
            for item in self.inventory_repository.items_by_id.values()
            if item.user_id == user_id and item.product_id in product_ids
        }

    async def get_products_for_user_by_ids(
        self,
        *,
        user_id: UUID,
        product_ids: set[UUID],
    ) -> dict[UUID, FakeProduct]:
        return {
            product.id: product
            for product in self.product_repository.products_by_id.values()
            if product.user_id == user_id and product.id in product_ids
        }

    async def count_existing_recommendations_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> int:
        return sum(
            1
            for recommendation in self.recommendations_by_id.values()
            if recommendation.user_id == user_id
            and recommendation.forecast_run_id == forecast_run_id
        )

    async def delete_recommendations_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> None:
        self.recommendations_by_id = {
            recommendation_id: recommendation
            for recommendation_id, recommendation in self.recommendations_by_id.items()
            if not (
                recommendation.user_id == user_id
                and recommendation.forecast_run_id == forecast_run_id
            )
        }

    async def bulk_create_recommendations(
        self,
        *,
        user_id: UUID,
        rows: list[dict[str, object]],
    ) -> list[FakeReorderRecommendation]:
        from app.shared.utils import utc_now

        recommendations: list[FakeReorderRecommendation] = []
        now = utc_now()
        for row in rows:
            recommendation = FakeReorderRecommendation(
                id=uuid4(),
                user_id=user_id,
                forecast_run_id=row["forecast_run_id"],
                product_id=row["product_id"],
                predicted_demand=_decimal_value(row["predicted_demand"]),
                current_stock=_decimal_value(row["current_stock"]),
                minimum_stock=_decimal_value(row["minimum_stock"]),
                safety_stock=_decimal_value(row["safety_stock"]),
                required_stock=_decimal_value(row["required_stock"]),
                reorder_quantity=_decimal_value(row["reorder_quantity"]),
                stock_gap=_decimal_value(row["stock_gap"]),
                risk_level=str(row["risk_level"]),
                recommended_action=str(row["recommended_action"]),
                reason=row.get("reason"),
                status=str(row["status"]),
                generated_at=row["generated_at"],
                acknowledged_at=None,
                dismissed_at=None,
                created_at=now,
                updated_at=now,
            )
            self.recommendations_by_id[recommendation.id] = recommendation
            recommendations.append(recommendation)
        return recommendations

    async def list_recommendations_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        product_id: UUID | None,
        category_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        action: str | None,
        generated_from: datetime | None,
        generated_to: datetime | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[dict[str, object]], int]:
        rows = [
            self._recommendation_to_row(recommendation)
            for recommendation in self.recommendations_by_id.values()
            if recommendation.user_id == user_id
        ]
        rows = self._filter_rows(
            rows,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=category_id,
            risk_level=risk_level,
            status=status,
            action=action,
            generated_from=generated_from,
            generated_to=generated_to,
            search=search,
        )
        rows.sort(
            key=lambda row: self._recommendation_sort_value(row, sort_by),
            reverse=sort_order == "desc",
        )
        total = len(rows)
        return rows[offset : offset + limit], total

    async def list_recommendations_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
        product_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> tuple[list[dict[str, object]], int]:
        return await self.list_recommendations_for_user(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=product_id,
            category_id=None,
            risk_level=risk_level,
            status=status,
            action=None,
            generated_from=None,
            generated_to=None,
            search=None,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def get_recommendation_for_user(
        self,
        *,
        user_id: UUID,
        recommendation_id: UUID,
    ) -> dict[str, object] | None:
        recommendation = self.recommendations_by_id.get(recommendation_id)
        if recommendation is None or recommendation.user_id != user_id:
            return None
        return self._recommendation_to_row(recommendation)

    async def get_recommendation_model_for_user(
        self,
        *,
        user_id: UUID,
        recommendation_id: UUID,
    ) -> FakeReorderRecommendation | None:
        recommendation = self.recommendations_by_id.get(recommendation_id)
        if recommendation is None or recommendation.user_id != user_id:
            return None
        return recommendation

    async def get_summary_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> dict[str, object] | None:
        rows, total = await self.list_recommendations_for_run(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
            product_id=None,
            risk_level=None,
            status=None,
            limit=10_000,
            offset=0,
            sort_by="reorder_quantity",
            sort_order="desc",
        )
        if total == 0:
            return None
        top_reorder_products = sorted(
            rows,
            key=lambda row: (row["reorder_quantity"], row["predicted_demand"]),
            reverse=True,
        )[:5]
        return {
            "forecast_run_id": forecast_run_id,
            "total_recommendations": total,
            "total_reorder_quantity": sum(
                (row["reorder_quantity"] for row in rows),
                Decimal("0.000"),
            ),
            "critical_count": sum(1 for row in rows if row["risk_level"] == "critical"),
            "high_count": sum(1 for row in rows if row["risk_level"] == "high"),
            "medium_count": sum(1 for row in rows if row["risk_level"] == "medium"),
            "low_count": sum(1 for row in rows if row["risk_level"] == "low"),
            "overstocked_count": sum(
                1 for row in rows if row["risk_level"] == "overstocked"
            ),
            "total_predicted_demand": sum(
                (row["predicted_demand"] for row in rows),
                Decimal("0.000"),
            ),
            "total_current_stock": sum(
                (row["current_stock"] for row in rows),
                Decimal("0.000"),
            ),
            "latest_generated_at": max(row["generated_at"] for row in rows),
            "top_reorder_products": top_reorder_products,
        }

    async def update_recommendation_status(
        self,
        recommendation: FakeReorderRecommendation,
        *,
        status: str,
        acknowledged_at: datetime | None,
        dismissed_at: datetime | None,
    ) -> FakeReorderRecommendation:
        from app.shared.utils import utc_now

        recommendation.status = status
        if acknowledged_at is not None:
            recommendation.acknowledged_at = acknowledged_at
        if dismissed_at is not None:
            recommendation.dismissed_at = dismissed_at
        recommendation.updated_at = utc_now()
        return recommendation

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    def _filter_rows(
        self,
        rows: list[dict[str, object]],
        *,
        forecast_run_id: UUID | None,
        product_id: UUID | None,
        category_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        action: str | None,
        generated_from: datetime | None,
        generated_to: datetime | None,
        search: str | None,
    ) -> list[dict[str, object]]:
        if forecast_run_id is not None:
            rows = [row for row in rows if row["forecast_run_id"] == forecast_run_id]
        if product_id is not None:
            rows = [row for row in rows if row["product_id"] == product_id]
        if category_id is not None:
            rows = [row for row in rows if row["category_id"] == category_id]
        if risk_level is not None:
            rows = [row for row in rows if row["risk_level"] == risk_level]
        if status is not None:
            rows = [row for row in rows if row["status"] == status]
        if action is not None:
            rows = [row for row in rows if row["recommended_action"] == action]
        if generated_from is not None:
            rows = [row for row in rows if row["generated_at"] >= generated_from]
        if generated_to is not None:
            rows = [row for row in rows if row["generated_at"] <= generated_to]
        if search:
            needle = search.strip().casefold()
            if needle:
                rows = [
                    row
                    for row in rows
                    if needle in str(row["product_name"]).casefold()
                    or needle in str(row["sku"]).casefold()
                    or needle in str(row["risk_level"]).casefold()
                    or needle in str(row["recommended_action"]).casefold()
                ]
        return rows

    def _recommendation_to_row(
        self,
        recommendation: FakeReorderRecommendation,
    ) -> dict[str, object]:
        product = self.product_repository.products_by_id[recommendation.product_id]
        category = (
            self.product_repository.categories_by_id.get(product.category_id)
            if product.category_id is not None
            else None
        )
        run = self.forecast_repository.runs_by_id[recommendation.forecast_run_id]
        return {
            "id": recommendation.id,
            "forecast_run_id": recommendation.forecast_run_id,
            "product_id": recommendation.product_id,
            "product_name": product.name,
            "sku": product.sku,
            "category_id": product.category_id,
            "category_name": category.name if category else None,
            "unit": product.unit,
            "predicted_demand": recommendation.predicted_demand,
            "current_stock": recommendation.current_stock,
            "minimum_stock": recommendation.minimum_stock,
            "safety_stock": recommendation.safety_stock,
            "required_stock": recommendation.required_stock,
            "reorder_quantity": recommendation.reorder_quantity,
            "stock_gap": recommendation.stock_gap,
            "risk_level": recommendation.risk_level,
            "recommended_action": recommendation.recommended_action,
            "reason": recommendation.reason,
            "status": recommendation.status,
            "generated_at": recommendation.generated_at,
            "acknowledged_at": recommendation.acknowledged_at,
            "dismissed_at": recommendation.dismissed_at,
            "created_at": recommendation.created_at,
            "updated_at": recommendation.updated_at,
            "forecast_run": {
                "id": run.id,
                "horizon_days": run.horizon_days,
                "status": run.status,
                "requested_at": run.requested_at,
                "completed_at": run.completed_at,
            },
        }

    def _recommendation_sort_value(
        self,
        row: dict[str, object],
        sort_by: str,
    ) -> object:
        if sort_by == "product_name":
            return str(row["product_name"]).casefold()
        if sort_by == "sku":
            return str(row["sku"]).upper()
        return row[sort_by]


class FakeDashboardAnalyticsRepository:
    def __init__(
        self,
        *,
        product_repository: FakeProductRepository,
        inventory_repository: FakeInventoryRepository,
        sales_repository: FakeSalesRepository,
        forecast_repository: FakeForecastRunRepository,
        recommendation_repository: FakeReorderRecommendationRepository,
    ) -> None:
        self.product_repository = product_repository
        self.inventory_repository = inventory_repository
        self.sales_repository = sales_repository
        self.forecast_repository = forecast_repository
        self.recommendation_repository = recommendation_repository

    async def validate_product_for_user(
        self,
        *,
        user_id: UUID,
        product_id: UUID,
    ) -> bool:
        return (
            await self.product_repository.get_product_by_id_for_user(
                user_id=user_id,
                product_id=product_id,
            )
            is not None
        )

    async def validate_category_for_user(
        self,
        *,
        user_id: UUID,
        category_id: UUID,
    ) -> bool:
        return (
            await self.product_repository.get_category_by_id_for_user(
                user_id=user_id,
                category_id=category_id,
            )
            is not None
        )

    async def validate_forecast_run_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID,
    ) -> bool:
        return (
            await self.forecast_repository.get_forecast_run_for_user(
                user_id=user_id,
                run_id=forecast_run_id,
            )
            is not None
        )

    async def get_product_counts_for_user(self, *, user_id: UUID) -> dict[str, int]:
        products = [
            product
            for product in self.product_repository.products_by_id.values()
            if product.user_id == user_id
        ]
        return {
            "total_products": len(products),
            "active_products": sum(1 for product in products if product.is_active),
        }

    async def get_sales_counts_for_user(self, *, user_id: UUID) -> dict[str, int]:
        return {
            "total_sales_records": len(
                [
                    transaction
                    for transaction in self.sales_repository.transactions_by_id.values()
                    if transaction.user_id == user_id
                    and transaction.deleted_at is None
                ]
            )
        }

    async def get_inventory_counts_for_user(self, *, user_id: UUID) -> dict[str, int]:
        from app.modules.inventory.domain.stock import calculate_stock_status

        statuses = [
            calculate_stock_status(
                current_stock=item.current_stock,
                minimum_stock=item.minimum_stock,
                is_active=item.is_active,
            )
            for item in self.inventory_repository.items_by_id.values()
            if item.user_id == user_id
        ]
        return {
            "total_inventory_items": len(statuses),
            "low_stock_count": statuses.count("low_stock"),
            "out_of_stock_count": statuses.count("out_of_stock"),
            "healthy_stock_count": statuses.count("in_stock"),
            "inactive_inventory_count": statuses.count("inactive"),
        }

    async def get_low_stock_preview_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [
            self._inventory_preview(item)
            for item in self.inventory_repository.items_by_id.values()
            if item.user_id == user_id
            and self._stock_status(item) == "low_stock"
        ]
        rows.sort(key=lambda row: (row["current_stock"], row["sku"]))
        return rows[:limit]

    async def get_out_of_stock_preview_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [
            self._inventory_preview(item)
            for item in self.inventory_repository.items_by_id.values()
            if item.user_id == user_id
            and self._stock_status(item) == "out_of_stock"
        ]
        rows.sort(key=lambda row: row["sku"])
        return rows[:limit]

    async def get_demand_trends_for_user(
        self,
        *,
        user_id: UUID,
        date_from: date,
        date_to: date,
        interval: str,
        product_id: UUID | None,
        category_id: UUID | None,
    ) -> list[dict[str, object]]:
        totals: dict[date, dict[str, object]] = {}
        for transaction in self.sales_repository.transactions_by_id.values():
            if transaction.user_id != user_id or transaction.deleted_at is not None:
                continue
            if transaction.sale_date < date_from or transaction.sale_date > date_to:
                continue
            if product_id is not None and transaction.product_id != product_id:
                continue
            if (
                category_id is not None
                and transaction.product.category_id != category_id
            ):
                continue
            period = _sales_period_start(transaction.sale_date, interval)
            row = totals.setdefault(
                period,
                {
                    "period": period,
                    "total_quantity_sold": Decimal("0.000"),
                    "total_sales_amount": Decimal("0.00"),
                    "transaction_count": 0,
                },
            )
            row["total_quantity_sold"] += transaction.quantity
            row["total_sales_amount"] += transaction.total_amount or Decimal("0.00")
            row["transaction_count"] += 1
        return [totals[period] for period in sorted(totals)]

    async def get_latest_forecast_overview_for_user(
        self,
        *,
        user_id: UUID,
    ) -> dict[str, object]:
        runs = [
            run
            for run in self.forecast_repository.runs_by_id.values()
            if run.user_id == user_id
        ]
        latest_run = max(runs, key=lambda run: run.requested_at, default=None)
        completed_runs = [run for run in runs if run.status == "completed"]
        latest_completed = max(
            completed_runs,
            key=lambda run: run.completed_at or run.updated_at,
            default=None,
        )
        return {
            "latest_forecast_run": self._forecast_run_dict(latest_run),
            "latest_completed_forecast_run": self._forecast_run_dict(
                latest_completed
            ),
        }

    async def get_forecast_run_counts_for_user(
        self,
        *,
        user_id: UUID,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for run in self.forecast_repository.runs_by_id.values():
            if run.user_id == user_id:
                counts[run.status] = counts.get(run.status, 0) + 1
        return counts

    async def get_latest_forecast_metrics_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
    ) -> dict[str, object] | None:
        if forecast_run_id is None:
            return None
        metrics = [
            metric
            for metric in self.forecast_repository.metrics_by_id.values()
            if metric.user_id == user_id and metric.forecast_run_id == forecast_run_id
        ]
        metric = max(metrics, key=lambda row: row.created_at, default=None)
        if metric is None:
            return None
        return {
            "model_name": metric.model_name,
            "mae": metric.mae,
            "rmse": metric.rmse,
            "mape": metric.mape,
            "training_rows": metric.training_rows,
            "validation_rows": metric.validation_rows,
            "total_products": metric.total_products,
            "fallback_products": metric.fallback_products,
            "created_at": metric.created_at,
        }

    async def get_prediction_summary_for_run(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
    ) -> dict[str, object]:
        predictions = [
            prediction
            for prediction in self.forecast_repository.predictions_by_id.values()
            if prediction.user_id == user_id
            and prediction.forecast_run_id == forecast_run_id
        ]
        if not predictions:
            return {
                "total_predictions_in_latest_run": 0,
                "forecast_date_range": {"date_from": None, "date_to": None},
                "total_predicted_demand": Decimal("0.000"),
            }
        dates = [prediction.forecast_date for prediction in predictions]
        return {
            "total_predictions_in_latest_run": len(predictions),
            "forecast_date_range": {
                "date_from": min(dates),
                "date_to": max(dates),
            },
            "total_predicted_demand": sum(
                (prediction.predicted_demand for prediction in predictions),
                Decimal("0.000"),
            ),
        }

    async def get_reorder_alert_counts_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
    ) -> dict[str, object]:
        recommendations = self._recommendations(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        )
        return {
            "critical_count": _count_attr(recommendations, "risk_level", "critical"),
            "high_count": _count_attr(recommendations, "risk_level", "high"),
            "medium_count": _count_attr(recommendations, "risk_level", "medium"),
            "low_count": _count_attr(recommendations, "risk_level", "low"),
            "overstocked_count": _count_attr(
                recommendations,
                "risk_level",
                "overstocked",
            ),
            "open_count": _count_attr(recommendations, "status", "open"),
            "acknowledged_count": _count_attr(
                recommendations,
                "status",
                "acknowledged",
            ),
            "dismissed_count": _count_attr(recommendations, "status", "dismissed"),
            "total_reorder_quantity": sum(
                (row.reorder_quantity for row in recommendations),
                Decimal("0.000"),
            ),
        }

    async def get_top_reorder_items_for_user(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
        risk_level: str | None,
        status: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        recommendations = self._recommendations(
            user_id=user_id,
            forecast_run_id=forecast_run_id,
        )
        if risk_level is not None:
            recommendations = [
                row for row in recommendations if row.risk_level == risk_level
            ]
        if status is not None:
            recommendations = [row for row in recommendations if row.status == status]
        recommendations.sort(
            key=lambda row: (row.reorder_quantity, row.generated_at),
            reverse=True,
        )
        return [self._recommendation_alert(row) for row in recommendations[:limit]]

    async def get_recent_sales_uploads_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [
            batch
            for batch in self.sales_repository.batches_by_id.values()
            if batch.user_id == user_id
        ]
        rows.sort(key=lambda row: row.completed_at or row.started_at, reverse=True)
        return [
            {
                "id": row.id,
                "filename": row.original_filename,
                "status": row.status,
                "accepted_rows": row.accepted_rows,
                "rejected_rows": row.rejected_rows,
                "occurred_at": row.completed_at or row.started_at,
            }
            for row in rows[:limit]
        ]

    async def get_recent_forecast_runs_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [
            run
            for run in self.forecast_repository.runs_by_id.values()
            if run.user_id == user_id
        ]
        rows.sort(key=lambda row: row.updated_at, reverse=True)
        return [
            {
                "id": row.id,
                "status": row.status,
                "horizon_days": row.horizon_days,
                "occurred_at": row.updated_at,
            }
            for row in rows[:limit]
        ]

    async def get_recent_stock_movements_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [
            movement
            for movement in self.inventory_repository.movements_by_id.values()
            if movement.user_id == user_id
        ]
        rows.sort(key=lambda row: row.occurred_at, reverse=True)
        return [
            {
                "id": row.id,
                "product_id": row.product_id,
                "product_name": self.product_repository.products_by_id[
                    row.product_id
                ].name,
                "sku": self.product_repository.products_by_id[row.product_id].sku,
                "movement_type": row.movement_type,
                "quantity_delta": row.quantity_delta,
                "occurred_at": row.occurred_at,
            }
            for row in rows[:limit]
        ]

    async def get_recent_recommendations_for_user(
        self,
        *,
        user_id: UUID,
        limit: int,
    ) -> list[dict[str, object]]:
        rows = [
            row
            for row in self.recommendation_repository.recommendations_by_id.values()
            if row.user_id == user_id
        ]
        rows.sort(key=lambda row: row.generated_at, reverse=True)
        return [
            {
                "id": row.id,
                "forecast_run_id": row.forecast_run_id,
                "product_id": row.product_id,
                "product_name": self.product_repository.products_by_id[
                    row.product_id
                ].name,
                "sku": self.product_repository.products_by_id[row.product_id].sku,
                "risk_level": row.risk_level,
                "reorder_quantity": row.reorder_quantity,
                "status": row.status,
                "occurred_at": row.generated_at,
            }
            for row in rows[:limit]
        ]

    def _stock_status(self, item: FakeInventoryItem) -> str:
        from app.modules.inventory.domain.stock import calculate_stock_status

        return calculate_stock_status(
            current_stock=item.current_stock,
            minimum_stock=item.minimum_stock,
            is_active=item.is_active,
        )

    def _inventory_preview(self, item: FakeInventoryItem) -> dict[str, object]:
        product = item.product
        category = (
            self.product_repository.categories_by_id.get(product.category_id)
            if product.category_id is not None
            else None
        )
        return {
            "product_id": item.product_id,
            "product_name": product.name,
            "sku": product.sku,
            "category_id": product.category_id,
            "category_name": category.name if category else None,
            "current_stock": item.current_stock,
            "minimum_stock": item.minimum_stock,
            "safety_stock": item.safety_stock,
            "stock_status": self._stock_status(item),
        }

    def _forecast_run_dict(
        self,
        run: FakeForecastRun | None,
    ) -> dict[str, object] | None:
        if run is None:
            return None
        return {
            "id": run.id,
            "horizon_days": run.horizon_days,
            "status": run.status,
            "requested_at": run.requested_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "failed_at": run.failed_at,
            "cancelled_at": run.cancelled_at,
            "failure_reason": run.failure_reason,
            "total_products": run.total_products,
            "total_sales_records": run.total_sales_records,
        }

    def _recommendations(
        self,
        *,
        user_id: UUID,
        forecast_run_id: UUID | None,
    ) -> list[FakeReorderRecommendation]:
        rows = [
            row
            for row in self.recommendation_repository.recommendations_by_id.values()
            if row.user_id == user_id
        ]
        if forecast_run_id is not None:
            rows = [row for row in rows if row.forecast_run_id == forecast_run_id]
        return rows

    def _recommendation_alert(
        self,
        recommendation: FakeReorderRecommendation,
    ) -> dict[str, object]:
        product = self.product_repository.products_by_id[recommendation.product_id]
        category = (
            self.product_repository.categories_by_id.get(product.category_id)
            if product.category_id is not None
            else None
        )
        return {
            "id": recommendation.id,
            "forecast_run_id": recommendation.forecast_run_id,
            "product_id": recommendation.product_id,
            "product_name": product.name,
            "sku": product.sku,
            "category_id": product.category_id,
            "category_name": category.name if category else None,
            "predicted_demand": recommendation.predicted_demand,
            "current_stock": recommendation.current_stock,
            "required_stock": recommendation.required_stock,
            "reorder_quantity": recommendation.reorder_quantity,
            "risk_level": recommendation.risk_level,
            "recommended_action": recommendation.recommended_action,
            "status": recommendation.status,
            "generated_at": recommendation.generated_at,
        }


def _product_sort_value(product: FakeProduct, sort_by: str) -> object:
    if sort_by == "name":
        return product.normalized_name
    if sort_by == "sku":
        return product.normalized_sku
    return getattr(product, sort_by)


def _category_sort_value(category: FakeProductCategory, sort_by: str) -> object:
    if sort_by == "name":
        return category.normalized_name
    return getattr(category, sort_by)


def _inventory_item_sort_value(item: FakeInventoryItem, sort_by: str) -> object:
    if sort_by == "product_name":
        return item.product.normalized_name
    if sort_by == "sku":
        return item.product.normalized_sku
    return getattr(item, sort_by)


def _sales_transaction_sort_value(
    transaction: FakeSalesTransaction,
    sort_by: str,
) -> object:
    if sort_by == "product_name":
        return transaction.product.normalized_name
    if sort_by == "sku":
        return transaction.product.normalized_sku
    value = getattr(transaction, sort_by)
    if value is None and sort_by in {"unit_price", "total_amount"}:
        return Decimal("-1")
    if value is None:
        return ""
    return value


def _sales_transactions_for_aggregate(
    transactions: object,
    *,
    user_id: UUID,
    date_from: date | None,
    date_to: date | None,
) -> list[FakeSalesTransaction]:
    filtered = [
        transaction
        for transaction in transactions
        if transaction.user_id == user_id and transaction.deleted_at is None
    ]
    if date_from is not None:
        filtered = [
            transaction
            for transaction in filtered
            if transaction.sale_date >= date_from
        ]
    if date_to is not None:
        filtered = [
            transaction for transaction in filtered if transaction.sale_date <= date_to
        ]
    return filtered


def _sales_period_start(value: date, interval: str) -> date:
    if interval == "week":
        return value - timedelta(days=value.weekday())
    if interval == "month":
        return date(value.year, value.month, 1)
    return value


def _decimal_value(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _count_attr(rows: list[object], field_name: str, expected: object) -> int:
    return sum(1 for row in rows if getattr(row, field_name) == expected)


@pytest.fixture
def auth_repository() -> FakeAuthRepository:
    return FakeAuthRepository()


@pytest.fixture
def product_repository() -> FakeProductRepository:
    return FakeProductRepository()


@pytest.fixture
def inventory_repository(product_repository) -> FakeInventoryRepository:
    return FakeInventoryRepository(product_repository=product_repository)


@pytest.fixture
def sales_repository(product_repository) -> FakeSalesRepository:
    return FakeSalesRepository(product_repository=product_repository)


@pytest.fixture
def forecast_repository(
    product_repository,
    inventory_repository,
    sales_repository,
) -> FakeForecastRunRepository:
    return FakeForecastRunRepository(
        product_repository=product_repository,
        inventory_repository=inventory_repository,
        sales_repository=sales_repository,
    )


@pytest.fixture
def recommendation_repository(
    product_repository,
    inventory_repository,
    forecast_repository,
) -> FakeReorderRecommendationRepository:
    return FakeReorderRecommendationRepository(
        product_repository=product_repository,
        inventory_repository=inventory_repository,
        forecast_repository=forecast_repository,
    )


@pytest.fixture
def dashboard_repository(
    product_repository,
    inventory_repository,
    sales_repository,
    forecast_repository,
    recommendation_repository,
) -> FakeDashboardAnalyticsRepository:
    return FakeDashboardAnalyticsRepository(
        product_repository=product_repository,
        inventory_repository=inventory_repository,
        sales_repository=sales_repository,
        forecast_repository=forecast_repository,
        recommendation_repository=recommendation_repository,
    )


@pytest.fixture
async def auth_client(app, auth_repository) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


@pytest.fixture
async def inventory_client(
    app,
    auth_repository,
    product_repository,
    inventory_repository,
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.inventory.api.dependencies import get_inventory_service
    from app.modules.inventory.application.service import InventoryService
    from app.modules.products.api.dependencies import get_product_service
    from app.modules.products.application.service import ProductService
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    async def override_product_service() -> ProductService:
        return ProductService(repository=product_repository)

    async def override_inventory_service() -> InventoryService:
        return InventoryService(repository=inventory_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    app.dependency_overrides[get_product_service] = override_product_service
    app.dependency_overrides[get_inventory_service] = override_inventory_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


@pytest.fixture
async def product_client(
    app,
    auth_repository,
    product_repository,
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.products.api.dependencies import get_product_service
    from app.modules.products.application.service import ProductService
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    async def override_product_service() -> ProductService:
        return ProductService(repository=product_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    app.dependency_overrides[get_product_service] = override_product_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


@pytest.fixture
async def sales_client(
    app,
    auth_repository,
    product_repository,
    sales_repository,
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.products.api.dependencies import get_product_service
    from app.modules.products.application.service import ProductService
    from app.modules.sales.api.dependencies import (
        get_sales_transaction_service,
        get_sales_upload_service,
    )
    from app.modules.sales.application.service import (
        SalesTransactionService,
        SalesUploadService,
    )
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    async def override_product_service() -> ProductService:
        return ProductService(repository=product_repository)

    async def override_sales_upload_service() -> SalesUploadService:
        return SalesUploadService(repository=sales_repository)

    async def override_sales_transaction_service() -> SalesTransactionService:
        return SalesTransactionService(repository=sales_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    app.dependency_overrides[get_product_service] = override_product_service
    app.dependency_overrides[get_sales_upload_service] = override_sales_upload_service
    app.dependency_overrides[get_sales_transaction_service] = (
        override_sales_transaction_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


@pytest.fixture
async def forecast_client(
    app,
    auth_repository,
    product_repository,
    sales_repository,
    forecast_repository,
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.forecasting.api.dependencies import (
        get_forecast_result_service,
        get_forecast_run_service,
        get_ml_forecasting_service,
    )
    from app.modules.forecasting.application.service import (
        ForecastResultService,
        ForecastRunService,
        MLForecastingService,
    )
    from app.modules.products.api.dependencies import get_product_service
    from app.modules.products.application.service import ProductService
    from app.modules.sales.api.dependencies import get_sales_transaction_service
    from app.modules.sales.application.service import SalesTransactionService
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    async def override_product_service() -> ProductService:
        return ProductService(repository=product_repository)

    async def override_sales_transaction_service() -> SalesTransactionService:
        return SalesTransactionService(repository=sales_repository)

    async def override_forecast_run_service() -> ForecastRunService:
        return ForecastRunService(repository=forecast_repository)

    async def override_ml_forecasting_service() -> MLForecastingService:
        return MLForecastingService(repository=forecast_repository)

    async def override_forecast_result_service() -> ForecastResultService:
        return ForecastResultService(repository=forecast_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    app.dependency_overrides[get_product_service] = override_product_service
    app.dependency_overrides[get_sales_transaction_service] = (
        override_sales_transaction_service
    )
    app.dependency_overrides[get_forecast_run_service] = override_forecast_run_service
    app.dependency_overrides[get_ml_forecasting_service] = (
        override_ml_forecasting_service
    )
    app.dependency_overrides[get_forecast_result_service] = (
        override_forecast_result_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


@pytest.fixture
async def recommendation_client(
    app,
    auth_repository,
    product_repository,
    inventory_repository,
    recommendation_repository,
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.inventory.api.dependencies import get_inventory_service
    from app.modules.inventory.application.service import InventoryService
    from app.modules.products.api.dependencies import get_product_service
    from app.modules.products.application.service import ProductService
    from app.modules.recommendations.api.dependencies import (
        get_reorder_recommendation_service,
    )
    from app.modules.recommendations.application.service import (
        ReorderRecommendationService,
    )
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    async def override_product_service() -> ProductService:
        return ProductService(repository=product_repository)

    async def override_inventory_service() -> InventoryService:
        return InventoryService(repository=inventory_repository)

    async def override_reorder_recommendation_service() -> ReorderRecommendationService:
        return ReorderRecommendationService(repository=recommendation_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    app.dependency_overrides[get_product_service] = override_product_service
    app.dependency_overrides[get_inventory_service] = override_inventory_service
    app.dependency_overrides[get_reorder_recommendation_service] = (
        override_reorder_recommendation_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()


@pytest.fixture
async def dashboard_client(
    app,
    auth_repository,
    product_repository,
    inventory_repository,
    sales_repository,
    dashboard_repository,
) -> AsyncGenerator[AsyncClient, None]:
    from app.core.config import get_settings
    from app.db.session import close_database_engine
    from app.modules.auth.api.dependencies import get_auth_service
    from app.modules.auth.application.service import AuthService
    from app.modules.dashboard.api.dependencies import (
        get_dashboard_analytics_service,
    )
    from app.modules.dashboard.application.service import DashboardAnalyticsService
    from app.modules.inventory.api.dependencies import get_inventory_service
    from app.modules.inventory.application.service import InventoryService
    from app.modules.products.api.dependencies import get_product_service
    from app.modules.products.application.service import ProductService
    from app.modules.sales.api.dependencies import (
        get_sales_transaction_service,
        get_sales_upload_service,
    )
    from app.modules.sales.application.service import (
        SalesTransactionService,
        SalesUploadService,
    )
    from app.modules.users.api.dependencies import get_user_profile_service
    from app.modules.users.application.service import UserProfileService

    async def override_auth_service() -> AuthService:
        return AuthService(repository=auth_repository, settings=get_settings())

    async def override_user_profile_service() -> UserProfileService:
        return UserProfileService(repository=auth_repository)

    async def override_product_service() -> ProductService:
        return ProductService(repository=product_repository)

    async def override_inventory_service() -> InventoryService:
        return InventoryService(repository=inventory_repository)

    async def override_sales_upload_service() -> SalesUploadService:
        return SalesUploadService(repository=sales_repository)

    async def override_sales_transaction_service() -> SalesTransactionService:
        return SalesTransactionService(repository=sales_repository)

    async def override_dashboard_service() -> DashboardAnalyticsService:
        return DashboardAnalyticsService(repository=dashboard_repository)

    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_user_profile_service] = override_user_profile_service
    app.dependency_overrides[get_product_service] = override_product_service
    app.dependency_overrides[get_inventory_service] = override_inventory_service
    app.dependency_overrides[get_sales_upload_service] = override_sales_upload_service
    app.dependency_overrides[get_sales_transaction_service] = (
        override_sales_transaction_service
    )
    app.dependency_overrides[get_dashboard_analytics_service] = (
        override_dashboard_service
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await close_database_engine()
