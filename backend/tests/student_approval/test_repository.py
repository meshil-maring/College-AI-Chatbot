"""Test repository."""

from __future__ import annotations

from app.core.errors import AppError

from app.repositories.admin import admin_academics as repo

from app.services.admin import admin_academics as svc

from unittest.mock import MagicMock, patch

from .support import (
    STUDENT_A,
    TENANT_A,
    _active_institution_authorization,
    _pending_row,
    _user,
)


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
    actor = _user(TENANT_A)
    row = _pending_row(approval_status="approved")
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
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
        assert svc.approve_student(STUDENT_A, TENANT_A, actor=actor) == row
    assert provision.call_args.kwargs == {
        "student_id": STUDENT_A,
        "institution_id": TENANT_A,
        "actor_user_id": actor["user_id"],
        "actor_auth_user_id": actor["auth_user_id"],
    }


def test_reject_pending_to_rejected_preserved():
    db = MagicMock()
    with (
        patch.object(svc, "get_admin_client", return_value=db),
        patch.object(repo, "get_student_for_approval", return_value=_pending_row()),
        patch.object(
            repo,
            "set_student_approval_status",
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
            svc.approve_student(STUDENT_A, TENANT_A, actor=_user(TENANT_A))
            raise AssertionError("expected 404")
        except AppError as exc:
            assert exc.status_code == 404
            assert exc.code == "STUDENT_NOT_FOUND"


def test_conditional_write_targets_pending_only():
    db = MagicMock()
    db.table.return_value.update.return_value.eq.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value.data = []
    repo.set_student_approval_status(db, STUDENT_A, TENANT_A, "approved")
    upd = db.table.return_value.update
    upd.assert_called_once_with({"approval_status": "approved"})
    upd.return_value.eq.assert_called_once_with("student_id", STUDENT_A)
    upd.return_value.eq.return_value.eq.assert_called_once_with(
        "institution_id", TENANT_A
    )
    upd.return_value.eq.return_value.eq.return_value.eq.assert_called_once_with(
        "approval_status", "pending"
    )
