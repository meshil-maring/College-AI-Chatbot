import hashlib
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.config import settings
from app.core.security import get_current_user
from app.main import app
from app.services.auth_security import (
    consume_password_recovery_session,
    reset_auth_abuse_state,
)

client = TestClient(app, raise_server_exceptions=False)
AUTH_USER_ID = "71000000-0000-0000-0000-000000000001"
APP_USER_ID = "72000000-0000-0000-0000-000000000001"
ACCESS_TOKEN = "test-access-token"
CURRENT_USER = {
    "user_id": APP_USER_ID,
    "auth_user_id": AUTH_USER_ID,
    "email": "person@college.edu",
    "roles": ["student"],
    "status": "active",
}


@pytest.fixture(autouse=True)
def clean_auth_test_state():
    previous_enabled = settings.auth_rate_limit_enabled
    previous_login_limit = settings.auth_login_ip_limit_requests
    settings.auth_rate_limit_enabled = True
    settings.auth_login_ip_limit_requests = 30
    reset_auth_abuse_state()
    app.dependency_overrides.pop(get_current_user, None)
    yield
    reset_auth_abuse_state()
    settings.auth_rate_limit_enabled = previous_enabled
    settings.auth_login_ip_limit_requests = previous_login_limit
    app.dependency_overrides.pop(get_current_user, None)


def _authenticated():
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def _recovery_authenticated(
    *,
    issued_at: int | None = None,
    session_id: str = "provider-recovery-session",
):
    issued_at = int(time.time()) if issued_at is None else issued_at
    app.dependency_overrides[get_current_user] = lambda: CURRENT_USER | {
        "auth_methods": [{"method": "recovery", "timestamp": issued_at}],
        "auth_session_id": session_id,
        "token_issued_at": issued_at,
    }
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}


def _session():
    return SimpleNamespace(
        access_token="new-access-token",
        refresh_token="new-refresh-token",
        expires_in=3600,
    )


def test_recovery_session_consumer_hashes_provider_session_id():
    admin = MagicMock()
    admin.rpc.return_value.execute.return_value.data = True
    with patch("app.services.auth_security.get_admin_client", return_value=admin):
        consumed = consume_password_recovery_session(
            session_id="provider-recovery-session",
            auth_user_id=AUTH_USER_ID,
            expires_at=1_800_000_000,
        )

    assert consumed is True
    name, params = admin.rpc.call_args.args
    assert name == "consume_auth_password_recovery_session"
    assert params["p_session_fingerprint"] == hashlib.sha256(
        b"provider-recovery-session"
    ).hexdigest()
    assert params["p_auth_user_id"] == AUTH_USER_ID
    assert params["p_expires_at"].startswith("2027-")


def test_forgot_password_uses_provider_and_returns_generic_response():
    provider = MagicMock()
    with (
        patch("app.api.auth.create_supabase_client", return_value=provider),
        patch("app.api.auth.record_auth_security_event") as audit,
    ):
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "unknown@college.edu"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "message": "If an account exists, password recovery instructions have been sent."
    }
    provider.auth.reset_password_for_email.assert_called_once_with(
        "unknown@college.edu",
        {"redirect_to": settings.effective_auth_recovery_redirect_url},
    )
    audit.assert_called_once()


def test_password_recovery_rejects_extra_fields_and_invalid_email():
    for payload in (
        {"email": "not-an-email"},
        {"email": "person@college.edu", "new_password": "attacker-chosen"},
    ):
        response = client.post("/api/v1/auth/forgot-password", json=payload)
        assert response.status_code == 422


def test_change_password_verifies_current_password_and_revokes_other_sessions():
    provider = MagicMock()
    provider.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id=AUTH_USER_ID)
    )
    admin = MagicMock()
    with (
        patch("app.api.auth.create_supabase_client", return_value=provider),
        patch("app.api.auth.get_admin_client", return_value=admin),
        patch("app.api.auth.record_auth_security_event") as audit,
    ):
        response = client.post(
            "/api/v1/auth/change-password",
            headers=_authenticated(),
            json={
                "current_password": "current-password",
                "new_password": "a-different-password",
                "confirm_password": "a-different-password",
            },
        )

    assert response.status_code == 200, response.text
    provider.auth.sign_in_with_password.assert_called_once_with(
        {"email": CURRENT_USER["email"], "password": "current-password"}
    )
    admin.auth.admin.update_user_by_id.assert_called_once_with(
        AUTH_USER_ID,
        {"password": "a-different-password"},
    )
    provider.auth.admin.sign_out.assert_called_once_with(ACCESS_TOKEN, scope="others")
    audit.assert_called_once()
    assert "a-different-password" not in response.text


def test_change_password_normalizes_wrong_current_password():
    provider = MagicMock()
    provider.auth.sign_in_with_password.side_effect = AuthApiError(
        "bad credentials", 400, "invalid_grant"
    )
    with (
        patch("app.api.auth.create_supabase_client", return_value=provider),
        patch("app.api.auth.record_auth_security_event"),
    ):
        response = client.post(
            "/api/v1/auth/change-password",
            headers=_authenticated(),
            json={
                "current_password": "wrong-password",
                "new_password": "a-different-password",
                "confirm_password": "a-different-password",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PASSWORD_VERIFICATION_FAILED"
    assert "bad credentials" not in response.text


def test_password_change_rejects_reused_and_short_passwords():
    _authenticated()
    for payload in (
        {
            "current_password": "same-password",
            "new_password": "same-password",
            "confirm_password": "same-password",
        },
        {
            "current_password": "current-password",
            "new_password": "short",
            "confirm_password": "short",
        },
    ):
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json=payload,
        )
        assert response.status_code == 422


def test_reset_completion_revokes_all_provider_sessions_without_touching_roles():
    provider = MagicMock()
    admin = MagicMock()
    recovery_issued_at = int(time.time())
    with (
        patch("app.api.auth.create_supabase_client", return_value=provider),
        patch("app.api.auth.get_admin_client", return_value=admin),
        patch("app.api.auth.consume_password_recovery_session", return_value=True) as consume,
        patch("app.api.auth.record_auth_security_event") as audit,
    ):
        response = client.post(
            "/api/v1/auth/reset-password",
            headers=_recovery_authenticated(issued_at=recovery_issued_at),
            json={
                "new_password": "new-recovery-password",
                "confirm_password": "new-recovery-password",
            },
        )

    assert response.status_code == 200, response.text
    consume.assert_called_once_with(
        session_id="provider-recovery-session",
        auth_user_id=AUTH_USER_ID,
        expires_at=recovery_issued_at + 900,
    )
    admin.auth.admin.update_user_by_id.assert_called_once_with(
        AUTH_USER_ID,
        {"password": "new-recovery-password"},
    )
    provider.auth.admin.sign_out.assert_called_once_with(ACCESS_TOKEN, scope="global")
    audit.assert_called_once()


def test_reset_completion_rejects_regular_authenticated_sessions():
    admin = MagicMock()
    with (
        patch("app.api.auth.get_admin_client", return_value=admin),
        patch("app.api.auth.consume_password_recovery_session") as consume,
        patch("app.api.auth.record_auth_security_event"),
    ):
        response = client.post(
            "/api/v1/auth/reset-password",
            headers=_authenticated(),
            json={
                "new_password": "new-recovery-password",
                "confirm_password": "new-recovery-password",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PASSWORD_RECOVERY_SESSION_INVALID"
    consume.assert_not_called()
    admin.auth.admin.update_user_by_id.assert_not_called()


def test_reset_completion_rejects_replayed_recovery_sessions():
    admin = MagicMock()
    with (
        patch("app.api.auth.get_admin_client", return_value=admin),
        patch("app.api.auth.consume_password_recovery_session", return_value=False),
        patch("app.api.auth.record_auth_security_event") as audit,
    ):
        response = client.post(
            "/api/v1/auth/reset-password",
            headers=_recovery_authenticated(),
            json={
                "new_password": "new-recovery-password",
                "confirm_password": "new-recovery-password",
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PASSWORD_RECOVERY_SESSION_INVALID"
    admin.auth.admin.update_user_by_id.assert_not_called()
    audit.assert_called_once()


def test_reset_completion_rejects_stale_recovery_sessions():
    admin = MagicMock()
    with (
        patch("app.api.auth.get_admin_client", return_value=admin),
        patch("app.api.auth.consume_password_recovery_session") as consume,
        patch("app.api.auth.record_auth_security_event"),
    ):
        response = client.post(
            "/api/v1/auth/reset-password",
            headers=_recovery_authenticated(issued_at=int(time.time()) - 901),
            json={
                "new_password": "new-recovery-password",
                "confirm_password": "new-recovery-password",
            },
        )

    assert response.status_code == 400
    consume.assert_not_called()
    admin.auth.admin.update_user_by_id.assert_not_called()


def test_refresh_uses_provider_refresh_token_and_revalidates_server_identity():
    provider = MagicMock()
    provider.auth.refresh_session.return_value = SimpleNamespace(
        session=_session(),
        user=SimpleNamespace(id=AUTH_USER_ID, email=CURRENT_USER["email"]),
    )
    account = {
        "user_id": APP_USER_ID,
        "status": "active",
        "institution_id": None,
        "approval_status": None,
        "student_is_active": None,
    }
    with (
        patch("app.api.auth.create_supabase_client", return_value=provider),
        patch("app.api.auth.get_sign_in_context", new=AsyncMock(return_value=account)),
        patch("app.api.auth.get_admin_client", return_value=MagicMock()),
        patch("app.api.auth.record_auth_security_event"),
    ):
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "provider-refresh-token"},
        )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"] == "new-access-token"
    assert response.json()["refresh_token"] == "new-refresh-token"
    assert response.json()["expires_in"] == 3600
    provider.auth.refresh_session.assert_called_once_with("provider-refresh-token")


@pytest.mark.parametrize(
    ("path", "scope", "event"),
    [
        ("/api/v1/auth/logout", "local", "logout"),
        ("/api/v1/auth/logout-all", "global", "logout_all"),
    ],
)
def test_logout_endpoints_use_provider_revocation_scope(path, scope, event):
    provider = MagicMock()
    with (
        patch("app.api.auth.create_supabase_client", return_value=provider),
        patch("app.api.auth.record_auth_security_event") as audit,
    ):
        response = client.post(path, headers=_authenticated())

    assert response.status_code == 200
    provider.auth.admin.sign_out.assert_called_once_with(ACCESS_TOKEN, scope=scope)
    assert audit.call_args.kwargs["event"] == event


def test_login_attempts_are_rate_limited_by_direct_peer_ip():
    settings.auth_login_ip_limit_requests = 1
    provider = MagicMock()
    provider.auth.sign_in_with_password.side_effect = AuthApiError(
        "bad credentials", 400, "invalid_grant"
    )
    with (
        patch("app.api.auth.create_supabase_client", return_value=provider),
        patch("app.api.auth.record_auth_security_event"),
    ):
        first = client.post(
            "/api/v1/auth/login",
            json={"email": "person@college.edu", "password": "current-password"},
        )
        second = client.post(
            "/api/v1/auth/login",
            json={"email": "person@college.edu", "password": "current-password"},
        )

    assert first.status_code == 400
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "AUTH_RATE_LIMITED"
    assert int(second.headers["retry-after"]) > 0
    assert provider.auth.sign_in_with_password.call_count == 1
