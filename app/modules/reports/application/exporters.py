from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import Any
from uuid import UUID

from fastapi.responses import Response

from app.modules.reports.domain.exceptions import ReportCsvExportFailedError
from app.modules.reports.domain.validators import build_safe_report_filename


def serialize_report_rows_to_csv(
    rows: list[dict[str, Any]],
    *,
    fieldnames: tuple[str, ...],
) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})
    return buffer.getvalue()


def generate_csv_response(
    *,
    report_name: str,
    generated_at: datetime,
    rows: list[dict[str, Any]],
    fieldnames: tuple[str, ...],
) -> Response:
    try:
        content = serialize_report_rows_to_csv(rows, fieldnames=fieldnames)
        filename = build_safe_report_filename(report_name, generated_at.date())
    except Exception as exc:
        raise ReportCsvExportFailedError() from exc
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str):
        return _escape_spreadsheet_formula(value)
    return str(value)


def _escape_spreadsheet_formula(value: str) -> str:
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value
