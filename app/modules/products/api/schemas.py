from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.products.domain.catalog import (
    ALLOWED_CATEGORY_FIELDS,
    ALLOWED_PRODUCT_FIELDS,
    ALLOWED_PRODUCT_UNITS,
    ensure_no_unsupported_fields,
)


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=64)
    category_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    unit: str = Field(..., min_length=1, max_length=32)
    selling_price: Decimal | None = Field(default=Decimal("0.00"))
    cost_price: Decimal | None = None

    model_config = ConfigDict(extra="allow")

    def create_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_unsupported_fields(
            extra_fields=extra_fields,
            allowed_fields=ALLOWED_PRODUCT_FIELDS,
            resource_name="Product",
        )
        return {
            "name": self.name,
            "sku": self.sku,
            "category_id": self.category_id,
            "description": self.description,
            "unit": self.unit,
            "selling_price": self.selling_price,
            "cost_price": self.cost_price,
        }


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    category_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    unit: str | None = Field(default=None, min_length=1, max_length=32)
    selling_price: Decimal | None = None
    cost_price: Decimal | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="allow")

    def update_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_unsupported_fields(
            extra_fields=extra_fields,
            allowed_fields=ALLOWED_PRODUCT_FIELDS,
            resource_name="Product",
        )
        return {
            field: getattr(self, field)
            for field in ALLOWED_PRODUCT_FIELDS
            if field in self.model_fields_set
        }


class ProductPublic(BaseModel):
    id: UUID
    category_id: UUID | None
    name: str
    sku: str
    description: str | None
    unit: str
    selling_price: Decimal
    cost_price: Decimal | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductData(BaseModel):
    product: ProductPublic


class ProductListData(BaseModel):
    products: list[ProductPublic]
    total: int
    limit: int
    offset: int


class ProductResponse(BaseModel):
    success: Literal[True] = True
    data: ProductData


class ProductListResponse(BaseModel):
    success: Literal[True] = True
    data: ProductListData


class ProductCategoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    model_config = ConfigDict(extra="allow")

    def create_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_unsupported_fields(
            extra_fields=extra_fields,
            allowed_fields=ALLOWED_CATEGORY_FIELDS,
            resource_name="Category",
        )
        return {"name": self.name, "description": self.description}


class ProductCategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

    model_config = ConfigDict(extra="allow")

    def update_values(self) -> dict[str, Any]:
        extra_fields = set(self.__pydantic_extra__ or {})
        ensure_no_unsupported_fields(
            extra_fields=extra_fields,
            allowed_fields=ALLOWED_CATEGORY_FIELDS,
            resource_name="Category",
        )
        return {
            field: getattr(self, field)
            for field in ALLOWED_CATEGORY_FIELDS
            if field in self.model_fields_set
        }


class ProductCategoryPublic(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductCategoryData(BaseModel):
    category: ProductCategoryPublic


class ProductCategoryListData(BaseModel):
    categories: list[ProductCategoryPublic]
    total: int
    limit: int
    offset: int


class ProductCategoryResponse(BaseModel):
    success: Literal[True] = True
    data: ProductCategoryData


class ProductCategoryListResponse(BaseModel):
    success: Literal[True] = True
    data: ProductCategoryListData


class ProductUnitData(BaseModel):
    units: tuple[
        Literal["pcs", "kg", "gram", "liter", "ml", "box", "packet", "dozen"], ...
    ]


class ProductUnitResponse(BaseModel):
    success: Literal[True] = True
    data: ProductUnitData


class MessageData(BaseModel):
    message: str


class MessageResponse(BaseModel):
    success: Literal[True] = True
    data: MessageData


def allowed_product_units() -> tuple[str, ...]:
    return ALLOWED_PRODUCT_UNITS
