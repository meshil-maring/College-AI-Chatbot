"""Test consistency."""

from __future__ import annotations

from app.core.errors import AppError

from app.services.auth import authorization as authz

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .fixtures import (
    _active_institution_authorization,
)

from .support import (
    INST_A,
    INST_ADMIN,
    INST_B,
    ORG_A,
    ORG_B,
    _as,
    _clear,
    _resolve,
    _role_row,
    _user,
    client,
)


def test_14_missing_role_and_scope_denied():
    """A user with no active role rows and no tenant has no scope at all."""
    ctx = _resolve([])
    assert ctx["roles"] == []
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "SCOPE_MISSING"


def test_15_missing_role_denied_on_protected_endpoint():
    """No role -> 403 FORBIDDEN on the admin boundary."""
    _as(_user(roles=()))
    try:
        with patch("app.services.admin.admin_dashboard.get_dashboard_summary") as svc:
            resp = client.get("/api/v1/admin/dashboard")
    finally:
        _clear()
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    svc.assert_not_called()


def test_16_invalid_scope_denied():
    """Unknown scope_type values fail closed (SCOPE_INCONSISTENT)."""
    ctx = _resolve([_role_row("galaxy", INST_A, ORG_A)])
    assert ctx["scope_type"] == "galaxy"
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16b_orphaned_organization_scope_denied():
    """An organization-scoped role row naming NO tenant is rejected."""
    ctx = _resolve([_role_row(authz.ORGANIZATION, None, None)])
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16c_orphaned_institution_scope_denied():
    """An institution-scoped role row naming NO institution is rejected."""
    ctx = _resolve([_role_row(authz.INSTITUTION, None, ORG_A)])
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(_user(), ctx)
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16d_scope_pointing_at_another_tenant_than_the_profile_denied():
    """Tenant-bound user whose scope names a DIFFERENT institution is rejected."""
    current_user = {"user_id": INST_ADMIN, "institution_id": INST_A}
    ctx = _resolve(
        [_role_row(authz.INSTITUTION, INST_B, ORG_B)], current_user=current_user
    )
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(current_user, ctx)
    assert excinfo.value.code == "SCOPE_INCONSISTENT"


def test_16e_platform_scope_on_tenant_bound_account_denied():
    """A tenant-bound account can never hold platform (unrestricted) scope."""
    ctx = {
        "user_id": INST_ADMIN,
        "roles": ["admin"],
        "scope_type": authz.PLATFORM,
        "scope_id": None,
        "organization_id": None,
        "institution_id": INST_A,
    }
    with pytest.raises(AppError) as excinfo:
        authz.assert_scope_consistency(
            {"user_id": INST_ADMIN, "institution_id": INST_A}, ctx
        )
    assert excinfo.value.code == "SCOPE_INCONSISTENT"
