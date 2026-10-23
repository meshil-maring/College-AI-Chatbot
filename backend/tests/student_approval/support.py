"""Support."""

from __future__ import annotations

from app.api.admin.dependencies import _APPROVAL

from app.core.security import get_current_user

from app.main import app

from fastapi.testclient import TestClient

from types import SimpleNamespace

from unittest.mock import MagicMock, patch

from uuid import uuid4

import pytest


client = TestClient(app, raise_server_exceptions=False)


TENANT_A = "a1111111-0000-0000-0000-000000000001"


TENANT_B = "b2222222-0000-0000-0000-000000000002"


STUDENT_A = "30000000-0000-0000-0000-000000000151"


STUDENT_B = "30000000-0000-0000-0000-000000000152"


def _user(tenant=None, roles=("admin",)):
    """A principal shaped exactly like ``get_current_user`` after Phase 7.20.

    Institution scope for every non-student role comes from the server-owned
    ``user_roles`` grant (``role_assignments``); a tenant-less account therefore
    holds a ``platform`` grant, never an institution grant.
    """
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "approver@example.com",
        "roles": list(roles),
        "status": "active",
        "institution_id": tenant,
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
    """Give the scoped admin dependency an ACTIVE institution to resolve.

    ``require_institution_roles`` verifies institution lifecycle through the
    authorization module's service-role client; only that client is stubbed so
    the real guard logic still runs.
    """
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={"institution_id": TENANT_A, "status": "active", "is_active": True}
    )
    with patch("app.services.auth.authorization.get_admin_client", return_value=client):
        yield


def _pending_row(student_id=STUDENT_A, tenant=TENANT_A, **over):
    row = {
        "student_id": student_id,
        "user_id": str(uuid4()),
        "institution_id": tenant,
        "student_number": "1001",
        "email": "s@college.example.com",
        "register_number": "1001",
        "university_roll_number": "2026-1001",
        "approval_status": "pending",
        "status": "active",
        "is_active": True,
        "enrollment_date": "2026-09-12",
        "created_at": "2026-09-12T00:00:00+00:00",
        "updated_at": "2026-09-12T00:00:00+00:00",
    }
    row.update(over)
    return row


def _as(role_user):
    app.dependency_overrides[get_current_user] = lambda: role_user


def _clear():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_APPROVAL, None)
