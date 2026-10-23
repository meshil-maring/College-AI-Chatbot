"""Test provisioning."""

from __future__ import annotations

from app.core.errors import AppError

from app.repositories.admin import admin_academics as repo

from app.services.admin import admin_academics as svc

from postgrest.exceptions import APIError

from unittest.mock import MagicMock, patch

import pytest

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


def test_student_approval_requires_institution_scope_even_for_platform_admin():
    with pytest.raises(AppError) as caught:
        svc.approve_student(STUDENT_A, None, actor=_user(None))
    assert caught.value.code == "FORBIDDEN"


@pytest.mark.parametrize(
    "actor",
    [
        None,
        {},
        {"user_id": "actor"},
        {"user_id": "actor", "auth_user_id": "auth", "roles": ["faculty"]},
        {"user_id": "actor", "auth_user_id": "auth", "roles": ["student"]},
    ],
)
def test_student_provisioning_requires_verified_supported_actor(actor):
    with patch.object(repo, "approve_student_and_provision") as provision:
        with pytest.raises(AppError) as caught:
            svc.approve_student(STUDENT_A, TENANT_A, actor=actor)
    assert caught.value.code == "FORBIDDEN"
    provision.assert_not_called()


@pytest.mark.parametrize(
    "result",
    [
        {"role_granted": False, "audit_persisted": True},
        {"role_granted": True, "audit_persisted": False},
        {"role_granted": True, "audit_persisted": True},
        {
            "student": {"approval_status": "pending"},
            "role_granted": True,
            "audit_persisted": True,
        },
    ],
)
def test_student_approval_never_reports_success_on_incomplete_provisioning(result):
    with (
        patch.object(svc, "get_admin_client", return_value=MagicMock()),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        patch.object(
            repo, "approve_student_and_provision", return_value=result
        ) as provision,
    ):
        with pytest.raises(AppError) as caught:
            svc.approve_student(STUDENT_A, TENANT_A, actor=_user(TENANT_A))
    assert caught.value.code == "STUDENT_PROVISIONING_UNCERTAIN"
    provision.assert_called_once()


@pytest.mark.parametrize("boundary", ["grant", "audit", "lost_commit_response"])
def test_student_transaction_failure_is_recoverable_by_same_command(boundary):
    row = _pending_row(approval_status="approved")
    with (
        patch.object(svc, "get_admin_client", return_value=MagicMock()),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        patch.object(
            repo,
            "approve_student_and_provision",
            side_effect=[
                RuntimeError(boundary),
                {"student": row, "role_granted": True, "audit_persisted": True},
            ],
        ) as provision,
    ):
        actor = _user(TENANT_A)
        with pytest.raises(AppError) as caught:
            svc.approve_student(STUDENT_A, TENANT_A, actor=actor)
        assert caught.value.code == "STUDENT_PROVISIONING_UNCERTAIN"
        assert svc.approve_student(STUDENT_A, TENANT_A, actor=actor) == row
    assert provision.call_count == 2
    assert provision.call_args_list[0] == provision.call_args_list[1]


def test_student_http_flow_delegates_approval_grant_and_audit_to_one_rpc():
    actor = _user(TENANT_A)
    db = MagicMock()
    row = _pending_row(approval_status="approved")
    db.rpc.return_value.execute.return_value.data = {
        "student": row,
        "role_granted": True,
        "audit_persisted": True,
    }
    _as(actor)
    try:
        with (
            patch.object(svc, "get_admin_client", return_value=db),
            patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        ):
            response = client.post(f"/api/v1/admin/students/{STUDENT_A}/approve")
    finally:
        _clear()
    assert response.status_code == 200
    db.rpc.assert_called_once_with(
        "b05_approve_student",
        {
            "p_student_id": STUDENT_A,
            "p_institution_id": TENANT_A,
            "p_actor_user_id": actor["user_id"],
            "p_actor_auth_user_id": actor["auth_user_id"],
        },
    )
    assert response.json()["approval_status"] == "approved"


def test_tenantless_admin_cannot_approve_any_tenant():
    """Phase 7.20: a tenant-less ordinary admin has no institution authority."""
    _as(_user(None, roles=("admin",)))
    try:
        with patch("app.services.admin.admin_academics.approve_student") as m:
            resp = client.post(f"/api/v1/admin/students/{STUDENT_B}/approve")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    m.assert_not_called()


def test_tenantless_admin_cannot_list_pending_globally():
    _as(_user(None, roles=("admin",)))
    try:
        with patch("app.services.admin.admin_academics.list_pending_approvals") as m:
            resp = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    m.assert_not_called()


def test_tenantless_admin_cannot_filter_by_institution():
    _as(_user(None, roles=("admin",)))
    try:
        with patch("app.services.admin.admin_academics.list_pending_approvals") as m:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_B}"
            )
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    m.assert_not_called()


def test_platform_staff_cannot_approve():
    _as(_user(None, roles=("staff",)))
    try:
        with patch("app.services.admin.admin_academics.approve_student") as m:
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


@pytest.mark.parametrize("code", ["PGRST202", "42883", "42703"])
def test_missing_approval_schema_is_unavailable_instead_of_a_decision_conflict(code):
    with (
        patch.object(svc, "get_admin_client", return_value=MagicMock()),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        patch.object(
            repo,
            "approve_student_and_provision",
            side_effect=APIError(
                {
                    "code": code,
                    "message": "internal database function or column details",
                    "details": None,
                    "hint": None,
                }
            ),
        ),
    ):
        with pytest.raises(AppError) as caught:
            svc.approve_student(STUDENT_A, TENANT_A, actor=_user(TENANT_A))
    assert caught.value.status_code == 503
    assert caught.value.code == "STUDENT_APPROVAL_UNAVAILABLE"
    assert "internal database" not in caught.value.message
