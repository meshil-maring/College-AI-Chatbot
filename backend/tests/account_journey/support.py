"""Shared authorization principals and test doubles."""

from contextlib import ExitStack, contextmanager

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from app.core.errors import AppError

from app.main import app
from tests.auth_fixtures.principals import resolved_principal

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"

FOREIGN_TENANT = "30000000-0000-0000-0000-0000000000ff"

USER_ID = "30000000-0000-0000-0000-000000000701"

STUDENT_ID = "30000000-0000-0000-0000-000000000151"

OTHER_STUDENT_ID = "30000000-0000-0000-0000-000000000152"

KNOWLEDGE_SOURCE_ID = "30000000-0000-0000-0000-000000000111"

PROCESSING_RUN_ID = "30000000-0000-0000-0000-000000000941"

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}

CLAIMS = {"sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "email": "demo@college.edu"}


def _user(role="student", tenant=INSTITUTION_A, user_id=USER_ID):
    return resolved_principal({
        "user_id": user_id,
        "auth_user_id": CLAIMS["sub"],
        "email": f"{role}@college.edu",
        "roles": [role],
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
        ],
    })


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    """Provide an ACTIVE institution to the scoped admin dependency only."""
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={"institution_id": INSTITUTION_A, "status": "active", "is_active": True}
    )
    with patch("app.services.auth.authorization.get_admin_client", return_value=db):
        yield


@contextmanager
def _auth(role="student", tenant=INSTITUTION_A, user_id=USER_ID):
    principal = _user(role, tenant, user_id)
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.tokens.verify_jwt", return_value=dict(CLAIMS))
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=principal),
            )
        )
        yield principal


def _envelope(response):
    """Return the error envelope; only {code, message[, details]} is ever exposed."""
    body = response.json()
    assert "error" in body, f"expected error envelope got: {body!r}"
    error = body["error"]
    assert {"code", "message"} <= set(error), f"missing envelope keys: {error}"
    assert set(error) <= {"code", "message", "details"}, f"leaked keys: {error}"
    return error


def _registration_payload(**overrides):
    payload = {
        "institution_id": INSTITUTION_A,
        "email": "phase622.student@demo.collegelocal.dev",
        "password": "DemoPassword!622",
        "first_name": "Demo",
        "last_name": "Student",
        "register_number": "622001",
        "university_roll_number": "R622001",
    }
    payload.update(overrides)
    return payload


_LOGIN_URL = "/api/v1/auth/student/login"

_SESSION = {
    "access_token": "student.session.token",
    "refresh_token": "student-refresh-token",
    "expires_in": 3600,
    "user": {"id": CLAIMS["sub"], "email": "student@college.edu"},
}
