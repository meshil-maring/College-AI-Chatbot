"""Read complete internal projections without silently accepting REST row caps."""

from typing import Any

from app.core.errors import AppError


def read_rows(query: Any) -> list[dict]:
    data = query.execute().data
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise AppError("Invalid database projection", 500, "DATABASE_PROJECTION_INVALID")
    return data


def read_one(query: Any) -> dict | None:
    response = query.execute()
    data = response.data if response is not None else None
    if data is not None and not isinstance(data, dict):
        raise AppError("Invalid database projection", 500, "DATABASE_PROJECTION_INVALID")
    return data


def read_all(query: Any) -> list[dict]:
    rows: list[dict] = []
    while True:
        page = read_rows(query.range(len(rows), len(rows) + 499))
        rows.extend(page)
        if len(page) < 500:
            return rows
