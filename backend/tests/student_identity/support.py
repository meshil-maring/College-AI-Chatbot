"""Support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from uuid import uuid4


INSTITUTION_A = "a1111111-0000-0000-0000-000000000001"


INSTITUTION_B = "b2222222-0000-0000-0000-000000000002"


USER_A = uuid4()


USER_B = uuid4()


STUDENT_ID_A = "30000000-0000-0000-0000-000000000151"


STUDENT_ID_B = "30000000-0000-0000-0000-000000000152"


STUDENT_ROW_A = {
    "student_id": STUDENT_ID_A,
    "user_id": str(USER_A),
    "institution_id": INSTITUTION_A,
    "student_number": "STU-2026-001",
    "email": "student.a@collegea.test",
    "register_number": "1001",
    "university_roll_number": "2026-1001",
    "approval_status": "approved",
    "status": "active",
    "is_active": True,
}


STUDENT_ROW_B = {
    "student_id": STUDENT_ID_B,
    "user_id": str(USER_B),
    "institution_id": INSTITUTION_B,
    "student_number": "STU-2026-002",
    "email": "student.b@collegeb.test",
    "register_number": "1001",  # intentionally mirrors College A's register number
    "university_roll_number": "2026-1002",
    "approval_status": "approved",
    "status": "active",
    "is_active": True,
}


def _make_mock_client(rows: list[dict] | None = None) -> MagicMock:
    """Return a MagicMock Supabase client returning ``rows`` on select.

    Supports the chained call patterns used by the admin_academics repository:

    * Identity lookups: ``.select(...).eq(...).eq(...).maybe_single().execute()``
    * Single lookups:  ``.select(...).eq(...).maybe_single().execute()``
    * Listing:         ``.select(...).eq(...).order(...).limit(...).range(...).execute()``
    """
    client = MagicMock()
    builder = MagicMock()
    # table("students").select(...) -> builder
    client.table.return_value.select.return_value = builder
    # chained .eq() calls return the same builder
    builder.eq.return_value = builder
    # maybe_single() -> wrapper whose execute() returns rows[0] or None
    maybe_single = MagicMock()
    maybe_single.execute.return_value = MagicMock(data=((rows or [None])[0]))
    builder.maybe_single.return_value = maybe_single
    # listing chain: .order().limit().range().execute()
    builder.order.return_value = builder
    builder.limit.return_value = builder
    builder.range.return_value = builder
    builder.execute.return_value = MagicMock(data=rows or [])
    return client


def _make_mock_insert(return_row: dict) -> MagicMock:
    """MagicMock whose ``insert(row).execute()`` returns ``[return_row]``."""
    db = MagicMock()
    db.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[return_row]
    )
    return db


def _make_mock_update(
    get_student_row: dict,
    update_rows: list[dict],
) -> MagicMock:
    """MagicMock for ``get_student`` + ``update`` chained calls."""
    db = MagicMock()
    # read path: .select(...).eq(...).maybe_single().execute()
    sel = MagicMock()
    sel.eq.return_value = sel
    sel.maybe_single.return_value.execute.return_value = MagicMock(data=get_student_row)
    db.table.return_value.select.return_value = sel
    # update path: .update(fields).eq(...).execute()
    upd = MagicMock()
    upd.eq.return_value = upd
    upd.execute.return_value = MagicMock(data=update_rows)
    db.table.return_value.update.return_value = upd
    return db
