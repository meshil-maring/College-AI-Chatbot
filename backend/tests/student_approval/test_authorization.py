"""Test authorization."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from .support import (
    STUDENT_A,
    TENANT_A,
    _active_institution_authorization,
    _as,
    _clear,
    _pending_row,
    _user,
    client,
)


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
            patch(
                "app.services.admin.admin_academics.approve_student", return_value=row
            ) as m,
            patch("app.api.admin.common.record_audit") as audit,
        ):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 200, resp.text
    assert resp.json()["approval_status"] == "approved"
    assert str(m.call_args.args[0]) == STUDENT_A
    assert str(m.call_args.args[1]) == TENANT_A
    assert m.call_args.kwargs["actor"]["auth_user_id"]


def test_staff_can_approve_and_reject():
    _as(_user(TENANT_A, roles=("staff",)))
    try:
        with (
            patch(
                "app.services.admin.admin_academics.approve_student",
                return_value=_pending_row(approval_status="approved"),
            ),
            patch("app.api.admin.common.record_audit"),
        ):
            r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
        with (
            patch(
                "app.services.admin.admin_academics.reject_student",
                return_value=_pending_row(approval_status="rejected"),
            ),
            patch("app.api.admin.common.record_audit"),
        ):
            r2 = client.post(f"/api/v1/admin/students/{STUDENT_A}/reject")
    finally:
        _clear()
    assert r1.status_code == 200
    assert r2.status_code == 200
