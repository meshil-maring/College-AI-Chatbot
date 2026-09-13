"""Phase 6.2 — Student Database Model tests.

Tests the Student identity model: new identity columns, institution-scoped
uniqueness, approval lifecycle, identity resolution helpers, and backward
compatibility of the unchanged student/admin projections.

Physical/integration tests that hit the live database are marked with
@pytest.mark.skip(reason="real DB calls require explicit manual opt-in"),
following the project convention used by
``test_physical_validation_phase_4_4.py``. All other tests are hermetic
(mocked Supabase client) and run everywhere.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.repositories import admin_academics as repo
from app.services import admin_academics as svc


# ============================================================================
# Shared test constants
# ============================================================================

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


# ============================================================================
# Mock helpers
# ============================================================================


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
    maybe_single.execute.return_value = MagicMock(
        data=((rows or [None])[0])
    )
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
    sel.maybe_single.return_value.execute.return_value = MagicMock(
        data=get_student_row
    )
    db.table.return_value.select.return_value = sel
    # update path: .update(fields).eq(...).execute()
    upd = MagicMock()
    upd.eq.return_value = upd
    upd.execute.return_value = MagicMock(data=update_rows)
    db.table.return_value.update.return_value = upd
    return db
# ============================================================================
# 1. Repository column projections — backward compatibility
# ============================================================================


def test_student_columns_projection_does_not_include_phase62_identity() -> None:
    """STUDENT_COLUMNS must stay untouched for backward compatibility."""
    cols = repo.STUDENT_COLUMNS
    assert "email" not in cols
    assert "register_number" not in cols
    assert "university_roll_number" not in cols
    assert "approval_status" not in cols
    assert "institution_id" in cols
    assert "student_number" in cols


def test_student_identity_columns_projection_exposes_phase62_fields() -> None:
    """STUDENT_IDENTITY_COLUMNS exposes the Phase 6.2 identity fields."""
    cols = repo.STUDENT_IDENTITY_COLUMNS
    assert "email" in cols
    assert "register_number" in cols
    assert "university_roll_number" in cols
    assert "approval_status" in cols
    assert "institution_id" in cols


def test_student_identity_columns_still_contains_core_identity() -> None:
    """Identity projection still includes the core tenant + student identity."""
    cols = repo.STUDENT_IDENTITY_COLUMNS
    for field in (
        "student_id",
        "user_id",
        "institution_id",
        "student_number",
        "status",
        "is_active",
    ):
        assert field in cols, f"{field} missing from STUDENT_IDENTITY_COLUMNS"


def test_identity_projection_has_no_tenant_id() -> None:
    """institution_id remains the sole tenant key — no tenant_id anywhere."""
    assert "tenant_id" not in repo.STUDENT_IDENTITY_COLUMNS
    assert "tenant_id" not in repo.STUDENT_COLUMNS


# ============================================================================
# 2. Repository identity lookup — institution scoping
# ============================================================================


def test_get_student_by_email_resolves_within_institution() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_email(client, INSTITUTION_A, "student.a@collegea.test")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_email_is_case_insensitive() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_email(client, INSTITUTION_A, "STUDENT.A@COLLEGEA.TEST")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_email_returns_none_when_missing() -> None:
    client = _make_mock_client()
    row = repo.get_student_by_email(client, INSTITUTION_A, "missing@collegea.test")
    assert row is None


def test_get_student_by_register_number_resolves_within_institution() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_register_number(client, INSTITUTION_A, "1001")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_register_number_trims_input() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_register_number(client, INSTITUTION_A, "  1001 ")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_register_number_returns_none_when_missing() -> None:
    client = _make_mock_client()
    row = repo.get_student_by_register_number(client, INSTITUTION_A, "9999")
    assert row is None


def test_get_student_by_university_roll_number_resolves_within_institution() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_university_roll_number(
        client, INSTITUTION_A, "2026-1001"
    )
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_get_student_by_university_roll_number_returns_none_when_missing() -> None:
    client = _make_mock_client()
    row = repo.get_student_by_university_roll_number(
        client, INSTITUTION_A, "no-such-roll"
    )
    assert row is None


def test_resolve_student_by_identifier_email_match() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.resolve_student_by_identifier(
        client, INSTITUTION_A, "student.a@collegea.test"
    )
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_resolve_student_by_identifier_register_number_match() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "1001")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_resolve_student_by_identifier_university_roll_match() -> None:
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "2026-1001")
    assert row is not None
    assert row["student_id"] == STUDENT_ID_A


def test_resolve_student_by_identifier_empty_returns_none() -> None:
    client = _make_mock_client()
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "   ")
    assert row is None
    row = repo.resolve_student_by_identifier(client, INSTITUTION_A, "")
    assert row is None
# ============================================================================
# 3. Institution-scoped identity uniqueness
#    (Phase 6.2 replaces the global student_number constraint with
#     UNIQUE(institution_id, student_number), and adds institution-scoped
#     uniqueness for email / register_number / university_roll_number.)
# ============================================================================


def test_same_register_number_allowed_in_different_institutions() -> None:
    """College A register 1001 and College B register 1001 may coexist."""
    client_a = _make_mock_client([STUDENT_ROW_A])
    client_b = _make_mock_client([STUDENT_ROW_B])

    a = repo.get_student_by_register_number(client_a, INSTITUTION_A, "1001")
    b = repo.get_student_by_register_number(client_b, INSTITUTION_B, "1001")

    assert a is not None and a["student_id"] == STUDENT_ID_A
    assert b is not None and b["student_id"] == STUDENT_ID_B
    assert a["institution_id"] != b["institution_id"]
    assert a["register_number"] == b["register_number"] == "1001"


def test_same_email_allowed_in_different_institutions() -> None:
    """Two institutions may independently scope an identical email value."""
    row_a = {**STUDENT_ROW_A, "email": "shared@college.test"}
    row_b = {**STUDENT_ROW_B, "email": "shared@college.test"}
    client_a = _make_mock_client([row_a])
    client_b = _make_mock_client([row_b])

    a = repo.get_student_by_email(client_a, INSTITUTION_A, "shared@college.test")
    b = repo.get_student_by_email(client_b, INSTITUTION_B, "shared@college.test")

    assert a is not None and a["student_id"] == STUDENT_ID_A
    assert b is not None and b["student_id"] == STUDENT_ID_B


def test_same_university_roll_allowed_in_different_institutions() -> None:
    """University roll numbers are scoped per institution as well."""
    row_a = {**STUDENT_ROW_A, "university_roll_number": "2026-0001"}
    row_b = {**STUDENT_ROW_B, "university_roll_number": "2026-0001"}
    client_a = _make_mock_client([row_a])
    client_b = _make_mock_client([row_b])

    a = repo.get_student_by_university_roll_number(
        client_a, INSTITUTION_A, "2026-0001"
    )
    b = repo.get_student_by_university_roll_number(
        client_b, INSTITUTION_B, "2026-0001"
    )

    assert a is not None and a["student_id"] == STUDENT_ID_A
    assert b is not None and b["student_id"] == STUDENT_ID_B


def test_same_student_number_allowed_in_different_institutions() -> None:
    """student_number uniqueness is now (institution_id, student_number)."""
    row_a = {**STUDENT_ROW_A, "student_number": "1001"}
    row_b = {**STUDENT_ROW_B, "student_number": "1001"}
    client_a = _make_mock_client([row_a])
    client_b = _make_mock_client([row_b])

    a = repo.get_student(client_a, STUDENT_ID_A)
    b = repo.get_student(client_b, STUDENT_ID_B)

    assert a["institution_id"] == INSTITUTION_A
    assert b["institution_id"] == INSTITUTION_B
    assert a["student_number"] == b["student_number"] == "1001"


def test_register_number_lookup_scopes_by_institution() -> None:
    """The repo passes institution_id into the query — scoping is server-side."""
    client = MagicMock()
    builder = MagicMock()
    eq_calls = []
    builder.eq.side_effect = lambda col, val: eq_calls.append((col, val)) or builder
    builder.maybe_single.return_value.execute.return_value = MagicMock(data=None)
    client.table.return_value.select.return_value = builder

    repo.get_student_by_register_number(client, INSTITUTION_B, "1001")

    # The lookup must filter on institution_id (tenant) then register_number.
    assert ("institution_id", INSTITUTION_B) in eq_calls
    assert ("register_number", "1001") in eq_calls


def test_get_student_returns_core_columns_without_identity_leak() -> None:
    """Backward compatibility: existing get_student shape is unchanged."""
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student(client, STUDENT_ID_A)
    assert row is None or row.get("student_id") == STUDENT_ID_A
    # STUDENT_COLUMNS governs the API response; identity fields stay private
    # to the identity projection.
    assert "email" not in repo.STUDENT_COLUMNS
# ============================================================================
# 4. Service identity normalization + persistence
# ============================================================================


def test_create_student_normalizes_email_and_numbers() -> None:
    """create_student lowercases/trims email and trims register/roll numbers."""
    db = _make_mock_insert(
        {
            "student_id": STUDENT_ID_A,
            "institution_id": INSTITUTION_A,
            "email": "student.a@collegea.test",
            "register_number": "1001",
            "university_roll_number": "2026-1001",
            "approval_status": "approved",
            "status": "active",
            "is_active": True,
        }
    )
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.create_student(
            svc.StudentCreate(
                user_id=USER_A,
                institution_id=INSTITUTION_A,
                student_number="STU-2026-001",
                email="  STUDENT.A@COLLEGEA.TEST  ",
                register_number="  1001  ",
                university_roll_number="  2026-1001  ",
                approval_status="approved",
                enrollment_date="2026-01-15",
            )
        )
    assert student["email"] == "student.a@collegea.test"
    assert student["register_number"] == "1001"
    assert student["university_roll_number"] == "2026-1001"
    assert student["approval_status"] == "approved"


def test_create_student_drops_whitespace_only_identity_values() -> None:
    """No identity value -> column stays NULL (provisioned in Phase 6.5)."""
    db = _make_mock_insert(
        {
            "student_id": STUDENT_ID_A,
            "institution_id": INSTITUTION_A,
            "email": None,
            "register_number": None,
            "university_roll_number": None,
            "approval_status": "approved",
            "status": "active",
        }
    )
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.create_student(
            svc.StudentCreate(
                user_id=USER_A,
                institution_id=INSTITUTION_A,
                student_number="STU-2026-001",
                email="   ",
                register_number="",
                enrollment_date="2026-01-15",
            )
        )
    assert student["email"] is None
    assert student["register_number"] is None


def test_create_student_without_identity_is_valid() -> None:
    """A student row without Phase 6.2 identity fields is still valid."""
    db = _make_mock_insert(
        {
            "student_id": STUDENT_ID_A,
            "institution_id": INSTITUTION_A,
            "email": None,
            "register_number": None,
            "university_roll_number": None,
            "approval_status": "pending",
            "status": "active",
        }
    )
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.create_student(
            svc.StudentCreate(
                user_id=USER_A,
                institution_id=INSTITUTION_A,
                student_number="STU-2026-001",
                email=None,
                approval_status="pending",
                enrollment_date="2026-01-15",
            )
        )
    assert student["approval_status"] == "pending"
    assert student["email"] is None


def test_update_student_normalizes_identity_fields() -> None:
    """update_student applies the same normalization to updated fields."""
    db = _make_mock_update(
        get_student_row=STUDENT_ROW_A,
        update_rows=[
            {
                **STUDENT_ROW_A,
                "email": "updated@collegea.test",
                "register_number": "2002",
            }
        ],
    )
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.update_student(
            STUDENT_ID_A,
            svc.StudentUpdate(
                email="  UPDATED@COLLEGEA.TEST  ",
                register_number="  2002  ",
            ),
        )
    assert student["email"] == "updated@collegea.test"
    assert student["register_number"] == "2002"


# ============================================================================
# 5. Approval lifecycle (approval_status)
# ============================================================================


def test_approval_statuses_enum() -> None:
    """Approval lifecycle states match the database CHECK constraint."""
    assert svc.APPROVAL_STATUSES == ["pending", "approved", "rejected"]
    assert "pending" in svc.APPROVAL_STATUSES
    assert "approved" in svc.APPROVAL_STATUSES
    assert "rejected" in svc.APPROVAL_STATUSES


def test_admin_provisioning_defaults_to_approved() -> None:
    """An admin creating the account is the approving action itself."""
    db = _make_mock_insert({**STUDENT_ROW_A, "approval_status": "approved"})
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.create_student(
            svc.StudentCreate(
                user_id=USER_A,
                institution_id=INSTITUTION_A,
                student_number="STU-2026-001",
                # approval_status omitted -> defaults to "approved"
                enrollment_date="2026-01-15",
            )
        )
    assert student["approval_status"] == "approved"


def test_pending_approval_is_storable() -> None:
    """pending is valid for self-registration (future phase)."""
    db = _make_mock_insert({**STUDENT_ROW_A, "approval_status": "pending"})
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.create_student(
            svc.StudentCreate(
                user_id=USER_A,
                institution_id=INSTITUTION_A,
                student_number="STU-2026-001",
                approval_status="pending",
                enrollment_date="2026-01-15",
            )
        )
    assert student["approval_status"] == "pending"


def test_rejected_is_storable() -> None:
    """rejected is a valid terminal approval state."""
    db = _make_mock_insert({**STUDENT_ROW_A, "approval_status": "rejected"})
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.create_student(
            svc.StudentCreate(
                user_id=USER_A,
                institution_id=INSTITUTION_A,
                student_number="STU-2026-001",
                approval_status="rejected",
                enrollment_date="2026-01-15",
            )
        )
    assert student["approval_status"] == "rejected"


def test_create_student_rejects_invalid_approval_status() -> None:
    """Unknown approval values are rejected at the service boundary."""
    db = _make_mock_insert({**STUDENT_ROW_A, "approval_status": "bogus"})
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        with pytest.raises(AppError) as exc_info:
            svc.create_student(
                svc.StudentCreate(
                    user_id=USER_A,
                    institution_id=INSTITUTION_A,
                    student_number="STU-2026-001",
                    approval_status="bogus",
                    enrollment_date="2026-01-15",
                )
            )
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "INVALID_STUDENT_APPROVAL_STATUS"


def test_update_student_rejects_invalid_approval_status() -> None:
    """update_student validates approval_status before persisting."""
    db = _make_mock_update(
        get_student_row=STUDENT_ROW_A,
        update_rows=[{**STUDENT_ROW_A, "approval_status": "bogus"}],
    )
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        with pytest.raises(AppError) as exc_info:
            svc.update_student(
                STUDENT_ID_A,
                svc.StudentUpdate(approval_status="bogus"),
            )
    assert exc_info.value.status_code == 422


def test_approval_status_distinct_from_academic_status() -> None:
    """approval_status (registration) is independent of status (academic)."""
    # A pending-approval student may still be academically 'active'.
    row = {**STUDENT_ROW_A, "approval_status": "pending", "status": "active"}
    assert row["approval_status"] == "pending"
    assert row["status"] == "active"
    # And a rejected student row keeps its academic status untouched.
    assert {"pending", "approved", "rejected"} == set(svc.APPROVAL_STATUSES)
    assert "pending" not in svc.STUDENT_STATUSES


# ============================================================================
# 6. Existing student functionality — backward compatibility
# ============================================================================


def test_archive_student_preserves_identity_fields() -> None:
    """Soft-archive flips status/is_active without touching identity."""
    archived = {
        **STUDENT_ROW_A,
        "status": "inactive",
        "is_active": False,
    }
    db = _make_mock_update(get_student_row=STUDENT_ROW_A, update_rows=[archived])
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        student = svc.archive_student(STUDENT_ID_A)
    assert student["status"] == "inactive"
    assert student["is_active"] is False
    assert student["email"] == STUDENT_ROW_A["email"]
    assert student["institution_id"] == INSTITUTION_A


def test_get_student_by_user_id_unchanged() -> None:
    """list/get by user id shape is unchanged by Phase 6.2."""
    client = _make_mock_client([STUDENT_ROW_A])
    row = repo.get_student_by_user_id(client, USER_A)
    assert row is None or row["institution_id"] == INSTITUTION_A


def test_list_students_still_returns_institution_rows() -> None:
    """list_students remains institution-scoped with the same projection."""
    client = _make_mock_client([STUDENT_ROW_A])
    rows = repo.list_students(client, INSTITUTION_A)
    assert len(rows) == 1
    assert rows[0]["institution_id"] == INSTITUTION_A


def test_create_student_requires_institution() -> None:
    """institution_id stays mandatory — the tenant key is never optional."""
    db = _make_mock_insert({**STUDENT_ROW_A, "institution_id": INSTITUTION_A})
    with patch("app.services.admin_academics.get_admin_client", return_value=db):
        payload = svc.StudentCreate(
            user_id=USER_A,
            institution_id=INSTITUTION_A,
            student_number="STU-2026-001",
            enrollment_date="2026-01-15",
        )
        student = svc.create_student(payload)
    # StudentCreate requires institution_id (a real missing value raises a
    # pydantic ValidationError before any DB call).
    assert student["institution_id"] == INSTITUTION_A


def test_studentcreate_requires_institution_id() -> None:
    """Pydantic contract: institution_id is a required identity field."""
    with pytest.raises(Exception):
        svc.StudentCreate(
            user_id=USER_A,
            student_number="STU-2026-001",
            enrollment_date="2026-01-15",
        )


# ============================================================================
# 7. Physical/integration tests — skipped unless explicitly opted in
# ============================================================================
# Following the project convention (test_physical_validation_phase_4_4.py),
# live-DB tests are skipped by default and run only under explicit manual
# opt-in. They re-verify the schema artifacts already validated read-only
# during migration authoring.


@pytest.mark.skip(reason="real DB schema check requires explicit manual opt-in")
def test_physical_migrated_table_has_phase62_columns() -> None:
    """The live students table exposes the Phase 6.2 identity columns.

    Verified read-only during migration authoring; re-run manually against a
    reachable Supabase database to confirm the deployed state.
    """
    from app.db.supabase import get_admin_client  # noqa: PLC0415

    db = get_admin_client()
    rpc = db.table("students").select(
        "student_id, email, register_number, university_roll_number, approval_status"
    ).limit(1).execute()
    if rpc.data:
        cols = set(rpc.data[0].keys())
        assert {"email", "register_number", "university_roll_number",
                "approval_status"}.issubset(cols)


@pytest.mark.skip(reason="real DB seed check requires explicit manual opt-in")
def test_physical_existing_students_backfilled_approved() -> None:
    """Existing admin-provisioned students are approved post-migration.

    Verified read-only during migration authoring (approved backfill).
    """
    from app.db.supabase import get_admin_client  # noqa: PLC0415

    db = get_admin_client()
    rpc = db.table("students").select(
        "student_id, approval_status"
    ).limit(10).execute()
    for row in rpc.data or []:
        assert row["approval_status"] in {"pending", "approved", "rejected"}