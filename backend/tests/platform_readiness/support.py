"""Shared authorization principals and test doubles."""

from contextlib import ExitStack, contextmanager

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import uuid4

import pytest

from fastapi.testclient import TestClient

from app.core.errors import AppError

from app.core.security import (
    assert_tenant_object,
    require_roles,
    resolve_primary_role,
    scope_tenant,
)

from app.main import app

from app.services.knowledge.ingestion import _safe_filename, _validate

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "30000000-0000-0000-0000-000000000001"

TENANT_B = "30000000-0000-0000-0000-000000000002"

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}

USER_ID = "30000000-0000-0000-0000-000000000701"

STUDENT_A = "30000000-0000-0000-0000-000000000101"

STUDENT_B = "30000000-0000-0000-0000-000000000102"

CLAIMS = {"sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "email": "p@college.edu"}


def _user(role="student", tenant=TENANT_A):
    return {
        "user_id": USER_ID,
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
    }


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    """Provide an ACTIVE institution to the scoped admin dependency only."""
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={"institution_id": TENANT_A, "status": "active", "is_active": True}
    )
    with patch("app.services.auth.authorization.get_admin_client", return_value=db):
        yield


@contextmanager
def _auth(role="student", tenant=TENANT_A):
    principal = _user(role, tenant)
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
    """Return the error envelope; ``code``/``message`` are always present.

    Validation failures (422) additionally carry a ``details`` list — the
    pre-existing contract. No other key is ever allowed, so an accidental
    leak of internals into the envelope is caught here.
    """
    body = response.json()
    assert "error" in body, f"expected error envelope got: {body!r}"
    keys = set(body["error"].keys())
    assert {"code", "message"} <= keys, f"missing envelope keys: {keys}"
    assert keys <= {"code", "message", "details"}, f"unexpected envelope keys: {keys}"
    return body["error"]


def _assert_no_leak(text: str):
    lowered = text.lower()
    for marker in (
        "traceback",
        "select ",
        "supabase",
        "access_token",
        "refresh_token",
        "service_role",
        "secret",
        "password",
    ):
        assert marker not in lowered, f"leak {marker!r} in: {text[:300]!r}"
