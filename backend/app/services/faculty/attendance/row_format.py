"""Bounded attendance table rows and canonical CSV columns."""

import csv
import io
from collections.abc import Iterable, Mapping
from typing import Any

from app.core.errors import AppError

MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_UNPACKED_XLSX_BYTES = 50 * 1024 * 1024
MAX_IMPORT_ROWS = 500
MAX_COLUMNS = 20
ALLOWED_SUFFIXES = {"csv", "xls", "xlsx", "pdf", "png", "jpg", "jpeg", "webp"}
ATTENDANCE_STATUSES = {"present", "absent", "late", "excused"}
REQUIRED_IDENTITY_COLUMNS = {"register_number", "student_name"}
SUMMARY_COLUMNS = {
    "attendance",
    "attendance_percentage",
    "classes_conducted",
    "classes_present",
    "classes_absent",
    "status",
}
ALLOWED_COLUMNS = REQUIRED_IDENTITY_COLUMNS | SUMMARY_COLUMNS | {'university_roll_number', 'email', 'address', 'session_date'}



class ParsedRows(list[dict[str, str]]):
    """A list that retains headers for server-side validation."""

    headers: tuple[str, ...]

    def __init__(self, rows: Iterable[dict[str, str]] = (), headers: Iterable[str] = ()):
        super().__init__(rows)
        self.headers = tuple(headers)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _column_name(value: object) -> str:
    return _clean(value).lstrip("\ufeff").lower().replace(" ", "_")


def _canonical_header(value: object) -> str:
    name = _column_name(value)
    return {"name": "student_name", "percentage": "attendance"}.get(name, name)


def _normalize_row(row: Mapping[Any, Any]) -> dict[str, str]:
    return {_canonical_header(key): _clean(value) for key, value in row.items() if key is not None and _clean(value)}


def _parse_csv(text: str, *, dialect='excel') -> ParsedRows:
    if '\x00' in text:
        raise AppError('The table contains binary data', 422, 'MALFORMED_FILE')
    try:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect, strict=True)
        headers = tuple(_canonical_header(k) for k in reader.fieldnames or [])
        if not headers or len(headers) > MAX_COLUMNS or len(headers) != len(set(headers)) or '' in headers:
            raise AppError('The table must have unique, nonblank column names (maximum 20)', 422, 'MISSING_REQUIRED_COLUMNS')
        rows = ParsedRows(headers=headers)
        for row in reader:
            if None in row:
                raise AppError('A table row has more values than columns', 422, 'MALFORMED_FILE')
            if any(_clean(v) for v in row.values()):
                rows.append(_normalize_row(row))
            if len(rows) > MAX_IMPORT_ROWS:
                raise AppError('Imports are limited to 500 rows; split the file', 413, 'TOO_MANY_ROWS')
        return rows
    except csv.Error as exc:
        raise AppError('The table is malformed', 422, 'MALFORMED_FILE') from exc


