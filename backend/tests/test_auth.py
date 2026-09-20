"""
Tests for Phase 17.5 — Supabase Auth JWT verification.

Scenarios:
  1. Missing Authorization header        → 401
  2. Invalid Bearer token                → 401
  3. Expired JWT                         → 401
  4. Valid JWT, no matching public.users → 404
  5. Valid JWT, matching public.users    → 200
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.supabase import get_user_by_auth_id
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "student@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FAKE_USER = {
    "id": 1,
    "user_id": 1,
    "auth_user_id": FAKE_CLAIMS["sub"],
    "email": FAKE_CLAIMS["email"],
    "roles": [],
}


def _patch_verify(claims=FAKE_CLAIMS):
    return patch("app.core.security.verify_jwt", return_value=claims)


def _patch_db(user=FAKE_USER):
    return patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=user))


@pytest.mark.asyncio
async def test_get_user_by_auth_id_uses_actual_users_schema():
    client = MagicMock()
    users_table = client.table.return_value
    users_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "user_roles": [
            {"roles": {"name": "student", "is_active": True}},
            {"roles": {"name": "disabled", "is_active": False}},
        ],
        "students": [
            {"institution_id": "30000000-0000-0000-0000-000000000001"},
        ],
    }

    with patch("app.db.supabase.get_admin_client", return_value=client):
        result = await get_user_by_auth_id(FAKE_CLAIMS["sub"])

    assert result == {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "roles": ["student"],
        "institution_id": "30000000-0000-0000-0000-000000000001",
    }
    users_table.select.assert_called_once_with(
        "user_id, auth_user_id, email, "
        "user_roles(roles(name, is_active)), "
        "students(institution_id)"
    )
    users_table.select.return_value.eq.assert_called_once_with(
        "auth_user_id", FAKE_CLAIMS["sub"]
    )


@pytest.mark.asyncio
async def test_get_user_by_auth_id_without_student_profile_has_no_tenant():
    """Platform-level accounts (no students row) resolve to institution_id=None."""
    client = MagicMock()
    users_table = client.table.return_value
    users_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "user_id": "30000000-0000-0000-0000-000000000102",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "user_roles": [
            {"roles": {"name": "admin", "is_active": True}},
        ],
        "students": [],
    }

    with patch("app.db.supabase.get_admin_client", return_value=client):
        result = await get_user_by_auth_id(FAKE_CLAIMS["sub"])

    assert result["institution_id"] is None


@pytest.mark.asyncio
async def test_get_user_by_auth_id_handles_one_to_one_students_object():
    """Regression: PostgREST embeds the students relation as a single OBJECT
    (not a list) when the FK is detected as one-to-one. This is what the live
    Supabase schema returns and previously crashed with ``KeyError: 0``.
    """
    client = MagicMock()
    users_table = client.table.return_value
    users_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "user_id": "30000000-0000-0000-0000-000000000103",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "user_roles": [
            {"roles": {"name": "student", "is_active": True}},
        ],
        "students": {
            "institution_id": "30000000-0000-0000-0000-000000000001",
        },
    }

    with patch("app.db.supabase.get_admin_client", return_value=client):
        result = await get_user_by_auth_id(FAKE_CLAIMS["sub"])

    assert result == {
        "user_id": "30000000-0000-0000-0000-000000000103",
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FAKE_CLAIMS["email"],
        "roles": ["student"],
        "institution_id": "30000000-0000-0000-0000-000000000001",
    }


# ---------------------------------------------------------------------------
# 1. Missing Authorization header
# ---------------------------------------------------------------------------

def test_missing_auth_header():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# ---------------------------------------------------------------------------
# 2. Invalid Bearer token (bad signature / malformed)
# ---------------------------------------------------------------------------

def test_invalid_token():
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


# ---------------------------------------------------------------------------
# 3. Expired JWT
# ---------------------------------------------------------------------------

def test_expired_token():
    from jwt import ExpiredSignatureError
    with patch(
        "app.core.security._get_jwks_client",
        side_effect=ExpiredSignatureError("expired"),
    ):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake.expired.token"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# 4. Valid JWT but no matching public.users row
# ---------------------------------------------------------------------------

def test_valid_jwt_no_user():
    with _patch_verify(), _patch_db(user=None):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


# ---------------------------------------------------------------------------
# 5. Valid JWT with matching public.users row
# ---------------------------------------------------------------------------

def test_valid_jwt_with_user():
    with _patch_verify(), _patch_db():
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["auth_user_id"] == FAKE_CLAIMS["sub"]
    assert body["email"] == FAKE_CLAIMS["email"]
    # Phase 6.15.4 — additive canonical identity fields.
    assert body["role"] is None
    assert body["institution_id"] is None


# ---------------------------------------------------------------------------
# Phase 6.15.4 — canonical identity contract on GET /auth/me
# ---------------------------------------------------------------------------

def test_auth_me_returns_admin_role():
    user = dict(FAKE_USER, roles=["admin"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert body["authenticated"] is True


def test_auth_me_returns_staff_role():
    user = dict(FAKE_USER, roles=["staff"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    assert response.json()["role"] == "staff"


def test_auth_me_returns_faculty_role():
    user = dict(FAKE_USER, roles=["faculty"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    assert response.json()["role"] == "faculty"


def test_auth_me_returns_student_role_with_tenant():
    """Student: role + tenant resolved in the correct institution context."""
    institution_id = "30000000-0000-0000-0000-000000000001"
    user = dict(FAKE_USER, roles=["student"], institution_id=institution_id)
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"
    assert body["institution_id"] == institution_id
    # Multi-role account: the canonical role is a single value.
    assert isinstance(body["role"], str)


def test_auth_me_resolves_highest_precedence_role_for_multi_role_account():
    """admin > staff > faculty > student precedence (existing RBAC preserved)."""
    from app.core.security import resolve_primary_role

    assert resolve_primary_role(["student", "admin"]) == "admin"
    assert resolve_primary_role(["faculty", "staff"]) == "staff"
    assert resolve_primary_role(["student", "faculty"]) == "faculty"
    assert resolve_primary_role(["student"]) == "student"


def test_auth_me_unknown_role_resolves_to_none_fail_safe():
    """A role outside the supported set must never surface as privileged."""
    from app.core.security import resolve_primary_role

    user = dict(FAKE_USER, roles=["superuser"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"})
    assert response.status_code == 200
    assert response.json()["role"] is None
    assert resolve_primary_role(["superuser", "root"]) is None
    assert resolve_primary_role([]) is None
    assert resolve_primary_role(None) is None


def test_auth_me_ignores_client_provided_role_or_tenant_data():
    """Security: query/body data can never influence the resolved role.

    The role comes only from the server-side user_roles chain; extra query
    parameters are ignored (no injection surface), and the response role is
    derived exclusively from the authenticated identity.
    """
    user = dict(FAKE_USER, roles=["student"])
    with _patch_verify(), _patch_db(user=user):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid.token.here"},
            params={"role": "admin", "institution_id": "00000000-0000-0000-0000-000000000099"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"
    assert body["institution_id"] != "00000000-0000-0000-0000-000000000099"


def test_auth_me_unauthenticated_rejected_preserved():
    """Regression: the unauthenticated 401 AUTH_REQUIRED contract is intact."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# ---------------------------------------------------------------------------
# Health check remains public
# ---------------------------------------------------------------------------

def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
