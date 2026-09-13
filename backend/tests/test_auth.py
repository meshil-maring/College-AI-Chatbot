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


# ---------------------------------------------------------------------------
# Health check remains public
# ---------------------------------------------------------------------------

def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
