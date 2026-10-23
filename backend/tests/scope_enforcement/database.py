"""Database."""

from __future__ import annotations

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4


class _Table:
    """Chainable query builder answering reads/writes from ``state``."""

    def __init__(self, state: dict, name: str):
        self._state = state
        self._name = name
        self._filters: list[tuple[str, object]] = []
        self._single = False
        self._payload = None
        self._deleting = False

    def select(self, *a, **k):
        return self

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        self._single = True
        return self

    def update(self, payload):
        self._payload = payload
        return self

    def insert(self, payload):
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        # Emulate PostgREST upsert: update matching rows, else insert.
        self._payload = payload
        self._upserting = True
        return self

    def delete(self):
        self._deleting = True
        return self

    def _rows(self):
        rows = self._state.get(self._name, {})
        if isinstance(rows, dict):
            rows = list(rows.values())
        return [
            row
            for row in rows
            if all(
                str(row.get(column, "")).lower() == str(value).lower()
                for column, value in self._filters
            )
        ]

    def execute(self):
        if self._deleting:
            for row in self._rows():
                table = self._state.setdefault(self._name, {})
                for key, value in list(table.items()):
                    if value is row:
                        table.pop(key, None)
            return SimpleNamespace(data=[])
        if self._payload is not None:
            updated = []
            for row in self._rows():
                row.update(self._payload)
                if self._name == "institutions":
                    # Emulate the trg_phase613_institutions_status trigger.
                    row["is_active"] = row.get("status") == "active"
                self._state.setdefault("updates", []).append((self._name, dict(row)))
                updated.append(row)
            if updated:
                return SimpleNamespace(data=updated)
            if getattr(self, "_upserting", False) or self._filters == []:
                # Upsert with no matching row (or unfiltered insert): create it.
                created = dict(self._payload)
                table = self._state.setdefault(self._name, {})
                if isinstance(table, list):
                    table.append(created)
                else:
                    table.setdefault(created.get("user_id", str(uuid4())), created)
                return SimpleNamespace(data=[created])
            return SimpleNamespace(data=[])
        rows = self._rows()
        if self._single:
            return SimpleNamespace(data=rows[0] if rows else None)
        return SimpleNamespace(data=rows)


def _db(state: dict):
    db = MagicMock()
    db.table.side_effect = lambda name: _Table(state, name)
    return db
