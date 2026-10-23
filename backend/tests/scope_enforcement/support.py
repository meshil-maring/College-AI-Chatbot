"""Support."""

from __future__ import annotations

from app.core.security import (
    assert_tenant_object,
    get_current_user,
    require_roles,
    scope_tenant,
)

from app.main import app

from app.repositories.platform import tenancy as tenancy_repo

from app.services.auth import authorization as authz

from fastapi.testclient import TestClient

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4


client = TestClient(app, raise_server_exceptions=False)


ORG_A = "a0000000-0000-0000-0000-00000000000a"


ORG_B = "a0000000-0000-0000-0000-00000000000b"


INST_A = "b0000000-0000-0000-0000-00000000000a"


INST_B = "b0000000-0000-0000-0000-00000000000b"


TENANT_A = INST_A  # institution A is tenant A for the academic endpoints


TENANT_B = INST_B


JR_A = "d0000000-0000-0000-0000-000000000001"


MR_A = "e1000000-0000-0000-0000-000000000001"


KS_A = "40000000-0000-0000-0000-00000000000a"


KS_B = "40000000-0000-0000-0000-00000000000b"


RUN_ID = "a0000000-0000-0000-0000-0000000000f1"


DV_ID = "d0000000-0000-0000-0000-0000000000f1"


STUDENT_A = "30000000-0000-0000-0000-000000000151"


ROLE_ID = "e0000000-0000-0000-0000-000000000001"


USER_ADMIN = "c0000000-0000-0000-0000-000000000001"


ORG_ADMIN = "c0000000-0000-0000-0000-000000000002"


INST_ADMIN = "c0000000-0000-0000-0000-000000000003"


def _user(tenant=None, roles=("admin",), user_id=None):
    return {
        "user_id": user_id or str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "phase6137@example.com",
        "roles": list(roles),
        "institution_id": tenant,
        "status": "active",
        "role_assignments": [
            {
                "role": role,
                "scope_type": "institution" if tenant else "platform",
                "scope_id": tenant,
                "scope_organization_id": None,
                "is_active": True,
            }
            for role in roles
        ],
    }


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear():
    app.dependency_overrides.pop(get_current_user, None)


def _role_row(scope_type, scope_id, org_id, role="admin"):
    return {
        "role_id": ROLE_ID,
        "role_name": role,
        "is_active": True,
        "scope_type": scope_type,
        "scope_id": scope_id,
        "scope_organization_id": org_id,
    }


def _resolve(rows, current_user=None):
    """Run resolve_authorization_context for real against mocked role rows."""
    cu = current_user or {"user_id": USER_ADMIN, "institution_id": None}
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo,
            "get_institution_organization",
            return_value=UUID(ORG_A),
        ),
    ):
        return authz.resolve_authorization_context(cu)


def _authz_patches(user_id: str, rows: list):
    """Mock the authorization-context sources (same seams as Phase 6.13.4)."""
    return (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo,
            "get_institution_organization",
            return_value=UUID(ORG_A),
        ),
    )


def _org_ctx():
    return _resolve([_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])


def _inst_ctx():
    return _resolve([_role_row(authz.INSTITUTION, INST_A, ORG_A)])


def _login(user):
    _as(user)


def _logout():
    _clear()


def _decision(decision: str, reason: str | None = None):
    body = {"decision": decision}
    if reason is not None:
        body["decision_reason"] = reason
    return body
