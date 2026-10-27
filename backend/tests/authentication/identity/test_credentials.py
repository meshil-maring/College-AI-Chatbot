"""Authentication identity regressions: credentials."""

from __future__ import annotations

from .support import (
    FAKE_CLAIMS,
    _patch_db,
    _patch_verify,
    client,
    patch,
)


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
        "app.core.security.tokens._get_jwks_client",
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
