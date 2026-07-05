import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
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


@pytest.fixture
def auth_repository() -> FakeAuthRepository:
    return FakeAuthRepository()


@pytest.fixture
def product_repository() -> FakeProductRepository:
    return FakeProductRepository()


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
