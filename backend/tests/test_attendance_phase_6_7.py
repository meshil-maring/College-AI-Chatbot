"""Phase 6.7 — Attendance data tests.

Covers the attendance foundation built on the locked Phase 6.1-6.6 identity,
tenant, authentication, and RBAC baseline:

  * schema / database contract (columns, constraints, indexes, trigger guard)
  * creation, read, update, delete behavior for authorized admin
  * role enforcement (staff/faculty/student -> 403; unauthenticated -> 401)
  * tenant isolation (institution A cannot touch institution B)
  * platform-admin global authority retained; platform staff stays non-global
  * student self-service strictly scoped to the JWT-derived profile
  * input validation (status, UUIDs, dates, required fields, unexpected fields)
  * academic-context validation (section existence, offering match)
  * duplicate / concurrency protection at the database level

Physical (live-database) constraint verification lives in a skip-by-default
class at the bottom of this file, mirroring the project's existing
``test_physical_validation_phase_4_4.py`` opt-in convention.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.repositories import attendance as attendance_repo
from app.repositories.admin_academics import STUDENT_ATTENDANCE_COLUMNS
from app.services import attendance as attendance_svc
from app.services.admin_academics import (
    ATTENDANCE_STATUSES,
    AttendanceCreate,
    AttendanceUpdate,
)

client = TestClient(app, raise_server_exceptions=False)

# ----------------------------------------------------------------------------
# Shared constants & helpers
# ----------------------------------------------------------------------------

TENANT_A = "a1111111-0000-0000-0000-000000000001"
TENANT_B = "b2222222-0000-0000-0000-000000000002"
STUDENT_A = "30000000-0000-0000-0000-000000000151"
STUDENT_B = "30000000-0000-0000-0000-000000000152"
AY_ID = "a0000000-0000-0000-0000-0000000000a1"
SEM_ID = "a0000000-0000-0000-0000-0000000000b1"
SECTION_A = "30000000-0000-0000-0000-000000000099"
ATTENDANCE_ID = "a0000000-0000-0000-0000-0000000000c1"

_ROOT = Path(__file__).resolve().parents[2]
PHASE_6_7_MIGRATION = (
    _ROOT / "supabase" / "migrations" / "20260913000000_phase_6_7_attendance.sql"
)


def _user(tenant=None, roles=("admin",)):
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "attendance@example.com",
        "roles": list(roles),
        "institution_id": tenant,
    }


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def clean_overrides():
    yield
    _clear()


def _student_context(student_id: str, institution_id: str) -> dict:
    return {"student_id": student_id, "institution_id": institution_id, "program_id": None}


def _section_context(institution_id: str, ay_id: str = AY_ID, sem_id: str = SEM_ID) -> dict:
    return {
        "section_id": SECTION_A,
        "section_code": "AIDS-CS101-A",
        "academic_year_id": ay_id,
        "semester_id": sem_id,
        "program_id": None,
        "course_id": None,
        "institution_id": institution_id,
    }


def _attendance_row(**overrides) -> dict:
    row = {
        "student_attendance_id": ATTENDANCE_ID,
        "student_id": STUDENT_A,
        "institution_id": TENANT_A,
        "section_id": SECTION_A,
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "date": "2026-09-01",
        "status": "present",
        "notes": None,
        "created_at": "2026-09-01T10:00:00+00:00",
        "updated_at": "2026-09-01T10:00:00+00:00",
    }
    row.update(overrides)
    return row


def _create_payload(**overrides) -> dict:
    payload = {
        "student_id": STUDENT_A,
        "section_id": SECTION_A,
        "academic_year_id": AY_ID,
        "semester_id": SEM_ID,
        "date": "2026-09-01",
        "status": "present",
    }
    payload.update(overrides)
    return payload


def _audit_db():
    db = MagicMock()
    audit = MagicMock(data=[{"audit_id": str(uuid4())}])
    db.table.return_value.insert.return_value.execute.return_value = audit
    return db


def _context_patches(institution_id=TENANT_A, ay_id=AY_ID, sem_id=SEM_ID, section=None, student=None):
    return (
        patch(
            "app.repositories.attendance.get_student_context",
            return_value=student or _student_context(STUDENT_A, institution_id),
        ),
        patch(
            "app.repositories.attendance.get_section_academic_context",
            return_value=section if section is not None else _section_context(institution_id, ay_id, sem_id),
        ),
    )


# ============================================================================
# DATABASE — schema contract
# ============================================================================


def test_attendance_projection_includes_phase67_columns() -> None:
    assert "institution_id" in STUDENT_ATTENDANCE_COLUMNS
    assert "updated_at" in STUDENT_ATTENDANCE_COLUMNS
    assert [c.strip() for c in STUDENT_ATTENDANCE_COLUMNS.split(",")][0] == "student_attendance_id"


def test_attendance_statuses_match_controlled_vocabulary() -> None:
    assert ATTENDANCE_STATUSES == ["present", "absent", "late", "excused"]


def test_migration_defines_tenant_and_academic_guard_ddl() -> None:
    sql = PHASE_6_7_MIGRATION.read_text(encoding="utf-8")
    # The migration must NOT create a duplicate attendance table.
    assert "CREATE TABLE" not in sql
    # institution_id column + institutions FK.
    assert 'ADD COLUMN "institution_id"' in sql
    assert "student_attendance_institution_id_fkey" in sql
    assert 'REFERENCES "public"."institutions"' in sql
    # updated_at follows the project convention.
    assert 'ADD COLUMN "updated_at"' in sql
    # Guard trigger enforcing tenant / academic-context / ownership invariants.
    assert "student_attendance_tenant_guard" in sql
    assert "BEFORE INSERT OR UPDATE" in sql
    assert "attendance academic context must match the section offering" in sql
    assert "attendance ownership fields cannot be changed" in sql


def test_migration_preserves_duplicate_prevention_unique_constraint() -> None:
    """The (student_id, section_id, date) uniqueness rule is the duplicate
    protection and it must be retained (it is defined in the locked Phase
    Admin-1 migration)."""
    admin1 = (
        _ROOT / "supabase" / "migrations" / "20260909000000_phase_admin_1_admin_student_schema.sql"
    ).read_text(encoding="utf-8")
    assert "student_attendance_student_section_date_key" in admin1
    assert 'UNIQUE ("student_id", "section_id", date)' in admin1


# ============================================================================
# CREATION — service behavior
# ============================================================================


def test_create_attendance_derives_tenant_server_side() -> None:
    """institution_id on the row comes from the STUDENT record, never the
    client payload (AttendanceCreate has no institution_id field)."""
    db = MagicMock()
    created = _attendance_row()
    p_student, p_section = _context_patches(institution_id=TENANT_A)
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        p_student,
        p_section,
        patch(
            "app.repositories.attendance.insert_attendance",
            return_value=created,
        ) as insert_mock,
    ):
        result = attendance_svc.create_attendance(
            AttendanceCreate(**_create_payload())
        )

    assert result["student_attendance_id"] == ATTENDANCE_ID
    row = insert_mock.call_args.args[1]
    assert row["institution_id"] == TENANT_A
    assert row["student_id"] == STUDENT_A
    assert row["status"] == "present"
    assert row["date"] == "2026-09-01"


def test_create_attendance_rejects_invalid_status() -> None:
    with pytest.raises(AppError) as exc:
        attendance_svc.create_attendance(
            AttendanceCreate(**_create_payload(status="bogus"))
        )
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_ATTENDANCE_STATUS"


def test_create_attendance_student_not_found() -> None:
    db = MagicMock()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch("app.repositories.attendance.get_student_context", return_value=None),
        patch("app.repositories.attendance.insert_attendance") as insert_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.create_attendance(
                AttendanceCreate(**_create_payload())
            )
    assert exc.value.status_code == 404
    assert exc.value.code == "STUDENT_NOT_FOUND"
    insert_mock.assert_not_called()


def test_create_attendance_section_not_found() -> None:
    db = MagicMock()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.get_student_context",
            return_value=_student_context(STUDENT_A, TENANT_A),
        ),
        patch("app.repositories.attendance.get_section_academic_context", return_value=None),
        patch("app.repositories.attendance.insert_attendance") as insert_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.create_attendance(
                AttendanceCreate(**_create_payload())
            )
    assert exc.value.status_code == 404
    assert exc.value.code == "SECTION_NOT_FOUND"
    insert_mock.assert_not_called()


def test_create_attendance_section_with_unresolvable_context_is_rejected() -> None:
    db = MagicMock()
    # Section exists but the offering chain is broken -> fail closed.
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.get_student_context",
            return_value=_student_context(STUDENT_A, TENANT_A),
        ),
        patch(
            "app.repositories.attendance.get_section_academic_context",
            return_value={
                "section_id": SECTION_A,
                "section_code": "X",
                "academic_year_id": None,
                "semester_id": None,
                "program_id": None,
                "course_id": None,
                "institution_id": None,
            },
        ),
        patch("app.repositories.attendance.insert_attendance") as insert_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.create_attendance(AttendanceCreate(**_create_payload()))
    assert exc.value.status_code == 404
    assert exc.value.code == "SECTION_NOT_FOUND"
    insert_mock.assert_not_called()


def test_create_attendance_rejects_cross_institution_section() -> None:
    db = MagicMock()
    p_student, p_section = _context_patches(
        student=_student_context(STUDENT_A, TENANT_A), section=_section_context(TENANT_B)
    )
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        p_student,
        p_section,
        patch("app.repositories.attendance.insert_attendance") as insert_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.create_attendance(AttendanceCreate(**_create_payload()))
    assert exc.value.status_code == 403
    assert exc.value.code == "TENANT_MISMATCH"
    insert_mock.assert_not_called()


def test_create_attendance_rejects_academic_context_mismatch() -> None:
    """The section's offering is AY_ID/SEM_ID; a payload for a different
    semester must be rejected before insertion."""
    db = MagicMock()
    other_sem = "a0000000-0000-0000-0000-0000000000b2"
    p_student, p_section = _context_patches(institution_id=TENANT_A)
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        p_student,
        p_section,
        patch("app.repositories.attendance.insert_attendance") as insert_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.create_attendance(
                AttendanceCreate(**_create_payload(semester_id=other_sem))
            )
    assert exc.value.status_code == 422
    assert exc.value.code == "ACADEMIC_CONTEXT_MISMATCH"
    insert_mock.assert_not_called()


def test_create_attendance_duplicate_maps_to_conflict() -> None:
    db = MagicMock()
    p_student, p_section = _context_patches(institution_id=TENANT_A)
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        p_student,
        p_section,
        patch(
            "app.repositories.attendance.insert_attendance",
            side_effect=Exception(
                'duplicate key value violates unique constraint '
                '"student_attendance_student_section_date_key" (SQLSTATE 23505)'
            ),
        ),
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.create_attendance(AttendanceCreate(**_create_payload()))
    assert exc.value.status_code == 409
    assert exc.value.code == "ATTENDANCE_DUPLICATE"


def test_create_attendance_other_insert_errors_are_generic_conflict() -> None:
    db = MagicMock()
    p_student, p_section = _context_patches(institution_id=TENANT_A)
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        p_student,
        p_section,
        patch(
            "app.repositories.attendance.insert_attendance",
            side_effect=Exception("some unrelated database failure"),
        ),
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.create_attendance(AttendanceCreate(**_create_payload()))
    assert exc.value.status_code == 409
    assert exc.value.code == "ATTENDANCE_CREATE_FAILED"


def test_admin_academics_create_attendance_delegates_to_phase67_service() -> None:
    """Backward-compat entrypoint used by the Phase Admin-3 surface."""
    from app.services import admin_academics as legacy

    created = _attendance_row()
    with patch("app.services.attendance.create_attendance", return_value=created) as svc_mock:
        result = legacy.create_attendance(AttendanceCreate(**_create_payload()))
    assert result == created
    svc_mock.assert_called_once()


# ============================================================================
# READ / UPDATE / DELETE — service behavior
# ============================================================================


def test_get_attendance_returns_row() -> None:
    db = MagicMock()
    row = _attendance_row()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.get_attendance_row",
            return_value=row,
        ) as get_mock,
    ):
        result = attendance_svc.get_attendance(ATTENDANCE_ID)
    assert result == row
    get_mock.assert_called_once_with(db, ATTENDANCE_ID)


def test_get_attendance_404_when_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch("app.repositories.attendance.get_attendance_row", return_value=None),
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.get_attendance(ATTENDANCE_ID)
    assert exc.value.status_code == 404
    assert exc.value.code == "ATTENDANCE_NOT_FOUND"


def test_list_attendance_for_student_delegates_with_filters() -> None:
    db = MagicMock()
    rows = [_attendance_row()]
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.list_attendance",
            return_value=rows,
        ) as list_mock,
    ):
        result = attendance_svc.list_attendance_for_student(
            STUDENT_A,
            academic_year_id=AY_ID,
            semester_id=SEM_ID,
            date_from="2026-08-01",
            date_to="2026-09-30",
            limit=50,
        )
    assert result == rows
    assert list_mock.call_args.args[1] == STUDENT_A
    assert list_mock.call_args.kwargs["academic_year_id"] == AY_ID
    assert list_mock.call_args.kwargs["date_from"] == "2026-08-01"


def test_update_attendance_updates_status_and_notes_only() -> None:
    db = MagicMock()
    existing = _attendance_row()
    updated = _attendance_row(status="absent", notes="updated")
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.get_attendance_row",
            return_value=existing,
        ),
        patch(
            "app.repositories.attendance.update_attendance_row",
            return_value=updated,
        ) as upd_mock,
    ):
        result = attendance_svc.update_attendance(
            ATTENDANCE_ID,
            AttendanceUpdate(status="absent", notes="updated"),
        )
    assert result["status"] == "absent"
    args, kwargs = upd_mock.call_args
    fields = args[2] if len(args) > 2 else kwargs.get("fields")
    assert set(fields) == {"status", "notes"}


def test_update_attendance_404_when_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch("app.repositories.attendance.get_attendance_row", return_value=None),
        patch("app.repositories.attendance.update_attendance_row") as upd_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.update_attendance(ATTENDANCE_ID, AttendanceUpdate(status="absent"))
    assert exc.value.status_code == 404
    assert exc.value.code == "ATTENDANCE_NOT_FOUND"
    upd_mock.assert_not_called()


def test_update_attendance_empty_payload_rejected() -> None:
    db = MagicMock()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.get_attendance_row",
            return_value=_attendance_row(),
        ),
        patch("app.repositories.attendance.update_attendance_row") as upd_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.update_attendance(ATTENDANCE_ID, AttendanceUpdate())
    assert exc.value.status_code == 422
    assert exc.value.code == "EMPTY_UPDATE"
    upd_mock.assert_not_called()


def test_update_attendance_invalid_status_rejected() -> None:
    db = MagicMock()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.get_attendance_row",
            return_value=_attendance_row(),
        ),
        patch("app.repositories.attendance.update_attendance_row") as upd_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.update_attendance(ATTENDANCE_ID, AttendanceUpdate(status="bogus"))
    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_ATTENDANCE_STATUS"
    upd_mock.assert_not_called()


def test_delete_attendance_deletes_existing() -> None:
    db = MagicMock()
    existing = _attendance_row()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch(
            "app.repositories.attendance.get_attendance_row",
            return_value=existing,
        ),
        patch("app.repositories.attendance.delete_attendance_row") as del_mock,
    ):
        result = attendance_svc.delete_attendance(ATTENDANCE_ID)
    assert result == existing
    del_mock.assert_called_once_with(db, ATTENDANCE_ID)


def test_delete_attendance_404_when_missing() -> None:
    db = MagicMock()
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch("app.repositories.attendance.get_attendance_row", return_value=None),
        patch("app.repositories.attendance.delete_attendance_row") as del_mock,
    ):
        with pytest.raises(AppError) as exc:
            attendance_svc.delete_attendance(ATTENDANCE_ID)
    assert exc.value.status_code == 404
    assert exc.value.code == "ATTENDANCE_NOT_FOUND"
    del_mock.assert_not_called()


# ============================================================================
# CONCURRENCY — database-level duplicate protection
# ============================================================================


def test_concurrent_duplicate_creates_single_record() -> None:
    """Two concurrent creates for the same (student, section, date) race: the
    database unique constraint lets exactly one insert succeed and the other
    surfaces as ATTENDANCE_DUPLICATE. The service maps the DB-enforced race
    correctly and never returns a second row."""
    db = MagicMock()
    state = {"inserted": 0}
    lock = threading.Lock()

    def fake_insert(_client, row):
        with lock:
            state["inserted"] += 1
            if state["inserted"] > 1:
                raise Exception(
                    'duplicate key value violates unique constraint '
                    '"student_attendance_student_section_date_key" (SQLSTATE 23505)'
                )
        return _attendance_row(**row)

    barrier = threading.Barrier(2)

    def attempt():
        barrier.wait()
        try:
            attendance_svc.create_attendance(AttendanceCreate(**_create_payload()))
            return "ok"
        except AppError as exc:
            return exc.code

    p_student, p_section = _context_patches(institution_id=TENANT_A)
    with (
        patch("app.services.attendance.get_admin_client", return_value=db),
        p_student,
        p_section,
        patch("app.repositories.attendance.insert_attendance", side_effect=fake_insert),
    ):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = sorted(pool.map(lambda _: attempt(), range(2)))

    assert results == ["ATTENDANCE_DUPLICATE", "ok"]


# ============================================================================
# API — authentication & roles
# ============================================================================


def test_unauthenticated_attendance_endpoints_are_401() -> None:
    _clear()
    try:
        statuses = [
            client.get(f"/api/v1/admin/students/{STUDENT_A}/attendance").status_code,
            client.post("/api/v1/admin/attendance", json={}).status_code,
            client.patch(f"/api/v1/admin/attendance/{ATTENDANCE_ID}", json={}).status_code,
            client.delete(f"/api/v1/admin/attendance/{ATTENDANCE_ID}").status_code,
            client.get("/api/v1/students/me/attendance").status_code,
        ]
    finally:
        _clear()
    assert statuses == [401, 401, 401, 401, 401]


def test_staff_cannot_manage_attendance() -> None:
    _as(_user(TENANT_A, roles=("staff",)))
    with patch("app.api.admin.attendance.create_attendance") as create_mock:
        try:
            r1 = client.post("/api/v1/admin/attendance", json=_create_payload())
            r2 = client.get(f"/api/v1/admin/students/{STUDENT_A}/attendance")
            r3 = client.patch(f"/api/v1/admin/attendance/{ATTENDANCE_ID}", json={"status": "absent"})
            r4 = client.delete(f"/api/v1/admin/attendance/{ATTENDANCE_ID}")
        finally:
            _clear()
    assert (r1.status_code, r2.status_code, r3.status_code, r4.status_code) == (403, 403, 403, 403)
    for resp in (r1, r2, r3, r4):
        assert resp.json()["error"]["code"] == "FORBIDDEN"
    create_mock.assert_not_called()


def test_faculty_cannot_manage_attendance() -> None:
    _as(_user(TENANT_A, roles=("faculty",)))
    with patch("app.api.admin.attendance.create_attendance") as create_mock:
        try:
            r1 = client.post("/api/v1/admin/attendance", json=_create_payload())
            r2 = client.get(f"/api/v1/admin/students/{STUDENT_A}/attendance")
        finally:
            _clear()
    assert (r1.status_code, r2.status_code) == (403, 403)
    create_mock.assert_not_called()


def test_student_cannot_manage_attendance() -> None:
    _as(_user(TENANT_A, roles=("student",)))
    with patch("app.api.admin.attendance.create_attendance") as create_mock:
        try:
            r1 = client.post("/api/v1/admin/attendance", json=_create_payload())
            r2 = client.get(f"/api/v1/admin/students/{STUDENT_A}/attendance")
            r3 = client.patch(f"/api/v1/admin/attendance/{ATTENDANCE_ID}", json={"status": "absent"})
            r4 = client.delete(f"/api/v1/admin/attendance/{ATTENDANCE_ID}")
        finally:
            _clear()
    assert (r1.status_code, r2.status_code, r3.status_code, r4.status_code) == (403, 403, 403, 403)
    create_mock.assert_not_called()


# ============================================================================
# API — tenant isolation & platform policy
# ============================================================================


def test_admin_can_create_own_tenant_attendance() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    created = _attendance_row()
    db = _audit_db()
    with (
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_A, TENANT_A),
        ),
        patch("app.api.admin.attendance.create_attendance", return_value=created),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        try:
            resp = client.post("/api/v1/admin/attendance", json=_create_payload())
        finally:
            _clear()
    assert resp.status_code == 201
    assert resp.json()["student_attendance_id"] == ATTENDANCE_ID
    audit_calls = [
        call.args[0]
        for call in db.table.return_value.insert.call_args_list
        if call.args and "action" in call.args[0]
    ]
    assert audit_calls and audit_calls[0]["action"] == "attendance.create"


def test_admin_cannot_create_foreign_tenant_student() -> None:
    """Institution-A admin cannot create attendance for an institution-B
    student; the tenant guard fails before the service is reached."""
    _as(_user(TENANT_A, roles=("admin",)))
    with (
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_B, TENANT_B),
        ),
        patch("app.api.admin.attendance.create_attendance") as create_mock,
    ):
        try:
            resp = client.post(
                "/api/v1/admin/attendance",
                json=_create_payload(student_id=STUDENT_B),
            )
        finally:
            _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    create_mock.assert_not_called()


def test_admin_cannot_list_foreign_tenant_student() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    with (
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_B, TENANT_B),
        ),
        patch("app.api.admin.attendance.list_attendance_for_student") as list_mock,
    ):
        try:
            resp = client.get(f"/api/v1/admin/students/{STUDENT_B}/attendance")
        finally:
            _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    list_mock.assert_not_called()


def test_admin_cannot_update_foreign_tenant_attendance() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    foreign_row = _attendance_row(student_id=STUDENT_B)
    with (
        patch("app.api.admin.attendance.get_attendance", return_value=foreign_row),
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_B, TENANT_B),
        ),
        patch("app.api.admin.attendance.update_attendance") as update_mock,
    ):
        try:
            resp = client.patch(
                f"/api/v1/admin/attendance/{ATTENDANCE_ID}", json={"status": "absent"}
            )
        finally:
            _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    update_mock.assert_not_called()


def test_admin_cannot_delete_foreign_tenant_attendance() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    foreign_row = _attendance_row(student_id=STUDENT_B)
    with (
        patch("app.api.admin.attendance.get_attendance", return_value=foreign_row),
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_B, TENANT_B),
        ),
        patch("app.api.admin.attendance.delete_attendance") as delete_mock,
    ):
        try:
            resp = client.delete(f"/api/v1/admin/attendance/{ATTENDANCE_ID}")
        finally:
            _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    delete_mock.assert_not_called()


def test_admin_can_update_own_tenant_attendance() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    row = _attendance_row()
    updated = _attendance_row(status="excused")
    db = _audit_db()
    with (
        patch("app.api.admin.attendance.get_attendance", return_value=row),
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_A, TENANT_A),
        ),
        patch("app.api.admin.attendance.update_attendance", return_value=updated),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        try:
            resp = client.patch(
                f"/api/v1/admin/attendance/{ATTENDANCE_ID}", json={"status": "excused"}
            )
        finally:
            _clear()
    assert resp.status_code == 200
    assert resp.json()["status"] == "excused"


def test_admin_can_delete_own_tenant_attendance() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    row = _attendance_row()
    db = _audit_db()
    with (
        patch("app.api.admin.attendance.get_attendance", return_value=row),
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_A, TENANT_A),
        ),
        patch("app.api.admin.attendance.delete_attendance", return_value=row),
        patch("app.api.admin.get_admin_client", return_value=db),
    ):
        try:
            resp = client.delete(f"/api/v1/admin/attendance/{ATTENDANCE_ID}")
        finally:
            _clear()
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_platform_admin_retains_global_attendance_authority() -> None:
    _as(_user(None, roles=("admin",)))
    with patch(
        "app.api.admin.attendance.list_attendance_for_student",
        return_value=[_attendance_row()],
    ) as list_mock:
        try:
            resp = client.get(f"/api/v1/admin/students/{STUDENT_B}/attendance")
        finally:
            _clear()
    assert resp.status_code == 200
    assert str(list_mock.call_args.args[0]) == STUDENT_B


def test_platform_staff_does_not_gain_global_attendance_authority() -> None:
    _as(_user(None, roles=("staff",)))
    with patch("app.api.admin.attendance.list_attendance_for_student") as list_mock:
        try:
            resp = client.get(f"/api/v1/admin/students/{STUDENT_B}/attendance")
        finally:
            _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    list_mock.assert_not_called()


# ============================================================================
# API — input validation
# ============================================================================


def test_create_rejects_malformed_uuids() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    with patch("app.api.admin.attendance.create_attendance") as create_mock:
        try:
            resp = client.post(
                "/api/v1/admin/attendance",
                json=_create_payload(student_id="not-a-uuid"),
            )
        finally:
            _clear()
    assert resp.status_code == 422
    create_mock.assert_not_called()


def test_create_rejects_invalid_date() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    with patch("app.api.admin.attendance.create_attendance") as create_mock:
        try:
            resp = client.post(
                "/api/v1/admin/attendance",
                json=_create_payload(date="2026-13-01"),
            )
        finally:
            _clear()
    assert resp.status_code == 422
    create_mock.assert_not_called()


def test_create_rejects_missing_required_fields() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    with patch("app.api.admin.attendance.create_attendance") as create_mock:
        try:
            resp = client.post(
                "/api/v1/admin/attendance",
                json={"student_id": STUDENT_A, "status": "present"},
            )
        finally:
            _clear()
    assert resp.status_code == 422
    create_mock.assert_not_called()


def test_create_rejects_unexpected_control_fields() -> None:
    """institution_id / role / created_by / approval_status are control fields
    that must be server-derived; any client attempt is rejected outright."""
    _as(_user(TENANT_A, roles=("admin",)))
    with patch("app.api.admin.attendance.create_attendance") as create_mock:
        try:
            resp = client.post(
                "/api/v1/admin/attendance",
                json=_create_payload(
                    institution_id=TENANT_B,
                    role="admin",
                    created_by=str(uuid4()),
                    approval_status="approved",
                ),
            )
        finally:
            _clear()
    assert resp.status_code == 422
    create_mock.assert_not_called()


def test_update_rejects_ownership_injection() -> None:
    """PATCH may only carry status/notes; student_id / institution_id /
    section_id injection attempts are schema-rejected."""
    _as(_user(TENANT_A, roles=("admin",)))
    with (
        patch("app.api.admin.attendance.get_attendance", return_value=_attendance_row()),
        patch("app.api.admin.attendance.update_attendance") as update_mock,
    ):
        try:
            resp_ownership = client.patch(
                f"/api/v1/admin/attendance/{ATTENDANCE_ID}",
                json={"student_id": STUDENT_B},
            )
            resp_tenant = client.patch(
                f"/api/v1/admin/attendance/{ATTENDANCE_ID}",
                json={"institution_id": TENANT_B},
            )
        finally:
            _clear()
    assert resp_ownership.status_code == 422
    assert resp_tenant.status_code == 422
    update_mock.assert_not_called()


def test_update_rejects_empty_payload() -> None:
    """PATCH with {} reaches the real service, which rejects it as EMPTY_UPDATE
    (422) before any database write or audit entry."""
    _as(_user(TENANT_A, roles=("admin",)))
    row = _attendance_row()
    db = MagicMock()
    with (
        patch("app.api.admin.attendance.get_attendance", return_value=row),
        patch(
            "app.services.admin_academics.get_student",
            return_value=_student_context(STUDENT_A, TENANT_A),
        ),
        patch("app.services.attendance.get_admin_client", return_value=db),
        patch("app.repositories.attendance.get_attendance_row", return_value=row),
        patch("app.repositories.attendance.update_attendance_row") as upd_mock,
    ):
        try:
            resp = client.patch(f"/api/v1/admin/attendance/{ATTENDANCE_ID}", json={})
        finally:
            _clear()
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "EMPTY_UPDATE"
    upd_mock.assert_not_called()


def test_attendance_404_when_missing_on_read_path() -> None:
    _as(_user(TENANT_A, roles=("admin",)))
    missing = AppError(
        "Attendance record not found", status_code=404, code="ATTENDANCE_NOT_FOUND"
    )
    with (
        patch("app.api.admin.attendance.get_attendance", side_effect=missing),
        patch("app.api.admin.attendance.update_attendance") as update_mock,
        patch("app.api.admin.attendance.delete_attendance") as delete_mock,
    ):
        try:
            resp_update = client.patch(
                f"/api/v1/admin/attendance/{ATTENDANCE_ID}", json={"status": "absent"}
            )
            resp_delete = client.delete(f"/api/v1/admin/attendance/{ATTENDANCE_ID}")
        finally:
            _clear()
    assert resp_update.status_code == 404
    assert resp_update.json()["error"]["code"] == "ATTENDANCE_NOT_FOUND"
    assert resp_delete.status_code == 404
    assert resp_delete.json()["error"]["code"] == "ATTENDANCE_NOT_FOUND"
    update_mock.assert_not_called()
    delete_mock.assert_not_called()


# ============================================================================
# STUDENT SELF-SERVICE — strictly own-attendance, never client-selected
# ============================================================================

STUDENT_USER_ID = "71000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "71000000-0000-0000-0000-000000000002"


def _student_user(user_id: str = STUDENT_USER_ID):
    return {
        "user_id": user_id,
        "auth_user_id": str(uuid4()),
        "email": "student@example.com",
        "roles": ["student"],
        "institution_id": TENANT_A,
    }


def _resolved_db():
    """Mock DB whose students lookup resolves the JWT user to a profile."""
    db = MagicMock()
    student_row = {
        "student_id": STUDENT_A,
        "user_id": STUDENT_USER_ID,
        "institution_id": TENANT_A,
        "program_id": None,
        "student_number": "S100",
        "status": "active",
        "is_active": True,
    }
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=student_row)
    return db


def test_student_can_read_own_attendance() -> None:
    _as(_student_user())
    db = _resolved_db()
    rows = [_attendance_row()]
    with (
        patch("app.services.student_data.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin_academics.list_student_attendance",
            return_value=rows,
        ) as list_mock,
    ):
        try:
            resp = client.get("/api/v1/students/me/attendance")
        finally:
            _clear()
    assert resp.status_code == 200
    assert resp.json()[0]["student_id"] == STUDENT_A
    assert list_mock.call_args.args[1] == STUDENT_A


def test_student_me_attendance_ignores_client_supplied_identity() -> None:
    """The endpoint never accepts a client-selected student_id/institution_id:
    identity always resolves from the JWT."""
    _as(_student_user())
    db = _resolved_db()
    with (
        patch("app.services.student_data.get_admin_client", return_value=db),
        patch(
            "app.repositories.admin_academics.list_student_attendance",
            return_value=[],
        ) as list_mock,
    ):
        try:
            resp = client.get(
                "/api/v1/students/me/attendance",
                params={
                    "student_id": STUDENT_B,
                    "institution_id": TENANT_B,
                },
            )
        finally:
            _clear()
    assert resp.status_code == 200
    assert list_mock.call_args.args[1] == STUDENT_A
    db.table.return_value.select.return_value.eq.assert_called_once_with(
        "user_id", STUDENT_USER_ID
    )


def test_student_me_attendance_404_without_profile() -> None:
    """A JWT that has no student profile gets 404 — never another student's
    attendance and never an empty list for a foreign identity."""
    _as(_student_user())
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=None)
    with patch("app.services.student_data.get_admin_client", return_value=db):
        try:
            resp = client.get("/api/v1/students/me/attendance")
        finally:
            _clear()
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


def test_student_user_cannot_read_another_students_attendance() -> None:
    """A different JWT resolves to a different (or no) profile — it can never
    select STUDENT_A's rows."""
    _as(_student_user(OTHER_USER_ID))
    db = MagicMock()
    (
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=None)
    with patch("app.services.student_data.get_admin_client", return_value=db):
        try:
            resp = client.get("/api/v1/students/me/attendance")
        finally:
            _clear()
    assert resp.status_code == 404
    db.table.return_value.select.return_value.eq.assert_called_once_with(
        "user_id", OTHER_USER_ID
    )


# ============================================================================
# REPOSITORY — context lookup flattening & persistence chains
# ============================================================================


def test_repository_flattens_section_academic_context() -> None:
    client_mock = MagicMock()
    (
        client_mock.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(
        data={
            "section_id": SECTION_A,
            "code": "AIDS-CS101-A",
            "course_offerings": {
                "course_id": "c1",
                "academic_year_id": AY_ID,
                "semester_id": SEM_ID,
                "program_id": "p1",
                "courses": {
                    "department_id": "d1",
                    "departments": {"institution_id": TENANT_A},
                },
            },
        }
    )
    result = attendance_repo.get_section_academic_context(client_mock, SECTION_A)
    assert result["institution_id"] == TENANT_A
    assert result["academic_year_id"] == AY_ID
    assert result["semester_id"] == SEM_ID
    assert result["program_id"] == "p1"
    assert result["section_code"] == "AIDS-CS101-A"


def test_repository_section_context_none_when_missing() -> None:
    client_mock = MagicMock()
    (
        client_mock.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=None)
    assert attendance_repo.get_section_academic_context(client_mock, SECTION_A) is None


def test_repository_insert_attendance_returns_first_row() -> None:
    client_mock = MagicMock()
    row = _attendance_row()
    (client_mock.table.return_value.insert.return_value.execute).return_value = MagicMock(data=[row])
    result = attendance_repo.insert_attendance(client_mock, row)
    assert result == row
    client_mock.table.assert_called_once_with("student_attendance")


def test_repository_update_attendance_row_filters_by_id() -> None:
    client_mock = MagicMock()
    updated = _attendance_row(status="late")
    (
        client_mock.table.return_value.update.return_value.eq.return_value.execute
    ).return_value = MagicMock(data=[updated])
    result = attendance_repo.update_attendance_row(client_mock, ATTENDANCE_ID, {"status": "late"})
    assert result["status"] == "late"
    client_mock.table.return_value.update.return_value.eq.assert_called_once_with(
        "student_attendance_id", str(ATTENDANCE_ID)
    )


def test_repository_delete_attendance_row_hard_deletes() -> None:
    client_mock = MagicMock()
    attendance_repo.delete_attendance_row(client_mock, ATTENDANCE_ID)
    client_mock.table.return_value.delete.return_value.eq.assert_called_once_with(
        "student_attendance_id", str(ATTENDANCE_ID)
    )


def test_repository_get_student_context_projection() -> None:
    client_mock = MagicMock()
    row = {"student_id": STUDENT_A, "institution_id": TENANT_A, "program_id": None}
    (
        client_mock.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute
    ).return_value = MagicMock(data=row)
    result = attendance_repo.get_student_context(client_mock, STUDENT_A)
    assert result == row
    client_mock.table.assert_called_once_with("students")
    client_mock.table.return_value.select.assert_called_once_with(
        "student_id, institution_id, program_id"
    )


# ============================================================================
# PHYSICAL (LIVE DATABASE) VALIDATION — opt-in, mirrors project convention
# ============================================================================
# These tests verify the Phase 6.7 migration against the real remote schema:
# backfill, tenant derivation, the guard trigger, and the unique constraint.
# They are skipped in the default suite and run only when a reviewer opts in,
# matching the existing ``test_physical_validation_phase_4_4.py`` pattern. No
# credentials are hardcoded — the app's ``.env`` service-role config is reused.


@pytest.mark.skip(reason="Live-database validation requires explicit manual opt-in")
class TestAttendancePhysicalValidationPhase67:
    """Live-database verification for Phase 6.7 constraints and triggers."""

    def test_live_schema_and_backfill(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        rows = db.table("student_attendance").select("*").limit(5).execute().data
        assert rows, "student_attendance must have seeded rows"
        assert "institution_id" in rows[0]
        assert "updated_at" in rows[0]
        for row in rows:
            student = (
                db.table("students")
                .select("institution_id")
                .eq("student_id", row["student_id"])
                .maybe_single()
                .execute()
                .data
            )
            assert row["institution_id"] == student["institution_id"]

    def test_live_guard_trigger_derives_tenant_and_rejects_violations(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        seed = db.table("student_attendance").select("*").limit(1).execute().data[0]
        offering = (
            db.table("sections")
            .select("course_offerings(semester_id, academic_year_id)")
            .eq("section_id", seed["section_id"])
            .maybe_single()
            .execute()
            .data["course_offerings"]
        )
        # institution_id is intentionally WRONG below — the trigger must derive
        # the tenant from the student record instead of trusting the input.
        payload = {
            "student_id": seed["student_id"],
            "section_id": seed["section_id"],
            "academic_year_id": offering["academic_year_id"],
            "semester_id": offering["semester_id"],
            "date": "2030-02-01",
            "status": "present",
            "institution_id": "00000000-0000-0000-0000-000000000000",
        }
        row = db.table("student_attendance").insert(payload).execute().data[0]
        try:
            assert row["institution_id"] == seed["institution_id"]
            assert row["updated_at"] is not None

            # Academic-context violation (wrong semester for the section's
            # offering) must be rejected at the database layer.
            other_sem = (
                db.table("semesters")
                .select("semester_id")
                .neq("semester_id", offering["semester_id"])
                .limit(1)
                .execute()
                .data
            )
            if other_sem:
                bad_context = dict(
                    payload,
                    date="2030-02-02",
                    semester_id=other_sem[0]["semester_id"],
                )
                with pytest.raises(Exception) as exc:
                    db.table("student_attendance").insert(bad_context).execute()
                assert "academic context" in str(exc.value)

            # Ownership reassignment must be rejected at the database layer.
            other_section = (
                db.table("sections")
                .select("section_id")
                .neq("section_id", seed["section_id"])
                .limit(1)
                .execute()
                .data
            )
            if other_section:
                with pytest.raises(Exception) as exc2:
                    db.table("student_attendance").update(
                        {"section_id": other_section[0]["section_id"]}
                    ).eq("student_attendance_id", row["student_attendance_id"]).execute()
                assert "ownership fields cannot be changed" in str(exc2.value)
        finally:
            db.table("student_attendance").delete().eq(
                "student_attendance_id", row["student_attendance_id"]
            ).execute()

    def test_live_duplicate_insert_rejected(self):
        from app.db.supabase import get_admin_client

        db = get_admin_client()
        row = db.table("student_attendance").select("*").limit(1).execute().data[0]
        dup = {
            "student_id": row["student_id"],
            "section_id": row["section_id"],
            "academic_year_id": row["academic_year_id"],
            "semester_id": row["semester_id"],
            "date": "2030-03-01",
            "status": "present",
        }
        inserted = db.table("student_attendance").insert(dup).execute().data[0]
        try:
            with pytest.raises(Exception) as exc:
                db.table("student_attendance").insert(dup).execute()
            assert "23505" in str(exc.value)
        finally:
            db.table("student_attendance").delete().eq(
                "student_attendance_id", inserted["student_attendance_id"]
            ).execute()