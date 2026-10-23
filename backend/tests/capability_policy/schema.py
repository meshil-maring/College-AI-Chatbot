"""Schema."""

from __future__ import annotations

import re

from .support import (
    _migration_sql,
)


def _created_tables() -> set[str]:
    sql = _migration_sql()
    return {
        match.lower()
        for match in re.findall(r'CREATE TABLE[^;]*?"public"\."([a-z_]+)"', sql)
    }


def _table_body(table: str) -> str:
    sql = _migration_sql()
    match = re.search(rf'CREATE TABLE[^;]*?"public"\."{table}"\s*\((.*?)\);', sql, re.S)
    assert match is not None, f"table {table} not found in the migration ledger"
    return match.group(1).lower()
