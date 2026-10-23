"""Test transitions."""

from __future__ import annotations

from .support import STUDENT_B

from app.core.errors import AppError

from app.repositories.admin import admin_academics as repo

from app.services.admin import admin_academics as svc

from unittest.mock import MagicMock, patch

import pytest

from .support import (
    STUDENT_A,
    TENANT_A,
    TENANT_B,
    _active_institution_authorization,
    _as,
    _clear,
    _pending_row,
    _user,
    client,
)


def test_invalid_transitions_rejected():
    cases = [
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
                repo,
                "get_student_for_approval",
                return_value=_pending_row(approval_status=current),
            ),
        ):
            try:
                fn(
                    STUDENT_A,
                    TENANT_A,
                    **({"actor": _user(TENANT_A)} if fn is svc.approve_student else {}),
                )
                raise AssertionError(f"expected 409 for {current}->{op}")
            except AppError as exc:
                assert exc.status_code == 409, (current, op)
                assert exc.code == "STUDENT_NOT_PENDING"


def test_api_surfaces_not_pending_as_409():
    _as(_user(TENANT_A, roles=("admin",)))

    def _stale(student_id, tenant, **kwargs):
        raise AppError(
            "Student is not pending approval (current: approved)",
            status_code=409,
            code="STUDENT_NOT_PENDING",
        )

    try:
        with patch(
            "app.services.admin.admin_academics.approve_student", side_effect=_stale
        ):
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
            patch(
                "app.services.admin.admin_academics.approve_student", return_value=row
            ) as m,
            patch("app.api.admin.common.record_audit"),
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
            patch(
                "app.services.admin.admin_academics.reject_student", return_value=row
            ) as m,
            patch("app.api.admin.common.record_audit"),
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
    with (
        patch.object(svc, "get_admin_client", return_value=MagicMock()),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        patch.object(
            repo, "approve_student_and_provision", return_value={"conflict": True}
        ),
    ):
        with pytest.raises(AppError) as caught:
            svc.approve_student(STUDENT_A, TENANT_A, actor=_user(TENANT_A))
    assert caught.value.code == "STUDENT_NOT_PENDING"


def test_double_approve_recovers_provisioning_and_audit():
    row = _pending_row(approval_status="approved")
    with (
        patch.object(svc, "get_admin_client", return_value=MagicMock()),
        patch.object(repo, "get_student_for_approval", return_value=row),
        patch.object(
            repo,
            "approve_student_and_provision",
            return_value={
                "student": row,
                "role_granted": True,
                "audit_persisted": True,
            },
        ) as provision,
    ):
        actor = _user(TENANT_A)
        assert svc.approve_student(STUDENT_A, TENANT_A, actor=actor) == row
        assert svc.approve_student(STUDENT_A, TENANT_A, actor=actor) == row
    assert (
        provision.call_count == 2
    )  # Every retry reaches durable grant/audit verification.


def test_platform_admin_can_reject_college_b_student():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(
            repo,
            "get_student_for_approval",
            return_value=_pending_row(STUDENT_B, TENANT_B),
        ),
        patch.object(
            repo,
            "set_student_approval_status",
            return_value=_pending_row(STUDENT_B, TENANT_B, approval_status="rejected"),
        ) as m,
    ):
        out = svc.reject_student(STUDENT_B, None)
    assert out["approval_status"] == "rejected"
    assert m.call_args.args[1:] == (STUDENT_B, TENANT_B, "rejected")
