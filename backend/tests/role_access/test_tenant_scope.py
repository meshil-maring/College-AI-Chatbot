"""Test tenant scope."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from .support import (
    TENANT_A,
    TENANT_B,
    _active_scope_lookup,
    _as,
    _clear,
    _user,
    client,
)


def test_foreign_institution_id_query_is_rejected_for_bound_admin():
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


def test_forbidden_never_runs_protected_operation():
    _as(_user(TENANT_A, roles=("student",)))
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals"
        ) as list_students:
            resp = client.get("/api/v1/admin/students/pending")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    list_students.assert_not_called()
