"""Test management."""

from __future__ import annotations

from app.core.errors import AppError

from app.repositories.platform import tenancy as tenancy_repo

from app.services.auth import authorization as authz

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import pytest

from .fixtures import (
    _active_institution_authorization,
)

from .support import (
    INST_A,
    INST_B,
    ORG_A,
    ORG_B,
    _inst_ctx,
    _org_ctx,
    _user,
)


def test_01_organization_scoped_admin_access():
    """Org-scoped admin of Org A manages Org A and its institutions."""
    ctx = _org_ctx()
    assert ctx["scope_type"] == authz.ORGANIZATION
    assert ctx["organization_id"] == ORG_A
    assert ctx["roles"] == ["admin"]
    # Institution A belongs to Org A -> manageable (the institution's
    # organization is resolved server-side).
    with patch.object(
        tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
    ):
        authz.assert_can_manage_institution(_user(), ctx, INST_A)
    authz.assert_can_manage_organization(_user(), ctx, ORG_A)


def test_02_organization_admin_cannot_access_another_organization():
    """Org A admin can never reach Org B (scope is server-side)."""
    ctx = _org_ctx()
    with pytest.raises(AppError) as org_err:
        authz.assert_can_manage_organization(_user(), ctx, ORG_B)
    assert org_err.value.status_code == 403
    assert org_err.value.code == "ORGANIZATION_MISMATCH"
    with pytest.raises(AppError) as jr_err:
        authz.assert_can_decide_join_request(ctx, {"organization_id": ORG_B})
    assert jr_err.value.code == "ORGANIZATION_MISMATCH"


def test_03_institution_scoped_admin_access():
    """Institution-scoped admin manages THEIR institution only."""
    ctx = _inst_ctx()
    assert ctx["scope_type"] == authz.INSTITUTION
    assert ctx["scope_id"] == INST_A
    assert ctx["institution_id"] == INST_A
    assert ctx["organization_id"] == ORG_A
    authz.assert_can_manage_institution(_user(), ctx, INST_A)
    # Never organization-wide authority.
    with pytest.raises(AppError) as org_err:
        authz.assert_can_manage_organization(_user(), ctx, ORG_A)
    assert org_err.value.code == "FORBIDDEN"


def test_04_institution_admin_cannot_access_another_institution():
    """Institution A admin cannot touch Institution B (TENANT_MISMATCH)."""
    ctx = _inst_ctx()
    with pytest.raises(AppError) as excinfo:
        authz.assert_can_manage_institution(_user(), ctx, INST_B)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_MISMATCH"


@pytest.mark.parametrize("scope", [None, "", "galaxy"])
@pytest.mark.parametrize("resource", ["institution", "organization"])
def test_management_guards_reject_unknown_scope(scope, resource):
    ctx = {"roles": ["admin"], "scope_type": scope}
    guard = (
        authz.assert_can_manage_institution
        if resource == "institution"
        else authz.assert_can_manage_organization
    )
    with pytest.raises(AppError) as error:
        guard(_user(), ctx, INST_A if resource == "institution" else ORG_A)
    assert error.value.code == "FORBIDDEN"


def test_management_guards_preserve_explicit_platform_authority():
    ctx = {"roles": ["admin"], "scope_type": "platform"}
    authz.assert_can_manage_institution(_user(), ctx, INST_A)
    authz.assert_can_manage_organization(_user(), ctx, ORG_A)
