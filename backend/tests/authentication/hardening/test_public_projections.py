"""Authentication hardening regressions: public projections."""

from __future__ import annotations

from .support import (
    AsyncMock,
    InstitutionLookupResponse,
    MagicMock,
    SUBMITTED_PASSWORD,
    SimpleNamespace,
    UserRegistrationResponse,
    _dev_flag_off_and_no_overrides,
    _fake_claims,
    client,
    patch,
    resolved_principal,
)


def test_auth_me_exposes_only_the_documented_fields():
    user = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": _fake_claims()["sub"],
        "email": "student@college.edu",
        "roles": ["student"],
        "institution_id": "30000000-0000-0000-0000-000000000001",
    }
    with patch("app.core.security.tokens.verify_jwt", return_value=_fake_claims()), patch(
        "app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=resolved_principal(user))
    ):
        response = client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer valid.token.here"}
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "authenticated",
        "user_id",
        "auth_user_id",
        "email",
        "role",
        "institution_id",
        "effective_permissions",
    }
    # No role list, no scope machinery, no provider metadata beyond the
    # authenticated user's own identity (the JWT `sub` the caller already holds).
    for forbidden in (
        "roles",
        "password",
        "password_hash",
        "is_admin",
        "scope_type",
        "scope_id",
        "organization_id",
        "access_token",
        "refresh_token",
        "service_role",
        "provider",
        "session",
    ):
        assert forbidden not in body


def test_login_response_is_minimal_and_never_echoes_the_password():
    """The locked login contract carries no role, scope, or credential echo."""
    session = SimpleNamespace(
        access_token="mock-access-token",
        refresh_token="mock-refresh-token",
        expires_in=3600,
    )
    user = SimpleNamespace(id="auth-user-1", email="admin@college.edu")
    auth_client = MagicMock()
    auth_client.auth.sign_in_with_password.return_value = SimpleNamespace(
        session=session, user=user
    )
    account = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "status": "active",
        "institution_id": None,
        "approval_status": None,
        "student_is_active": None,
    }
    with patch("app.api.auth.common.create_supabase_client", return_value=auth_client), patch(
        "app.api.auth.common.get_sign_in_context", new=AsyncMock(return_value=account)
    ), patch("app.api.auth.common.get_admin_client", return_value=MagicMock()):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@college.edu", "password": SUBMITTED_PASSWORD},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {
        "access_token",
        "refresh_token",
        "expires_in",
        "message",
        "user",
    }
    assert body["refresh_token"] == "mock-refresh-token"
    assert body["expires_in"] == 3600
    assert set(body["user"].keys()) == {"id", "email"}
    for forbidden in ("role", "roles", "is_admin", "password", "institution_id", "scope"):
        assert forbidden not in body
    # The plaintext password is never echoed back in any form.
    assert SUBMITTED_PASSWORD not in response.text


def test_registration_response_schema_has_no_privileged_or_credential_fields():
    """POST /users/register can never return a token, role, or plan field."""
    fields = set(UserRegistrationResponse.model_fields)
    assert fields == {
        "message",
        "user_id",
        "institution_id",
        "institution_code",
        "registration_type",
        "approval_status",
        "student_id",
        "request_id",
    }
    for forbidden in (
        "access_token",
        "refresh_token",
        "token",
        "role",
        "roles",
        "is_admin",
        "scope_type",
        "scope_id",
        "password",
        "password_hash",
    ):
        assert forbidden not in fields


def test_institution_lookup_projection_is_exactly_the_public_triple():
    """The public lookup can never become an institution directory."""
    assert set(InstitutionLookupResponse.model_fields) == {
        "institution_id",
        "code",
        "name",
    }
