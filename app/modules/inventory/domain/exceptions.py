from app.core.exceptions import AppError


class InventoryItemAlreadyExistsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Inventory item already exists for this product.",
            code="inventory_item_already_exists",
            status_code=409,
        )


class InventoryItemNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Inventory item was not found.",
            code="inventory_item_not_found",
            status_code=404,
        )


class InventoryProductNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Product was not found.",
            code="inventory_product_not_found",
            status_code=404,
        )


class InvalidInventoryMovementTypeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Inventory movement type is invalid.",
            code="invalid_inventory_movement_type",
            status_code=400,
        )


class InvalidStockQuantityError(AppError):
    def __init__(self, message: str = "Stock quantity is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_stock_quantity",
            status_code=400,
        )


class InsufficientStockError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Insufficient stock for this movement.",
            code="insufficient_stock",
            status_code=409,
        )


class InvalidInventoryThresholdError(AppError):
    def __init__(self, message: str = "Inventory threshold is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_inventory_threshold",
            status_code=400,
        )


class InvalidInventoryFieldError(AppError):
    def __init__(self, message: str = "Inventory field is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_inventory_field",
            status_code=400,
        )


class InvalidInventorySortFieldError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Inventory sort field is invalid.",
            code="invalid_inventory_sort_field",
            status_code=400,
        )
