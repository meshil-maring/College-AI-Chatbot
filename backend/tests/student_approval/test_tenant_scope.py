"""Test tenant scope."""

from __future__ import annotations

from app.core.errors import AppError

from app.repositories.admin import admin_academics as repo

from app.services.admin import admin_academics as svc

from unittest.mock import MagicMock, patch

from .support import (
    STUDENT_A,
    STUDENT_B,
    TENANT_A,
    TENANT_B,
    _active_institution_authorization,
    _as,
    _clear,
    _pending_row,
    _user,
    client,
)


def test_admin_lists_only_own_pending():
    _as(_user(TENANT_A, roles=("admin",)))
    rows_a = [_pending_row(STUDENT_A, TENANT_A)]
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals",
            return_value=rows_a,
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
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as m:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_B}"
            )
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
    m.assert_not_called()


def test_client_own_institution_query_is_accepted():
    _as(_user(TENANT_A, roles=("admin",)))
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as m:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_A}"
            )
    finally:
        _clear()
    assert resp.status_code == 200
    assert str(m.call_args.args[0]) == TENANT_A


def test_admin_cannot_approve_other_tenant_student():
    _as(_user(TENANT_A, roles=("admin",)))

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


def test_admin_cannot_reject_other_tenant_student():
    _as(_user(TENANT_A, roles=("admin",)))

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


def test_service_enforces_tenant_before_state():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(
            repo,
            "get_student_for_approval",
            return_value=_pending_row(STUDENT_B, TENANT_B, approval_status="approved"),
        ),
    ):
        for fn in (svc.approve_student, svc.reject_student):
            try:
                fn(
                    STUDENT_B,
                    TENANT_A,
                    **({"actor": _user(TENANT_A)} if fn is svc.approve_student else {}),
                )
                raise AssertionError("expected TENANT_MISMATCH")
            except AppError as exc:
                assert exc.status_code == 403
                assert exc.code == "TENANT_MISMATCH"


def test_service_cross_tenant_pending_rejected():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(
            repo,
            "get_student_for_approval",
            return_value=_pending_row(STUDENT_B, TENANT_B),
        ),
    ):
        try:
            svc.approve_student(STUDENT_B, TENANT_A, actor=_user(TENANT_A))
            raise AssertionError("expected TENANT_MISMATCH")
        except AppError as exc:
            assert exc.code == "TENANT_MISMATCH"
