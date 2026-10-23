"""Identity constants and authorization fixtures."""

from __future__ import annotations

import asyncio

import inspect

import re

from pathlib import Path

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import pytest

from fastapi.testclient import TestClient

from supabase_auth.errors import AuthApiError

from app.core.errors import AppError

from app.core.security import (
    PUBLIC_USER_ID,
    assert_tenant_object,
    get_current_user,
    require_roles,
    scope_tenant,
)

from app.main import app

from app.repositories.platform import tenancy as tenancy_repo

from app.services.auth import authorization as authz

from app.services.platform import tenancy as tenancy_svc

from app.services.auth.student_auth import SafeAuthFailure

client = TestClient(app, raise_server_exceptions=False)

ORG_A = "a0000000-0000-0000-0000-00000000000a"

ORG_B = "b0000000-0000-0000-0000-00000000000b"

INST_A1 = "10000000-0000-0000-0000-0000000000a1"

INST_A2 = "10000000-0000-0000-0000-0000000000a2"

INST_B1 = "10000000-0000-0000-0000-0000000000b1"

KS_FAQ_A1 = "20000000-0000-0000-0000-0000000000a1"

KS_PRIVATE_A1 = "20000000-0000-0000-0000-0000000000a2"

KS_FAQ_B1 = "20000000-0000-0000-0000-0000000000b1"

RUN_FAQ_A1 = "30000000-0000-0000-0000-0000000000a1"

RUN_PRIVATE_A1 = "30000000-0000-0000-0000-0000000000a2"

RUN_FAQ_B1 = "30000000-0000-0000-0000-0000000000b1"

CHUNK_FAQ_A1 = "40000000-0000-0000-0000-0000000000a1"

CHUNK_PRIVATE_A1 = "40000000-0000-0000-0000-0000000000a2"

CHUNK_FAQ_B1 = "40000000-0000-0000-0000-0000000000b1"

SESSION_ID = "00000000-0000-0000-0000-000000000999"

CONVERSATION_ID = "50000000-0000-0000-0000-000000000001"

MESSAGE_ID = "50000000-0000-0000-0000-000000000002"

ROLE_ID = "e0000000-0000-0000-0000-000000000001"

USER_PLATFORM = "c0000000-0000-0000-0000-000000000001"

USER_ORG_A = "c0000000-0000-0000-0000-000000000002"

USER_ORG_B = "c0000000-0000-0000-0000-000000000003"

USER_INST_A1 = "c0000000-0000-0000-0000-000000000004"

USER_STUDENT_A1 = "c0000000-0000-0000-0000-000000000005"

USER_FACULTY_A1 = "c0000000-0000-0000-0000-000000000006"

USER_STAFF_A1 = "c0000000-0000-0000-0000-000000000007"

STUDENT_ID_A1 = "d0000000-0000-0000-0000-000000000001"

STUDENT_ID_B1 = "d0000000-0000-0000-0000-000000000002"

JR_A = "60000000-0000-0000-0000-000000000001"

JR_B = "60000000-0000-0000-0000-000000000002"

MR_A = "70000000-0000-0000-0000-000000000001"

MR_A = "70000000-0000-0000-0000-000000000001"


def _user(tenant=None, roles=("admin",), user_id=None):
    return {
        "user_id": user_id or str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "phase6139@example.com",
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


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    """Supply an ACTIVE institution to the scoped admin dependency only.

    Phase 7.20's ``require_institution_roles`` resolves the caller's institution
    from the server-owned ``user_roles`` grant and verifies its lifecycle through
    the authorization module's service-role client. This fixture swaps ONLY that
    client so endpoint tests exercise the real guard. The tenancy repository is
    deliberately left untouched so the public-AI pipeline and the lifecycle
    security tests keep resolving real institution rows.
    """
    from .database import _FakeClient
    from .state import _base_state

    with patch(
        "app.services.auth.authorization.get_admin_client",
        return_value=_FakeClient(_base_state()),
    ):
        yield


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
    cu = current_user or {"user_id": USER_PLATFORM, "institution_id": None}
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch.object(tenancy_repo, "get_user_role_scope_rows", return_value=rows),
        patch.object(
            tenancy_repo, "get_institution_organization", return_value=UUID(ORG_A)
        ),
    ):
        return authz.resolve_authorization_context(cu)


def _deep_values(obj):
    """Yield every string/number value found anywhere in a nested structure."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from _deep_values(value)
    elif isinstance(obj, (list, tuple, set)):
        for value in obj:
            yield from _deep_values(value)
    elif obj is not None:
        yield str(obj)


LOGIN_URL = "/api/v1/auth/login"

STUDENT_LOGIN_URL = "/api/v1/auth/student/login"
