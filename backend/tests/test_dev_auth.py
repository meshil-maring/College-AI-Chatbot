"""DEVELOPMENT / TESTING ONLY — tests for the dev-only password recovery API.

Covers:
  * feature disabled by default (dev_test_mode=False) → 404 for every route
  * forgot-password validation (email format, password length, confirm match)
  * forgot-password success and anti-enumeration parity for an unknown email
  * change-password success and invalid-current-password failure
  * change-password unauthorized is impossible to bypass (feature flag first)
  * admin reset-student-password requires admin role + dev flag
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.core.security import get_current_user
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

ADMIN_USER = {
    "user_id": "80000000-0000-0000-0000-000000000001",
    "auth_user_id": "80000000-0000-0000-0000-0000000000aa",
    "email": "admin@example.com",
    "roles": ["admin"],
}
STUDENT_USER = {
    "user_id": "80000000-0000-0000-0000-000000000002",
    "auth_user_id": "80000000-0000-0000-0000-0000000000bb",
    "email": "student@example.com",
    "roles": ["student"],
}


@pytest.fixture(autouse=True)
def _reset_dev_flag_and_auth_overrides():
    """Every test starts with the dev flag OFF and no auth override."""
    original = settings.dev_test_mode
    settings.dev_test_mode = False
    app.dependency_overrides.pop(get_current_user, None)
    yield
    settings.dev_test_mode = original
    app.dependency_overrides.pop(get_current_user, None)


def _enable_dev_mode():
    settings.dev_test_mode = True


def _fake_user(uid: str, email: str):
    user = MagicMock()
    user.id = uid
    user.email = email
    return user


# ---------------------------------------------------------------------------
# DEV flag disabled behavior — every endpoint must 404 when flag is off.
# ---------------------------------------------------------------------------


def test_forgot_password_disabled_by_default():
    response = client.post(
        "/api/v1/dev/auth/forgot-password",
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_change_password_disabled_by_default():
    response = client.post(
        "/api/v1/dev/auth/change-password",
        json={
            "email": "student@college.edu",
            "current_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_admin_reset_disabled_by_default_even_for_admin():
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
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


def test_dev_auth_status_reports_disabled_by_default():
    response = client.get("/api/v1/dev/auth/status")
    assert response.status_code == 200
    assert response.json() == {"dev_test_mode": False}


def test_dev_auth_status_reports_enabled_when_flag_set():
    _enable_dev_mode()
    response = client.get("/api/v1/dev/auth/status")
    assert response.status_code == 200
    assert response.json() == {"dev_test_mode": True}


# ---------------------------------------------------------------------------
# Forgot-password validation (dev flag enabled)
# ---------------------------------------------------------------------------


def test_forgot_password_rejects_invalid_email():
    _enable_dev_mode()
    response = client.post(
        "/api/v1/dev/auth/forgot-password",
        json={
            "email": "not-an-email",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 422


def test_forgot_password_rejects_short_password():
    _enable_dev_mode()
    response = client.post(
        "/api/v1/dev/auth/forgot-password",
        json={
            "email": "student@college.edu",
            "new_password": "abc",
            "confirm_password": "abc",
        },
    )
    assert response.status_code == 422


def test_forgot_password_rejects_mismatched_confirmation():
    _enable_dev_mode()
    response = client.post(
        "/api/v1/dev/auth/forgot-password",
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "different123",
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Forgot-password success / failure (dev flag enabled)
# ---------------------------------------------------------------------------


def test_forgot_password_success():
    _enable_dev_mode()
    admin_client = MagicMock()
    admin_client.auth.admin.list_users.return_value = [
        _fake_user("uid-1", "student@college.edu")
    ]
    with patch("app.api.dev_auth.get_admin_client", return_value=admin_client):
        response = client.post(
            "/api/v1/dev/auth/forgot-password",
            json={
                "email": "student@college.edu",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
        )
    assert response.status_code == 200
    # Phase 6.15.6 — the response is the generic anti-enumeration message.
    assert "If an account exists for this email" in response.json()["message"]
    admin_client.auth.admin.update_user_by_id.assert_called_once_with(
        "uid-1", {"password": "newpass123"}
    )


def test_forgot_password_does_not_reveal_account_existence():
    """Phase 6.15.6 — anti-enumeration contract.

    An unknown email must be INDISTINGUISHABLE from a successful reset: same
    HTTP status, same generic message, no password change, and no wording that
    confirms or denies that the account exists.
    """
    _enable_dev_mode()
    body = {
        "email": "student@college.edu",
        "new_password": "newpass123",
        "confirm_password": "newpass123",
    }

    # Known email → password is updated.
    known_client = MagicMock()
    known_client.auth.admin.list_users.return_value = [
        _fake_user("uid-1", "student@college.edu")
    ]
    with patch("app.api.dev_auth.get_admin_client", return_value=known_client):
        known = client.post("/api/v1/dev/auth/forgot-password", json=body)

    # Unknown email → generic response, nothing updated.
    unknown_client = MagicMock()
    unknown_client.auth.admin.list_users.return_value = []
    with patch("app.api.dev_auth.get_admin_client", return_value=unknown_client):
        unknown = client.post(
            "/api/v1/dev/auth/forgot-password",
            json={**body, "email": "nobody@college.edu"},
        )

    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()
    unknown_client.auth.admin.update_user_by_id.assert_not_called()
    known_client.auth.admin.update_user_by_id.assert_called_once_with(
        "uid-1", {"password": "newpass123"}
    )
    message = unknown.json()["message"].lower()
    assert "no account" not in message
    assert "not found" not in message
    assert "does not exist" not in message


# ---------------------------------------------------------------------------
# Change-password (dev flag enabled)
# ---------------------------------------------------------------------------


def test_change_password_success():
    _enable_dev_mode()
    auth_client = MagicMock()
    admin_client = MagicMock()
    admin_client.auth.admin.list_users.return_value = [
        _fake_user("uid-2", "student@college.edu")
    ]
    with patch("app.api.dev_auth.create_supabase_client", return_value=auth_client), patch(
        "app.api.dev_auth.get_admin_client", return_value=admin_client
    ):
        response = client.post(
            "/api/v1/dev/auth/change-password",
            json={
                "email": "student@college.edu",
                "current_password": "oldpass123",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
        )
    assert response.status_code == 200
    auth_client.auth.sign_in_with_password.assert_called_once_with(
        {"email": "student@college.edu", "password": "oldpass123"}
    )
    admin_client.auth.admin.update_user_by_id.assert_called_once_with(
        "uid-2", {"password": "newpass123"}
    )


def test_change_password_rejects_wrong_current_password():
    _enable_dev_mode()
    auth_client = MagicMock()
    auth_client.auth.sign_in_with_password.side_effect = AuthApiError(
        "Invalid login credentials", 400, "invalid_grant"
    )
    with patch("app.api.dev_auth.create_supabase_client", return_value=auth_client):
        response = client.post(
            "/api/v1/dev/auth/change-password",
            json={
                "email": "student@college.edu",
                "current_password": "wrongpass",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# Admin reset-student-password (dev flag enabled) — requires admin role.
# ---------------------------------------------------------------------------


def test_admin_reset_requires_authentication():
    _enable_dev_mode()
    response = client.post(
        "/api/v1/dev/auth/admin/reset-student-password",
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_admin_reset_forbidden_for_non_admin():
    _enable_dev_mode()
    app.dependency_overrides[get_current_user] = lambda: STUDENT_USER
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


def test_admin_reset_success_for_admin():
    _enable_dev_mode()
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    admin_client = MagicMock()
    admin_client.auth.admin.list_users.return_value = [
        _fake_user("uid-3", "student@college.edu")
    ]
    with patch("app.api.dev_auth.get_admin_client", return_value=admin_client):
        response = client.post(
            "/api/v1/dev/auth/admin/reset-student-password",
            json={
                "email": "student@college.edu",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
        )
    assert response.status_code == 200
    admin_client.auth.admin.update_user_by_id.assert_called_once_with(
        "uid-3", {"password": "newpass123"}
    )
