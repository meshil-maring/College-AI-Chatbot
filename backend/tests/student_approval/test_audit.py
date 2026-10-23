"""Test audit."""

from __future__ import annotations

from app.core.errors import AppError

from unittest.mock import MagicMock, patch

from .support import (
    STUDENT_A,
    STUDENT_B,
    TENANT_A,
    _active_institution_authorization,
    _as,
    _clear,
    _pending_row,
    _user,
    client,
)


def test_approve_and_reject_write_audit_log():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with (
            patch(
                "app.services.admin.admin_academics.approve_student",
                return_value=_pending_row(approval_status="approved"),
            ),
            patch("app.api.admin.common.record_audit") as audit,
        ):
            client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
            assert (
                not audit.mock_calls
            )  # Atomic RPC audit contract covered by service and failure tests.
        with (
            patch(
                "app.services.admin.admin_academics.reject_student",
                return_value=_pending_row(approval_status="rejected"),
            ),
            patch("app.api.admin.common.record_audit") as audit2,
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
            patch(
                "app.services.admin.admin_academics.approve_student", return_value=row
            ),
            patch("app.api.admin.common.record_audit"),
        ):
            body = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve").json()
    finally:
        _clear()
    blob = str(body).lower()
    for secret in ("password", "access_token", "refresh_token", "secret"):
        assert secret not in blob
    assert set(body) <= set(row)


def test_institution_staff_cannot_approve_other_tenant_student():
    _as(_user(TENANT_A, roles=("staff",)))

    def _deny(student_id, tenant, **kwargs):
        raise AppError(
            "This resource belongs to a different institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    try:
        with patch(
            "app.services.admin.admin_academics.approve_student", side_effect=_deny
        ):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/approve")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"


def test_institution_staff_cannot_reject_other_tenant_student():
    _as(_user(TENANT_A, roles=("staff",)))

    def _deny(student_id, tenant, **kwargs):
        raise AppError(
            "This resource belongs to a different institution",
            status_code=403,
            code="TENANT_MISMATCH",
        )

    try:
        with patch(
            "app.services.admin.admin_academics.reject_student", side_effect=_deny
        ):
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/reject")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
