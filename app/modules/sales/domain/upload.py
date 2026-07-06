from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import StringIO
from pathlib import PureWindowsPath
from typing import Any

from app.modules.products.domain.catalog import normalize_sku
from app.modules.products.domain.exceptions import InvalidProductSkuError
from app.modules.sales.domain.exceptions import (
    InvalidSalesCsvFormatError,
    InvalidSalesUploadFileError,
    MissingSalesCsvColumnsError,
    SalesUploadFileTooLargeError,
)

REQUIRED_COLUMNS = ("sale_date", "product_sku", "quantity")
OPTIONAL_COLUMNS = (
    "unit_price",
    "total_amount",
    "customer_name",
    "channel",
    "notes",
)
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
UPLOAD_STATUSES = (
    "processing",
    "completed",
    "completed_with_errors",
    "failed",
)
SALES_SOURCES = ("csv_upload", "manual", "api")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = (".csv",)
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "text/plain",
    "",
}
QUANTITY_QUANTUM = Decimal("0.001")
MONEY_QUANTUM = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class ParsedCsvRow:
    row_number: int
    raw_data: dict[str, str]


@dataclass(frozen=True, slots=True)
class ValidSalesRow:
    row_number: int
    product_sku: str
    sale_date: date
    quantity: Decimal
    unit_price: Decimal | None
    total_amount: Decimal | None
    customer_name: str | None
    channel: str | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class RejectedSalesRow:
    row_number: int
    raw_data: dict[str, str]
    error_code: str
    error_message: str


def validate_upload_file(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> tuple[str, str]:
    safe_name = sanitize_filename(filename)
    if not safe_name.lower().endswith(ALLOWED_EXTENSIONS):
        raise InvalidSalesUploadFileError("Only .csv sales uploads are supported.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise SalesUploadFileTooLargeError()
    if len(content) == 0:
        raise InvalidSalesUploadFileError("Sales upload file is empty.")

    normalized_content_type = (content_type or "").split(";")[0].strip().lower()
    if normalized_content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidSalesUploadFileError("Sales upload content type is unsupported.")

    return safe_name, calculate_file_hash(content)


def sanitize_filename(filename: str | None) -> str:
    raw_name = PureWindowsPath(filename or "sales_upload.csv").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._")
    if not cleaned:
        cleaned = "sales_upload.csv"
    if len(cleaned) > 255:
        stem, dot, suffix = cleaned.rpartition(".")
        if dot:
            cleaned = f"{stem[:240]}.{suffix[:10]}"
        else:
            cleaned = cleaned[:255]
    return cleaned


def calculate_file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_sales_csv(content: bytes) -> list[ParsedCsvRow]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidSalesCsvFormatError("Sales CSV must be UTF-8 encoded.") from exc

    try:
        reader = csv.DictReader(StringIO(text))
    except csv.Error as exc:
        raise InvalidSalesCsvFormatError() from exc

    if reader.fieldnames is None:
        raise InvalidSalesCsvFormatError("Sales CSV must include a header row.")

    normalized_headers = [_normalize_header(header) for header in reader.fieldnames]
    missing = sorted(set(REQUIRED_COLUMNS) - set(normalized_headers))
    if missing:
        raise MissingSalesCsvColumnsError(missing)
    if len(set(normalized_headers)) != len(normalized_headers):
        raise InvalidSalesCsvFormatError("Sales CSV contains duplicate columns.")

    rows: list[ParsedCsvRow] = []
    try:
        for index, raw_row in enumerate(reader, start=2):
            if None in raw_row:
                rows.append(
                    ParsedCsvRow(
                        row_number=index,
                        raw_data={"_raw": str(raw_row)},
                    )
                )
                continue

            normalized_row = {
                _normalize_header(key): (value or "")
                for key, value in raw_row.items()
            }
            rows.append(ParsedCsvRow(row_number=index, raw_data=normalized_row))
    except csv.Error as exc:
        raise InvalidSalesCsvFormatError() from exc

    if not rows:
        raise InvalidSalesCsvFormatError("Sales CSV does not contain data rows.")
    return rows


def collect_normalized_skus(rows: list[ParsedCsvRow]) -> set[str]:
    normalized_skus: set[str] = set()
    for row in rows:
        sku_value = row.raw_data.get("product_sku", "")
        if not sku_value.strip():
            continue
        try:
            normalized_skus.add(normalize_sku(sku_value))
        except InvalidProductSkuError:
            continue
    return normalized_skus


def validate_sales_row(
    row: ParsedCsvRow,
    *,
    known_skus: set[str],
) -> ValidSalesRow | RejectedSalesRow:
    if _is_empty_row(row.raw_data):
        return _reject(row, "empty_row", "Sales CSV row is empty.")

    raw_sku = row.raw_data.get("product_sku", "")
    try:
        normalized_sku = normalize_sku(raw_sku)
    except InvalidProductSkuError:
        return _reject(row, "invalid_product_sku", "Product SKU is invalid.")

    if normalized_sku not in known_skus:
        return _reject(
            row,
            "unknown_product_sku",
            "Product SKU was not found for this user.",
        )

    sale_date = _parse_sale_date(row.raw_data.get("sale_date", ""))
    if isinstance(sale_date, RejectedSalesRow):
        return _copy_rejection(row, sale_date)

    quantity = _parse_quantity(row.raw_data.get("quantity", ""))
    if isinstance(quantity, RejectedSalesRow):
        return _copy_rejection(row, quantity)

    unit_price = _parse_money(
        row.raw_data.get("unit_price", ""),
        field_name="unit_price",
        required=False,
        precision=MONEY_QUANTUM,
    )
    if isinstance(unit_price, RejectedSalesRow):
        return _copy_rejection(row, unit_price)

    total_amount = _parse_money(
        row.raw_data.get("total_amount", ""),
        field_name="total_amount",
        required=False,
        precision=MONEY_QUANTUM,
    )
    if isinstance(total_amount, RejectedSalesRow):
        return _copy_rejection(row, total_amount)

    if total_amount is None and unit_price is not None:
        total_amount = (quantity * unit_price).quantize(MONEY_QUANTUM)

    return ValidSalesRow(
        row_number=row.row_number,
        product_sku=normalized_sku,
        sale_date=sale_date,
        quantity=quantity,
        unit_price=unit_price,
        total_amount=total_amount,
        customer_name=_normalize_optional_text(row.raw_data.get("customer_name"), 255),
        channel=_normalize_optional_text(row.raw_data.get("channel"), 64),
        notes=_normalize_optional_text(row.raw_data.get("notes"), 1000),
    )


def calculate_upload_status(*, accepted_rows: int, rejected_rows: int) -> str:
    if accepted_rows > 0 and rejected_rows == 0:
        return "completed"
    if rejected_rows > 0:
        return "completed_with_errors"
    return "failed"


def upload_template() -> dict[str, Any]:
    return {
        "required_columns": list(REQUIRED_COLUMNS),
        "optional_columns": list(OPTIONAL_COLUMNS),
        "example_rows": [
            {
                "sale_date": "2026-07-01",
                "product_sku": "MILK-1",
                "quantity": "12.000",
                "unit_price": "25.50",
                "total_amount": "306.00",
                "customer_name": "Walk-in",
                "channel": "store",
                "notes": "Historical sale",
            }
        ],
        "notes": (
            "Sales uploads store historical demand only. They do not reduce "
            "inventory stock."
        ),
    }


def _parse_sale_date(value: str) -> date | RejectedSalesRow:
    raw_value = value.strip()
    if not raw_value:
        return RejectedSalesRow(0, {}, "invalid_sale_date", "sale_date is required.")

    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw_value, date_format).date()
        except ValueError:
            continue
    return RejectedSalesRow(0, {}, "invalid_sale_date", "sale_date is invalid.")


def _parse_quantity(value: str) -> Decimal | RejectedSalesRow:
    raw_value = value.strip()
    if not raw_value:
        return RejectedSalesRow(0, {}, "invalid_quantity", "quantity is required.")
    try:
        quantity = Decimal(raw_value)
    except InvalidOperation:
        return RejectedSalesRow(0, {}, "invalid_quantity", "quantity is invalid.")
    if quantity <= 0:
        return RejectedSalesRow(
            0,
            {},
            "invalid_quantity",
            "quantity must be positive.",
        )
    if quantity.as_tuple().exponent < -3:
        return RejectedSalesRow(
            0,
            {},
            "invalid_quantity",
            "quantity cannot have more than 3 decimals.",
        )
    return quantity.quantize(QUANTITY_QUANTUM)


def _parse_money(
    value: str,
    *,
    field_name: str,
    required: bool,
    precision: Decimal,
) -> Decimal | None | RejectedSalesRow:
    raw_value = value.strip()
    if not raw_value:
        if required:
            return RejectedSalesRow(
                0,
                {},
                f"invalid_{field_name}",
                f"{field_name} is required.",
            )
        return None
    try:
        amount = Decimal(raw_value)
    except InvalidOperation:
        return RejectedSalesRow(
            0,
            {},
            f"invalid_{field_name}",
            f"{field_name} is invalid.",
        )
    if amount < 0:
        return RejectedSalesRow(
            0,
            {},
            f"invalid_{field_name}",
            f"{field_name} cannot be negative.",
        )
    if amount.as_tuple().exponent < -2:
        return RejectedSalesRow(
            0,
            {},
            f"invalid_{field_name}",
            f"{field_name} cannot have more than 2 decimals.",
        )
    return amount.quantize(precision)


def _normalize_optional_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not normalized:
        return None
    return normalized[:max_length]


def _normalize_header(value: str | None) -> str:
    return (value or "").strip().lower()


def _is_empty_row(raw_data: dict[str, str]) -> bool:
    return all(not str(value).strip() for value in raw_data.values())


def _reject(row: ParsedCsvRow, code: str, message: str) -> RejectedSalesRow:
    return RejectedSalesRow(
        row_number=row.row_number,
        raw_data=row.raw_data,
        error_code=code,
        error_message=message,
    )


def _copy_rejection(
    row: ParsedCsvRow,
    rejection: RejectedSalesRow,
) -> RejectedSalesRow:
    return _reject(row, rejection.error_code, rejection.error_message)
