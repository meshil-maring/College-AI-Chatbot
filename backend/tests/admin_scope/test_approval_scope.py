"""Test approval scope."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

from .support import (
    ADMIN_A_USER,
    INST_A,
    INST_B,
    _authenticated,
    _clean_dependencies,
    _principal,
    client,
    conflicting_admin,
)


def test_staff_keeps_only_the_institution_scoped_approval_exception() -> None:
    staff = _principal("72000000-0000-0000-0000-0000000000aa", "staff", INST_A)
    with (
        _authenticated(staff),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as pending,
    ):
        allowed = client.get("/api/v1/admin/students/pending")
        denied = client.get("/api/v1/admin/me")
    assert allowed.status_code == 200
    assert pending.call_args.args[0] == UUID(INST_A)
    assert denied.status_code == 403


def test_forged_institution_query_and_code_cannot_change_scope() -> None:
    with (
        _authenticated(ADMIN_A_USER),
        patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as list_students,
    ):
        foreign = client.get(f"/api/v1/admin/students/pending?institution_id={INST_B}")
        own = client.get(
            f"/api/v1/admin/students/pending?institution_id={INST_A}&institution_code=FORGED"
        )
    assert foreign.status_code == 403
    assert foreign.json()["error"]["code"] == "TENANT_MISMATCH"
    assert own.status_code == 200
    assert list_students.call_args.args[0] == UUID(INST_A)
