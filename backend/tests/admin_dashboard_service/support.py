"""Shared authorization principals and test doubles."""

from unittest.mock import MagicMock, patch

from uuid import uuid4

from app.services.admin import admin_dashboard as svc

TABLE_COUNTS = {
    "knowledge_sources": 4,
    "documents": 11,
    "faqs": 7,
    "notices": 3,
    "students": 42,
}


def _db(counts: dict[str, int] | None = None):
    """Mock client returning per-table counts for chained .eq()/.in_() filters."""
    counts = TABLE_COUNTS if counts is None else counts
    db = MagicMock()
    registry = {}

    def table(name):
        m = MagicMock()
        response = MagicMock(count=counts.get(name, 0), data=[])
        sel = m.select.return_value
        sel.execute.return_value = response
        eq1 = sel.eq.return_value
        eq1.execute.return_value = response
        eq1.eq.return_value.execute.return_value = response
        eq1.in_.return_value.execute.return_value = response
        registry[name] = m
        return m

    db.table.side_effect = table
    db._registry = registry
    return db


def _no_notices():
    """Stub the shared notice-listing repository used for recent notices."""
    return patch(
        "app.services.admin.admin_dashboard.knowledge_repo.list_notices",
        return_value=[],
    )
