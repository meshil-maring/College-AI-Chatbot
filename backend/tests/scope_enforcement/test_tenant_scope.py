"""Test tenant scope."""

from __future__ import annotations

from app.core.errors import AppError

from app.core.security import (
    assert_tenant_object,
    get_current_user,
    require_roles,
    scope_tenant,
)

from app.repositories.platform import tenancy as tenancy_repo

from app.services.auth import authorization as authz

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import pytest

from .fixtures import (
    _active_institution_authorization,
)

from .support import (
    INST_B,
    ORG_B,
    TENANT_A,
    TENANT_B,
    _as,
    _clear,
    _org_ctx,
    _user,
    client,
)


def test_07_staff_isolation_on_approval_queue():
    """A staff of Institution A is scoped to A and denied B."""
    staff = _user(TENANT_A, roles=("staff",))
    _as(staff)
    try:
        with patch("app.services.admin.admin_academics.list_pending_approvals") as svc:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_B}"
            )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TENANT_MISMATCH"
        svc.assert_not_called()

        # Own tenant: forced to A even when A is requested.
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as svc:
            resp = client.get(
                f"/api/v1/admin/students/pending?institution_id={TENANT_A}"
            )
        assert resp.status_code == 200
        assert str(svc.call_args.args[0]) == TENANT_A
    finally:
        _clear()


def test_07b_staff_cannot_access_admin_only_operations():
    """Staff is denied the admin-only boundary (no escalation)."""
    staff = _user(TENANT_A, roles=("staff",))
    _as(staff)
    try:
        r1 = client.get("/api/v1/admin/me")
        r2 = client.get("/api/v1/admin/audit-logs")
    finally:
        _clear()
    assert r1.status_code == 403
    assert r2.status_code == 403


def test_12_client_institution_id_substitution_denied():
    """A tenant-bound admin cannot substitute another institution id."""
    admin = _user(TENANT_A, roles=("admin",))
    _as(admin)
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


def test_13_client_organization_id_substitution_denied():
    """Org A admin cannot manage an institution belonging to Org B.

    The institution's organization is resolved SERVER-SIDE (the client can
    never substitute it) — even against a foreign institution id, the guard
    compares the resolved organization with the caller's scope.
    """
    ctx = _org_ctx()
    with patch.object(
        tenancy_repo, "get_institution_organization", return_value=UUID(ORG_B)
    ):
        with pytest.raises(AppError) as excinfo:
            authz.assert_can_manage_institution(_user(), ctx, INST_B)
    assert excinfo.value.code == "ORGANIZATION_MISMATCH"


def test_22_valid_same_tenant_resource_access_allowed():
    """Same-tenant reads succeed and are forced to the caller's institution."""
    admin = _user(TENANT_A, roles=("admin",))
    _as(admin)
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


def test_22b_platform_account_behavior_preserved():
    """Platform-level accounts keep the previous passthrough behaviour."""
    assert scope_tenant(_user(None), TENANT_B) == UUID(TENANT_B)
    assert_tenant_object(_user(None), TENANT_B)  # no-op
