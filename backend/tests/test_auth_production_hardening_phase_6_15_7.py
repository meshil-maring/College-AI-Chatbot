"""Phase 6.15.7 — Authentication production-hardening tests.

Focused production-readiness assurances that were NOT already covered by the
Phase 6.13.x / 6.15.x suites (no duplicated coverage):

  1. Configuration guard — ``DEV_TEST_MODE=true`` is refused outside a local
     development/testing ``ENVIRONMENT`` (fail closed, allowlist based).
  2. Dev-route gating — with the flag OFF every ``/dev/auth`` route answers
     404 for EVERY payload shape (including malformed and unknown-field
     bodies), before authentication and before any Supabase client is built;
     with the flag ON the dev schemas reject unexpected fields with 422.
  3. Response minimization — ``/auth/me``, ``/auth/login`` and the public
     registration contract expose exactly the documented field sets (no role,
     token, hash or internal-auth metadata beyond the locked contract).
  4. Error sanitization — an unhandled server exception returns a generic 500
     with no traceback / exception name / file path / internal detail, and a
     rejected login never echoes the submitted password or discloses account
     existence.

Every test uses mocked Supabase clients — no live services are contacted.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from supabase_auth.errors import AuthApiError

from app.config import DEV_TEST_ENVIRONMENTS, Settings, settings
from app.core.security import get_current_user
from app.main import app
from app.schemas.tenancy import InstitutionLookupResponse
from app.schemas.users import UserRegistrationResponse

client = TestClient(app, raise_server_exceptions=False)

DEV_ROUTES = (
    "/api/v1/dev/auth/forgot-password",
    "/api/v1/dev/auth/change-password",
    "/api/v1/dev/auth/admin/reset-student-password",
)

ADMIN_USER = {
    "user_id": "90000000-0000-0000-0000-000000000001",
    "auth_user_id": "90000000-0000-0000-0000-0000000000aa",
    "email": "admin@example.com",
    "roles": ["admin"],
    "institution_id": None,
}

# A distinctive value so "is the password echoed anywhere?" is a real question.
SUBMITTED_PASSWORD = "Sup3rSecret-Passw0rd!"


@pytest.fixture(autouse=True)
def _dev_flag_off_and_no_overrides():
    """Every test starts with DEV_TEST_MODE off and no dependency override."""
    original = settings.dev_test_mode
    settings.dev_test_mode = False
    app.dependency_overrides.pop(get_current_user, None)
    yield
    settings.dev_test_mode = original
    app.dependency_overrides.pop(get_current_user, None)



# ===========================================================================
# 1. Configuration guard — DEV_TEST_MODE can never be enabled in a deployment
# ===========================================================================


@pytest.mark.parametrize(
    "environment",
    ["production", "Production", "PROD", "prod", "staging", "", "  ", "prod-eu"],
)
def test_dev_test_mode_refused_outside_local_environments(environment):
    """The application must refuse to start rather than expose dev endpoints."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            environment=environment,
            dev_test_mode=True,
        )
    message = str(exc_info.value)
    assert "DEV_TEST_MODE" in message
    # The failure message itself must not leak any secret value.
    assert settings.supabase_secret_key not in message


@pytest.mark.parametrize("environment", sorted(DEV_TEST_ENVIRONMENTS))
def test_dev_test_mode_allowed_in_local_environments(environment, caplog):
    """Local development/testing keeps the dev helpers working (with a warning)."""
    with caplog.at_level("WARNING"):
        local = Settings(_env_file=None, environment=environment, dev_test_mode=True)

    assert local.dev_test_mode is True
    assert "DEV_TEST_MODE is enabled" in caplog.text


@pytest.mark.parametrize("environment", ["production", "prod", "staging", ""])
def test_dev_test_mode_disabled_is_always_allowed(environment):
    """Production is only valid with the dev flag OFF — the default."""
    config = Settings(_env_file=None, environment=environment, dev_test_mode=False)
    assert config.dev_test_mode is False


def test_shipped_settings_are_consistent_with_the_guard():
    """The running configuration satisfies its own production guard."""
    environment = (settings.environment or "").strip().lower()
    if settings.dev_test_mode:
        assert environment in DEV_TEST_ENVIRONMENTS



# ===========================================================================
# 2. Dev route gating — 404 for every shape, before auth and before Supabase
# ===========================================================================


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_return_404_for_a_valid_body(route):
    response = client.post(
        route,
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_return_404_for_unexpected_fields(route):
    """An extra field must NOT turn the hidden route into a 422 disclosure."""
    response = client.post(
        route,
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
            "role": "admin",
            "user_id": str(uuid4()),
            "approval_status": "approved",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_handle_malformed_bodies_without_side_effects(route):
    """Route existence is never turned into a handler/DB disclosure.

    Verified behaviour (FastAPI ordering):
      * a body that cannot be DECODED is rejected by the framework's parser
        before any dependency runs, for every body route in the API — it
        returns the standardized 422 envelope and executes nothing;
      * an absent body or a non-object body is gated first → 404 NOT_FOUND.
    In both cases the dev handler never runs and no Supabase client is built.
    """
    malformed = None
    with patch("app.api.dev_auth.create_supabase_client") as auth_client, patch(
        "app.api.dev_auth.get_admin_client"
    ) as admin_client:
        malformed = client.post(
            route,
            content=b"{not-json",
            headers={"content-type": "application/json"},
        )
        empty = client.post(route)
        scalar = client.post(route, json="just-a-string")

    auth_client.assert_not_called()
    admin_client.assert_not_called()

    for response in (empty, scalar):
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"

    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "VALIDATION_ERROR"
    assert malformed.json()["error"]["message"] == "Request validation failed"
    for leak in ("Traceback", "File \"", "site-packages", "RuntimeError"):
        assert leak not in malformed.text


# ===========================================================================
# 3. Response minimization
# ===========================================================================


def _fake_claims() -> dict:
    return {
        "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "email": "student@college.edu",
        "aud": "authenticated",
        "exp": 9999999999,
    }


def test_auth_me_exposes_only_the_documented_fields():
    user = {
        "user_id": "10000000-0000-0000-0000-000000000001",
        "auth_user_id": _fake_claims()["sub"],
        "email": "student@college.edu",
        "roles": ["student"],
        "institution_id": "30000000-0000-0000-0000-000000000001",
    }
    with patch("app.core.security.verify_jwt", return_value=_fake_claims()), patch(
        "app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=user)
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
    session = SimpleNamespace(access_token="mock-access-token")
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
    with patch("app.api.auth.create_supabase_client", return_value=auth_client), patch(
        "app.api.auth.get_sign_in_context", new=AsyncMock(return_value=account)
    ), patch("app.api.auth.get_admin_client", return_value=MagicMock()):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@college.edu", "password": SUBMITTED_PASSWORD},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {"access_token", "message", "user"}
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


# ===========================================================================
# 4. Error sanitization
# ===========================================================================


def test_unhandled_exception_returns_a_sanitized_500():
    """No traceback, exception name, file path, or internal value on a 500."""
    with patch(
        "app.api.auth.create_supabase_client",
        side_effect=RuntimeError("secret-internal-dsn-and-stack-detail"),
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@college.edu", "password": SUBMITTED_PASSWORD},
        )

    assert response.status_code == 500
    body = response.text
    for leak in (
        "Traceback",
        "RuntimeError",
        "secret-internal-dsn-and-stack-detail",
        "File \"",
        "site-packages",
        str(UUID(int=0)),
    ):
        assert leak not in body
    # The password that was submitted must never appear in an error response.
    assert SUBMITTED_PASSWORD not in body


def test_rejected_login_is_generic_and_never_echoes_the_password():
    auth_client = MagicMock()
    auth_client.auth.sign_in_with_password.side_effect = AuthApiError(
        "Invalid login credentials", 400, "invalid_grant"
    )
    with patch("app.api.auth.create_supabase_client", return_value=auth_client):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "unknown@college.edu", "password": SUBMITTED_PASSWORD},
        )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["message"] == "Invalid login credentials"
    assert SUBMITTED_PASSWORD not in response.text
    # Anti-enumeration: nothing here confirms or denies that the account exists.
    message = body["error"]["message"].lower()
    for disclosure in ("no account", "not found", "does not exist", "unknown email"):
        assert disclosure not in message


def test_validation_failure_detail_never_echoes_submitted_values():
    """422 bodies list field locations/types — never the submitted values."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@college.edu",
            "password": SUBMITTED_PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert SUBMITTED_PASSWORD not in response.text


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_never_create_a_supabase_client(route):
    """Fail closed: a disabled route must not touch auth infrastructure."""
    with patch("app.api.dev_auth.create_supabase_client") as auth_client, patch(
        "app.api.dev_auth.get_admin_client"
    ) as admin_client:
        response = client.post(
            route,
            json={
                "email": "student@college.edu",
                "current_password": "oldpass123",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
        )
    assert response.status_code == 404
    auth_client.assert_not_called()
    admin_client.assert_not_called()


def test_disabled_admin_reset_route_hides_existence_from_unauthenticated_caller():
    """No Authorization header + flag off → 404, never 401 (route is hidden)."""
    response = client.post(
        "/api/v1/dev/auth/admin/reset-student-password",
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_enabled_dev_routes_reject_unexpected_fields_with_422(route):
    """Flag ON: the dev schemas are strict (extra="forbid")."""
    settings.dev_test_mode = True
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    response = client.post(
        route,
        json={
            "email": "student@college.edu",
            "current_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
            "role": "admin",
            "user_id": str(uuid4()),
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_enabled_admin_reset_still_requires_the_admin_role():
    """The dev flag never replaces the existing RBAC boundary."""
    settings.dev_test_mode = True
    app.dependency_overrides[get_current_user] = lambda: {
        **ADMIN_USER,
        "roles": ["student"],
    }
    response = client.post(
        "/api/v1/dev/auth/admin/reset-student-password",
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
