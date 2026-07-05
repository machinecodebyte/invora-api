from app.core.exceptions import AppError


class DuplicateProductSkuError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "A product with this SKU already exists.",
            code="duplicate_product_sku",
            status_code=409,
        )


class DuplicateProductCategoryError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "A product category with this name already exists.",
            code="duplicate_product_category",
            status_code=409,
        )


class ProductNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Product was not found.",
            code="product_not_found",
            status_code=404,
        )


class ProductCategoryNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Product category was not found.",
            code="product_category_not_found",
            status_code=404,
        )


class InvalidProductFieldError(AppError):
    def __init__(self, message: str = "Product field is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_product_field",
            status_code=400,
        )


class InvalidProductSkuError(AppError):
    def __init__(self, message: str = "Product SKU is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_product_sku",
            status_code=400,
        )


class InvalidProductUnitError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Product unit is invalid.",
            code="invalid_product_unit",
            status_code=400,
        )


class InvalidProductPriceError(AppError):
    def __init__(self, message: str = "Product price is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_product_price",
            status_code=400,
        )


class ProductCategoryHasActiveProductsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Product category has active products and cannot be archived.",
            code="product_category_has_active_products",
            status_code=409,
        )


class InvalidProductSortFieldError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Product sort field is invalid.",
            code="invalid_product_sort_field",
            status_code=400,
        )
