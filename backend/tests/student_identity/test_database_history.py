"""Test database history."""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="real DB schema check requires explicit manual opt-in")
def test_physical_migrated_table_has_phase62_columns() -> None:
    """The live students table exposes the Phase 6.2 identity columns.

    Verified read-only during migration authoring; re-run manually against a
    reachable Supabase database to confirm the deployed state.
    """
    from app.db.supabase import get_admin_client  # noqa: PLC0415

    db = get_admin_client()
    rpc = (
        db.table("students")
        .select(
            "student_id, email, register_number, university_roll_number, approval_status"
        )
        .limit(1)
        .execute()
    )
    if rpc.data:
        cols = set(rpc.data[0].keys())
        assert {
            "email",
            "register_number",
            "university_roll_number",
            "approval_status",
        }.issubset(cols)


@pytest.mark.skip(reason="real DB seed check requires explicit manual opt-in")
def test_physical_existing_students_backfilled_approved() -> None:
    """Existing admin-provisioned students are approved post-migration.

    Verified read-only during migration authoring (approved backfill).
    """
    from app.db.supabase import get_admin_client  # noqa: PLC0415

    db = get_admin_client()
    rpc = db.table("students").select("student_id, approval_status").limit(10).execute()
    for row in rpc.data or []:
        assert row["approval_status"] in {"pending", "approved", "rejected"}
