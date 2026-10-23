"""Test compatibility."""

from __future__ import annotations

from app.core.errors import AppError

from app.core.security import (
    assert_tenant_object,
    get_current_user,
    require_roles,
    scope_tenant,
)

from app.services.auth import authorization as authz

from app.services.auth.student_auth import SafeAuthFailure

from app.services.platform import tenancy as tenancy_svc

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import asyncio

import pytest

from .fixtures import (
    _active_institution_authorization,
)

from .support import (
    INST_A,
    INST_ADMIN,
    ROLE_ID,
    TENANT_A,
    TENANT_B,
    USER_ADMIN,
    _clear,
    _resolve,
    _user,
    client,
)


def test_23_phase_6_rbac_regression():
    """Existing RBAC primitives are unchanged by Phase 6.13.7."""
    # Role-based RBAC still passes an institution-scoped admin...
    admin = {
        "user_id": INST_ADMIN,
        "auth_user_id": str(uuid4()),
        "email": "inst-admin@example.com",
        "roles": ["admin"],
        "institution_id": TENANT_A,
    }
    assert asyncio.run(require_roles("admin")(current_user=admin)) is admin
    # ...while narrowing stays with the scope layer, not require_roles().
    with pytest.raises(AppError) as excinfo:
        asyncio.run(require_roles("admin")(current_user=_user(roles=("staff",))))
    assert excinfo.value.code == "FORBIDDEN"
    # Unauthenticated requests still get 401 from get_current_user.
    _clear()
    resp = client.get("/api/v1/admin/me")
    assert resp.status_code == 401
    # Tenant primitives keep their locked semantics.
    with pytest.raises(AppError) as tenant_err:
        scope_tenant(_user(TENANT_A), TENANT_B)
    assert tenant_err.value.code == "TENANT_MISMATCH"
    with pytest.raises(AppError) as row_err:
        assert_tenant_object(_user(TENANT_A), TENANT_B)
    assert row_err.value.code == "TENANT_MISMATCH"


def test_24_phase_6_13_1_to_6_13_6_regression():
    """Legacy scope resolution, sign-in guard, and schemas stay locked."""
    # Legacy tenant-bound unscoped row stays INSTITUTION (never widened).
    legacy_tenant_row = {
        "role_id": ROLE_ID,
        "role_name": "student",
        "is_active": True,
        "scope_type": None,
        "scope_id": None,
        "scope_organization_id": None,
    }
    ctx = _resolve(
        [legacy_tenant_row],
        current_user={"user_id": INST_ADMIN, "institution_id": INST_A},
    )
    assert ctx["scope_type"] == authz.INSTITUTION
    assert ctx["institution_id"] == INST_A
    # Legacy tenant-less unscoped row stays PLATFORM.
    ctx_platform = _resolve([legacy_tenant_row])
    assert ctx_platform["scope_type"] == authz.PLATFORM
    # Sign-in guard: missing account and non-active user fail closed.
    from app.services.auth.sign_in import assert_sign_in_allowed

    with pytest.raises(SafeAuthFailure):
        assert_sign_in_allowed(MagicMock(), None)
    with pytest.raises(SafeAuthFailure):
        assert_sign_in_allowed(
            MagicMock(),
            {
                "user_id": USER_ADMIN,
                "status": "inactive",
                "institution_id": None,
                "approval_status": None,
                "student_is_active": None,
            },
        )
    assert (
        assert_sign_in_allowed(
            MagicMock(),
            {
                "user_id": USER_ADMIN,
                "status": "active",
                "institution_id": None,
                "approval_status": None,
                "student_is_active": None,
            },
        )
        is None
    )
    # Decision vocabulary and schema locks are untouched.
    assert tenancy_svc.ORGANIZATION_DECISION_STATUS == {
        "approve": "active",
        "reject": "rejected",
    }
    from app.schemas.platform.tenancy import ApprovalDecisionRequest

    with pytest.raises(Exception):
        ApprovalDecisionRequest.model_validate(
            {"decision": "approve", "scope_type": "platform"}
        )
