"""Support."""

from __future__ import annotations

from app.api.admin.dependencies import _ADMIN

from app.api.admin.dependencies import _APPROVAL

from app.core.security import get_current_user

from app.main import app

from contextlib import contextmanager

from fastapi.testclient import TestClient

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

import pytest


client = TestClient(app, raise_server_exceptions=False)


INST_A = "71000000-0000-0000-0000-00000000000a"


INST_B = "71000000-0000-0000-0000-00000000000b"


ADMIN_A = "72000000-0000-0000-0000-00000000000a"


ADMIN_B = "72000000-0000-0000-0000-00000000000b"


STUDENT_A = "73000000-0000-0000-0000-00000000000a"


STUDENT_B = "73000000-0000-0000-0000-00000000000b"


RESOURCE_ID = "74000000-0000-0000-0000-000000000001"


def _grant(role: str, institution_id: str, scope_type: str = "institution") -> dict:
    return {
        "role": role,
        "scope_type": scope_type,
        "scope_id": institution_id,
        "scope_organization_id": None,
        "is_active": True,
    }


def _principal(
    user_id: str,
    role: str,
    institution_id: str | None,
    *,
    status: str = "active",
    scope_type: str = "institution",
) -> dict:
    assignments = (
        [_grant(role, institution_id, scope_type)] if institution_id is not None else []
    )
    return {
        "user_id": user_id,
        "auth_user_id": user_id,
        "email": f"{role}@example.edu",
        "status": status,
        "roles": [role],
        # Deliberately None: the dependency must use role_assignments.scope_id.
        "institution_id": None,
        "role_assignments": assignments,
    }


ADMIN_A_USER = _principal(ADMIN_A, "admin", INST_A)


ADMIN_B_USER = _principal(ADMIN_B, "admin", INST_B)


@pytest.fixture(
    params=[(INST_A, INST_B), (INST_B, INST_A)], ids=["a-then-b", "b-then-a"]
)
def conflicting_admin(request: pytest.FixtureRequest) -> dict:
    principal = _principal(ADMIN_A, "admin", None)
    principal["role_assignments"] = [
        _grant("admin", institution_id) for institution_id in request.param
    ]
    return principal


def _active_institution(institution_id: UUID | str) -> dict:
    return {
        "institution_id": str(institution_id),
        "status": "active",
        "is_active": True,
    }


@contextmanager
def _authenticated(principal: dict, *, institution_active: bool = True):
    app.dependency_overrides[get_current_user] = lambda: principal
    institution = (
        _active_institution(principal["role_assignments"][0]["scope_id"])
        if institution_active and principal.get("role_assignments")
        else {"status": "suspended", "is_active": False}
    )
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            return_value=institution,
        ),
    ):
        yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def authorized_admin_endpoint():
    """Keep real scoped authorization while isolating endpoint database access."""
    permissions = ["audit.read", "documents.read"]
    principal = dict(
        ADMIN_A_USER,
        permissions_resolved=True,
        scoped_permissions_resolved=True,
        effective_permissions=list(permissions),
        direct_permission_grants=[],
        role_assignments=[
            dict(grant, permissions=list(permissions))
            for grant in ADMIN_A_USER["role_assignments"]
        ],
    )
    db = object()
    with (
        _authenticated(principal),
        patch("app.api.admin.common.get_admin_client", return_value=db),
    ):
        yield db


@pytest.fixture(autouse=True)
def _clean_dependencies():
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)
    yield
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)
