from .support import (
    AUTH_HEADERS,
    AppError,
    TENANT_A,
    _active_institution_authorization,
    _assert_no_leak,
    _auth,
    _envelope,
    client,
    patch,
    resolve_primary_role,
)


def test_missing_token_is_401_auth_required():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert _envelope(r)["code"] == "AUTH_REQUIRED"
    _assert_no_leak(r.text)


def test_empty_bearer_token_is_401():
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer  "})
    assert r.status_code == 401
    assert _envelope(r)["code"] == "TOKEN_MISSING"


def test_invalid_token_is_401_without_internals():
    with patch(
        "app.core.security.tokens.verify_jwt",
        side_effect=AppError("Invalid token", status_code=401, code="INVALID_TOKEN"),
    ):
        r = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert r.status_code == 401
    assert _envelope(r)["code"] == "INVALID_TOKEN"
    _assert_no_leak(r.text)


def test_expired_token_is_401_token_expired():
    with patch(
        "app.core.security.tokens.verify_jwt",
        side_effect=AppError(
            "Token has expired", status_code=401, code="TOKEN_EXPIRED"
        ),
    ):
        r = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert r.status_code == 401
    assert _envelope(r)["code"] == "TOKEN_EXPIRED"


def test_auth_me_shape_is_stable_and_minimal():
    with _auth("admin", TENANT_A):
        r = client.get("/api/v1/auth/me", headers=AUTH_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {
        "authenticated",
        "user_id",
        "auth_user_id",
        "email",
        "role",
        "institution_id",
        "institution_code",
        "effective_permissions",
    }
    assert body["role"] == "admin"
    assert "access_token" not in body


def test_expired_token_on_conversations_is_401():
    with patch(
        "app.core.security.tokens.verify_jwt",
        side_effect=AppError(
            "Token has expired", status_code=401, code="TOKEN_EXPIRED"
        ),
    ):
        r = client.get("/api/v1/conversations", headers=AUTH_HEADERS)
    assert r.status_code == 401
    assert _envelope(r)["code"] == "TOKEN_EXPIRED"
    _assert_no_leak(r.text)


def test_client_role_values_never_influence_resolution():
    assert resolve_primary_role(["student"]) == "student"
    assert resolve_primary_role(["admin", "student"]) == "admin"
    assert resolve_primary_role(["superadmin", "root"]) is None
    assert resolve_primary_role([]) is None
    assert resolve_primary_role(None) is None
