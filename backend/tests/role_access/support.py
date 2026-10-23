"""Support."""

from __future__ import annotations

from app.api.admin.dependencies import _ADMIN

from app.api.admin.dependencies import _APPROVAL

from app.api.knowledge.ingestion import _INGEST_ALLOWED

from app.core.security import get_current_user

from app.main import app

from fastapi.testclient import TestClient

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import uuid4

import pytest


client = TestClient(app, raise_server_exceptions=False)


TENANT_A = "a1111111-0000-0000-0000-000000000001"


TENANT_B = "b2222222-0000-0000-0000-000000000002"


STUDENT_A = "30000000-0000-0000-0000-000000000151"


KS_ID = "40000000-0000-0000-0000-000000000111"


RUN_ID = "a0000000-0000-0000-0000-000000000001"


def _user(tenant=None, roles=("admin",)):
    assignments = [
        {
            "role": role,
            "scope_type": "institution",
            "scope_id": tenant,
            "scope_organization_id": None,
            "is_active": True,
        }
        for role in roles
        if tenant is not None
    ]
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "rbac@example.com",
        "roles": list(roles),
        "status": "active",
        "institution_id": tenant,
        "role_assignments": assignments,
    }


@pytest.fixture(autouse=True)
def _active_scope_lookup():
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            side_effect=lambda _db, institution_id: {
                "institution_id": str(institution_id),
                "status": "active",
                "is_active": True,
            },
        ),
    ):
        yield


def _as(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _clear():
    for dep in (get_current_user, _ADMIN, _APPROVAL, _INGEST_ALLOWED):
        app.dependency_overrides.pop(dep, None)
