"""Test approvals."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from .support import (
    STUDENT_A,
    TENANT_A,
    TENANT_B,
    _active_scope_lookup,
    _as,
    _clear,
    _user,
    client,
)


def test_institution_admin_cannot_cross_tenant_on_admin_list():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals"
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_B}"
            )
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    list_students.assert_not_called()


def test_institution_admin_forced_to_own_institution():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_A}"
            )
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(list_students.call_args.args[0]) == TENANT_A


def test_tenantless_ordinary_admin_has_no_global_authority():
    _as(_user(None, roles=("admin",)))
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as list_students:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_B}"
            )
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "SCOPE_MISSING"
    list_students.assert_not_called()


def test_staff_can_approve_own_tenant_student():
    _as(_user(TENANT_A, roles=("staff",)))
    row = {"student_id": STUDENT_A, "approval_status": "approved"}
    try:
        with (
            patch(
                "app.services.admin.admin_academics.approve_student",
                return_value=row,
            ) as approve,
            patch("app.api.admin.common.record_audit"),
        ):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert resp.status_code == 200
    approve.assert_called_once()


def test_staff_cannot_access_admin_only_operations():
    _as(_user(TENANT_A, roles=("staff",)))
    try:
        r1 = client.get("/api/v1/admin/me")
        r2 = client.get("/api/v1/admin/audit-logs")
        r3 = client.get(f"/api/v1/admin/students/{STUDENT_A}")
    finally:
        _clear()
    assert r1.status_code == 403
    assert r2.status_code == 403
    assert r3.status_code == 404


def test_platform_staff_cannot_obtain_platform_admin_authority():
    _as(_user(None, roles=("staff",)))
    try:
        with patch("app.services.admin.admin_academics.approve_student") as approve:
            r1 = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
            r2 = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert r1.status_code == 403
    assert r2.status_code == 403
    assert r1.json()["error"]["code"] == "SCOPE_MISSING"
    assert r2.json()["error"]["code"] == "SCOPE_MISSING"
    approve.assert_not_called()
