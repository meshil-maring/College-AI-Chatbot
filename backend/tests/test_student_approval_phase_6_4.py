"""Phase 6.4 — Admin/staff student approval tests (hermetic, mocked Supabase).

Covers: authorization (unauthenticated / student / unauthorized / admin /
staff), tenant isolation (A cannot see or mutate B), pending-list filtering,
approve (pending->approved), reject (pending->rejected), invalid transitions,
client tampering (institution_id / role / approval_status ignored), stale /
concurrency races, audit logging, and data-protection (no secrets leaked).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.admin import _APPROVAL
from app.core.security import get_current_user
from app.core.errors import AppError
from app.main import app
from app.repositories import admin_academics as repo
from app.services import admin_academics as svc

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "a1111111-0000-0000-0000-000000000001"
TENANT_B = "b2222222-0000-0000-0000-000000000002"
STUDENT_A = "30000000-0000-0000-0000-000000000151"
STUDENT_B = "30000000-0000-0000-0000-000000000152"


def _user(tenant=None, roles=("admin",)):
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "approver@example.com",
        "roles": list(roles),
        "institution_id": tenant,
    }


def _pending_row(student_id=STUDENT_A, tenant=TENANT_A, **over):
    row = {
        "student_id": student_id,
        "user_id": str(uuid4()),
        "institution_id": tenant,
        "student_number": "1001",
        "email": "s@college.example.com",
        "register_number": "1001",
        "university_roll_number": "2026-1001",
        "approval_status": "pending",
        "status": "active",
        "is_active": True,
        "enrollment_date": "2026-09-12",
        "created_at": "2026-09-12T00:00:00+00:00",
        "updated_at": "2026-09-12T00:00:00+00:00",
    }
    row.update(over)
    return row


def _as(role_user):
    app.dependency_overrides[get_current_user] = lambda: role_user


def _clear():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_APPROVAL, None)


# ============================================================================
# Authorization
# ============================================================================


def test_unauthenticated_cannot_approve():
    _clear()
    resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] in ("AUTH_REQUIRED", "INVALID_SCHEME")


def test_unauthenticated_cannot_reject_or_list():
    _clear()
    assert client.post(f"/api/v1/admin/students/{STUDENT_A}/reject").status_code == 401
    assert client.get("/api/v1/admin/students/pending").status_code == 401


def test_student_cannot_approve_reject_or_list():
    _as(_user(TENANT_A, roles=("student",)))
    try:
        r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
        r3 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert r1.status_code == 403 and r1.json()["error"]["code"] == "FORBIDDEN"
    assert r2.status_code == 403 and r2.json()["error"]["code"] == "FORBIDDEN"
    assert r3.status_code == 403 and r3.json()["error"]["code"] == "FORBIDDEN"


def test_unauthorized_role_cannot_approve():
    _as(_user(TENANT_A, roles=("faculty",)))
    try:
        resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_approve():
    _as(_user(TENANT_A, roles=("admin",)))
    row = _pending_row(approval_status="approved")
    try:
        with (
            patch("app.api.admin.admin_academics.approve_student", return_value=row) as m,
            patch("app.api.admin._record_audit") as audit,
        ):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 200, resp.text
    assert resp.json()["approval_status"] == "approved"
    assert str(m.call_args.args[0]) == STUDENT_A
    assert str(m.call_args.args[1]) == TENANT_A
    assert audit.call_count == 1
    assert audit.call_args.args[1] == "student.approve"


def test_staff_can_approve_and_reject():
    _as(_user(TENANT_A, roles=("staff",)))
    try:
        with (
            patch(
                "app.api.admin.admin_academics.approve_student",
                return_value=_pending_row(approval_status="approved"),
            ),
            patch("app.api.admin._record_audit"),
        ):
            r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        with (
            patch(
                "app.api.admin.admin_academics.reject_student",
                return_value=_pending_row(approval_status="rejected"),
            ),
            patch("app.api.admin._record_audit"),
        ):
            r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
    finally:
        _clear()
    assert r1.status_code == 200
    assert r2.status_code == 200


# Tenant isolation

def test_admin_lists_only_own_pending():
    _as(_user(TENANT_A, roles=("admin",)))
    rows_a = [_pending_row(STUDENT_A, TENANT_A)]
    try:
        with patch(
            "app.api.admin.admin_academics.list_pending_approvals", return_value=rows_a
        ) as m:
            resp = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert resp.status_code == 200, resp.text
    assert resp.json() == rows_a
    assert str(m.call_args.args[0]) == TENANT_A


def test_client_institution_query_cannot_override_scope():
    """A foreign ?institution_id is rejected — never silently rewritten."""
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as m:
            resp = client.get(f"/api/v1/admin/students/pending?institution_id={TENANT_B}")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    m.assert_not_called()


def test_client_own_institution_query_is_accepted():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as m:
            resp = client.get(f"/api/v1/admin/students/pending?institution_id={TENANT_A}")
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(m.call_args.args[0]) == TENANT_A


def test_admin_cannot_approve_other_tenant_student():
    _as(_user(TENANT_A, roles=("admin",)))

    def _deny(student_id, tenant):
        raise AppError(
            "This resource belongs to a different institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    try:
        with patch("app.api.admin.admin_academics.approve_student", side_effect=_deny):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/approve")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_admin_cannot_reject_other_tenant_student():
    _as(_user(TENANT_A, roles=("admin",)))

    def _deny(student_id, tenant):
        raise AppError(
            "This resource belongs to a different institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    try:
        with patch("app.api.admin.admin_academics.reject_student", side_effect=_deny):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/reject")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_service_enforces_tenant_before_state():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(
            repo, "get_student_for_approval",
            return_value=_pending_row(STUDENT_B, TENANT_B, approval_status="approved"),
        ),
    ):
        for fn in (svc.approve_student, svc.reject_student):
            try:
                fn(STUDENT_B, TENANT_A)
                raise AssertionError("expected TENANT_MISMATCH")
            except AppError as exc:
                assert exc.status_code == 403
                assert exc.code == "TENANT_MISMATCH"


def test_service_cross_tenant_pending_rejected():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(
            repo, "get_student_for_approval",
            return_value=_pending_row(STUDENT_B, TENANT_B),
        ),
    ):
        try:
            svc.approve_student(STUDENT_B, TENANT_A)
            raise AssertionError("expected TENANT_MISMATCH")
        except AppError as exc:
            assert exc.code == "TENANT_MISMATCH"


def test_pending_list_queries_pending_only_in_tenant():
    db = MagicMock()
    expected = _pending_row()
    chain = db.table.return_value.select.return_value
    chain.eq.return_value.eq.return_value.order.return_value.limit.return_value.range.return_value.execute.return_value = MagicMock(
        data=[expected]
    )
    rows = repo.list_pending_students(db, TENANT_A)
    assert rows == [expected]
    db.table.assert_called_once_with("students")
    chain.eq.assert_called_once_with("institution_id", TENANT_A)
    chain.eq.return_value.eq.assert_called_once_with("approval_status", "pending")


def test_approve_pending_to_approved_db_state():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        patch.object(
            repo, "set_student_approval_status",
            return_value=_pending_row(approval_status="approved"),
        ) as m,
    ):
        out = svc.approve_student(STUDENT_A, TENANT_A)
    assert out["approval_status"] == "approved"
    assert m.call_args.args[1:] == (STUDENT_A, TENANT_A, "approved")


def test_reject_pending_to_rejected_preserved():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        patch.object(
            repo, "set_student_approval_status",
            return_value=_pending_row(approval_status="rejected"),
        ) as m,
    ):
        out = svc.reject_student(STUDENT_A, TENANT_A)
    assert out["approval_status"] == "rejected"
    assert m.call_args.args[1:] == (STUDENT_A, TENANT_A, "rejected")


def test_approve_unknown_student_404():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval", return_value=None),
    ):
        try:
            svc.approve_student(STUDENT_A, TENANT_A)
            raise AssertionError("expected 404")
        except AppError as exc:
            assert exc.status_code == 404
            assert exc.code == "STUDENT_NOT_FOUND"


def test_conditional_write_targets_pending_only():
    db = MagicMock()
    repo.set_student_approval_status(db, STUDENT_A, TENANT_A, "approved")
    upd = db.table.return_value.update
    upd.assert_called_once_with({"approval_status": "approved"})
    upd.return_value.eq.assert_called_once_with("student_id", STUDENT_A)
    upd.return_value.eq.return_value.eq.assert_called_once_with("institution_id", TENANT_A)
    upd.return_value.eq.return_value.eq.return_value.eq.assert_called_once_with(
        "approval_status", "pending"
    )


def test_invalid_transitions_rejected():
    cases = [
        ("approved", "approve"),
        ("approved", "reject"),
        ("rejected", "approve"),
        ("rejected", "reject"),
    ]
    for current, op in cases:
        db = MagicMock()
        fn = svc.approve_student if op == "approve" else svc.reject_student
        with (
            patch.object(svc, "get_admin_client", return_value=db),
            patch.object(
                repo, "get_student_for_approval",
                return_value=_pending_row(approval_status=current),
            ),
        ):
            try:
                fn(STUDENT_A, TENANT_A)
                raise AssertionError(f"expected 409 for {current}->{op}")
            except AppError as exc:
                assert exc.status_code == 409, (current, op)
                assert exc.code == "STUDENT_NOT_PENDING"


def test_api_surfaces_not_pending_as_409():
    _as(_user(TENANT_A, roles=("admin",)))

    def _stale(student_id, tenant):
        raise AppError(
            "Student is not pending approval (current: approved)",
            status_code=409,
            code="STUDENT_NOT_PENDING",
        )

    try:
        with patch("app.api.admin.admin_academics.approve_student", side_effect=_stale):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "STUDENT_NOT_PENDING"


def test_client_body_cannot_bypass_authorization():
    _as(_user(TENANT_A, roles=("admin",)))
    row = _pending_row(approval_status="approved")
    try:
        with (
            patch("app.api.admin.admin_academics.approve_student", return_value=row) as m,
            patch("app.api.admin._record_audit"),
        ):
            resp = client.post(
                f"/api/v1/admin/students/{STUDENT_A}/approve",
                json={
                    "institution_id": TENANT_B,
                    "role": "admin",
                    "roles": ["admin"],
                    "approval_status": "approved",
                },
            )
    finally:
        _clear()
    assert resp.status_code == 200, resp.text
    assert str(m.call_args.args[1]) == TENANT_A


def test_reject_body_tampering_inert():
    _as(_user(TENANT_A, roles=("staff",)))
    row = _pending_row(approval_status="rejected")
    try:
        with (
            patch("app.api.admin.admin_academics.reject_student", return_value=row) as m,
            patch("app.api.admin._record_audit"),
        ):
            resp = client.post(
                f"/api/v1/admin/students/{STUDENT_A}/reject",
                json={"institution_id": TENANT_B, "approval_status": "approved"},
            )
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(m.call_args.args[1]) == TENANT_A


def test_stale_approve_after_reject_maps_to_409():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval",
                     side_effect=[_pending_row(), _pending_row(approval_status="rejected")]),
        patch.object(repo, "set_student_approval_status", return_value=None),
    ):
        try:
            svc.approve_student(STUDENT_A, TENANT_A)
            raise AssertionError("expected 409 stale")
        except AppError as exc:
            assert exc.status_code == 409
            assert exc.code == "STUDENT_NOT_PENDING"


def test_double_approve_second_rejected_as_not_pending():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval",
                     return_value=_pending_row(approval_status="approved")),
    ):
        try:
            svc.approve_student(STUDENT_A, TENANT_A)
            raise AssertionError("expected 409")
        except AppError as exc:
            assert exc.code == "STUDENT_NOT_PENDING"


def test_approve_and_reject_write_audit_log():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with (
            patch("app.api.admin.admin_academics.approve_student",
                  return_value=_pending_row(approval_status="approved")),
            patch("app.api.admin._record_audit") as audit,
        ):
            client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
            assert audit.call_args.args[1] == "student.approve"
            assert audit.call_args.args[2] == "students"
        with (
            patch("app.api.admin.admin_academics.reject_student",
                  return_value=_pending_row(approval_status="rejected")),
            patch("app.api.admin._record_audit") as audit2,
        ):
            client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
            assert audit2.call_args.args[1] == "student.reject"
    finally:
        _clear()


def test_approval_response_leaks_no_secrets():
    _as(_user(TENANT_A, roles=("admin",)))
    row = _pending_row(approval_status="approved")
    try:
        with (
            patch("app.api.admin.admin_academics.approve_student", return_value=row),
            patch("app.api.admin._record_audit"),
        ):
            body = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve").json()
    finally:
        _clear()
    blob = str(body).lower()
    for secret in ("password", "access_token", "refresh_token", "secret"):
        assert secret not in blob
    assert set(body) <= set(row)


# ============================================================================
# Platform-level policy (review decision — OPTION A)
# ============================================================================
# Institution-bound admin/staff: strictly own tenant. Platform-level ADMIN:
# global approval authority (Phase 6.1 convention). Platform-level STAFF (or
# any other tenant-less role): 403 — no silent escalation.


def test_institution_staff_cannot_approve_other_tenant_student():
    _as(_user(TENANT_A, roles=("staff",)))

    def _deny(student_id, tenant):
        raise AppError(
            "This resource belongs to a different institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    try:
        with patch("app.api.admin.admin_academics.approve_student", side_effect=_deny):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/approve")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_institution_staff_cannot_reject_other_tenant_student():
    _as(_user(TENANT_A, roles=("staff",)))

    def _deny(student_id, tenant):
        raise AppError(
            "This resource belongs to a different institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    try:
        with patch("app.api.admin.admin_academics.reject_student", side_effect=_deny):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/reject")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_platform_admin_can_approve_college_a_student():
    """Platform admin (tenant None) approves via the target's institution."""
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval",
                     return_value=_pending_row(STUDENT_A, TENANT_A)),
        patch.object(repo, "set_student_approval_status",
                     return_value=_pending_row(STUDENT_A, TENANT_A, approval_status="approved")) as m,
    ):
        out = svc.approve_student(STUDENT_A, None)
    assert out["approval_status"] == "approved"
    assert m.call_args.args[1:] == (STUDENT_A, TENANT_A, "approved")


def test_platform_admin_can_reject_college_b_student():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval",
                     return_value=_pending_row(STUDENT_B, TENANT_B)),
        patch.object(repo, "set_student_approval_status",
                     return_value=_pending_row(STUDENT_B, TENANT_B, approval_status="rejected")) as m,
    ):
        out = svc.reject_student(STUDENT_B, None)
    assert out["approval_status"] == "rejected"
    assert m.call_args.args[1:] == (STUDENT_B, TENANT_B, "rejected")


def test_platform_admin_endpoint_approves_any_tenant():
    _as(_user(None, roles=("admin",)))
    row = _pending_row(STUDENT_B, TENANT_B, approval_status="approved")
    try:
        with (
            patch("app.api.admin.admin_academics.approve_student", return_value=row) as m,
            patch("app.api.admin._record_audit"),
        ):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/approve")
    finally:
        _clear()
    assert resp.status_code == 200, resp.text
    assert m.call_args.args[1] is None  # global authority, server-resolved


def test_platform_admin_lists_pending_globally():
    _as(_user(None, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as m:
            resp = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert resp.status_code == 200
    assert m.call_args.args[0] is None  # unfiltered global queue


def test_platform_admin_list_can_filter_by_explicit_institution():
    _as(_user(None, roles=("admin",)))
    try:
        with patch(
            "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as m:
            resp = client.get(f"/api/v1/admin/students/pending?institution_id={TENANT_B}")
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(m.call_args.args[0]) == TENANT_B


def test_platform_staff_cannot_approve():
    _as(_user(None, roles=("staff",)))
    try:
        with patch("app.api.admin.admin_academics.approve_student") as m:
            resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    m.assert_not_called()


def test_platform_staff_cannot_reject_or_list():
    _as(_user(None, roles=("staff",)))
    try:
        r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
        r2 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert r1.status_code == 403 and r1.json()["error"]["code"] == "FORBIDDEN"
    assert r2.status_code == 403 and r2.json()["error"]["code"] == "FORBIDDEN"


def test_platform_student_role_still_forbidden():
    _as(_user(None, roles=("student",)))
    try:
        resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


