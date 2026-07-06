from app.core.exceptions import AppError


class InvalidSalesUploadFileError(AppError):
    def __init__(self, message: str = "Sales upload file is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_sales_upload_file",
            status_code=400,
        )


class SalesUploadFileTooLargeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Sales upload file is too large.",
            code="sales_upload_file_too_large",
            status_code=413,
        )


class MissingSalesCsvColumnsError(AppError):
    def __init__(self, missing_columns: list[str]) -> None:
        super().__init__(
            f"Sales CSV is missing required columns: {', '.join(missing_columns)}.",
            code="missing_sales_csv_columns",
            status_code=400,
        )


class InvalidSalesCsvFormatError(AppError):
    def __init__(self, message: str = "Sales CSV format is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_sales_csv_format",
            status_code=400,
        )


class DuplicateSalesUploadError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "This sales file has already been uploaded.",
            code="duplicate_sales_upload",
            status_code=409,
        )


class SalesUploadNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Sales upload was not found.",
            code="sales_upload_not_found",
            status_code=404,
        )


class SalesTransactionNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Sales transaction was not found.",
            code="sales_transaction_not_found",
            status_code=404,
        )


class SalesTransactionProductNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Product was not found.",
            code="sales_transaction_product_not_found",
            status_code=404,
        )


class InvalidSalesTransactionFieldError(AppError):
    def __init__(
        self,
        message: str = "Sales transaction field is invalid.",
    ) -> None:
        super().__init__(
            message,
            code="invalid_sales_transaction_field",
            status_code=400,
        )


class InvalidSalesTransactionQuantityError(AppError):
    def __init__(self, message: str = "Sales transaction quantity is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_sales_transaction_quantity",
            status_code=400,
        )


class InvalidSalesTransactionPriceError(AppError):
    def __init__(self, message: str = "Sales transaction price is invalid.") -> None:
        super().__init__(
            message,
            code="invalid_sales_transaction_price",
            status_code=400,
        )


class InvalidSalesTransactionDateRangeError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Sales transaction date range is invalid.",
            code="invalid_sales_transaction_date_range",
            status_code=400,
        )


class InvalidSalesTransactionSourceError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Sales transaction source is invalid.",
            code="invalid_sales_transaction_source",
            status_code=400,
        )


class InvalidSalesTransactionSortFieldError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Sales transaction sort field is invalid.",
            code="invalid_sales_transaction_sort_field",
            status_code=400,
        )


class SalesTransactionAlreadyDeletedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "Sales transaction is already deleted.",
            code="sales_transaction_already_deleted",
            status_code=409,
        )
