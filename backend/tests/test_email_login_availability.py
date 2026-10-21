"""Email login must distinguish dependency outages from rejected credentials."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthRetryableError

from app.main import app


@pytest.fixture
def login_dependencies():
    provider = MagicMock()
    provider.auth.sign_in_with_password.return_value = SimpleNamespace(
        user=SimpleNamespace(id="test-auth-user", email="admin@college.edu"),
        session=SimpleNamespace(
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_in=3600,
        ),
    )
    context = AsyncMock(return_value={
        "user_id": "test-app-user", "status": "active", "institution_id": None,
    })
    with (
        patch("app.api.auth.common.enforce_auth_rate_limit"),
        patch("app.api.auth.common.create_supabase_client", return_value=provider),
        patch("app.api.auth.common.get_admin_client"),
        patch("app.api.auth.common.get_sign_in_context", context),
        patch("app.repositories.platform.tenancy.get_pending_membership_request_for_user", return_value=None) as membership,
        patch("app.api.auth.common.record_auth_security_event") as audit,
    ):
        yield SimpleNamespace(provider=provider, context=context, membership=membership, audit=audit)


@pytest.mark.parametrize("boundary", ["provider", "context", "membership"])
@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
def test_email_login_connection_outage_returns_safe_retryable_error(
    login_dependencies, boundary, error_type, caplog,
):
    dependency = getattr(login_dependencies, boundary)
    if boundary == "provider":
        dependency = dependency.auth.sign_in_with_password
    dependency.side_effect = error_type("private hostname, password, and provider diagnostics")

    response = TestClient(app).post("/api/v1/auth/login", json={
        "email": "admin@college.edu", "password": "test-password",
    })

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert response.json() == {"error": {
        "code": "AUTH_SERVICE_UNAVAILABLE",
        "message": "Authentication is temporarily unavailable. Please try again shortly.",
    }}
    login_dependencies.audit.assert_not_called()
    assert "private hostname" not in caplog.text


def test_retryable_auth_provider_failure_is_not_invalid_credentials(login_dependencies):
    login_dependencies.provider.auth.sign_in_with_password.side_effect = AuthRetryableError(
        "private upstream error", 503,
    )
    response = TestClient(app).post("/api/v1/auth/login", json={
        "email": "admin@college.edu", "password": "test-password",
    })
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_SERVICE_UNAVAILABLE"
    login_dependencies.context.assert_not_awaited()


def test_email_login_recovers_after_database_connection_is_restored(login_dependencies):
    login_dependencies.membership.side_effect = [httpx.ConnectError("offline"), None]
    payload = {"email": "admin@college.edu", "password": "test-password"}
    client = TestClient(app)

    assert client.post("/api/v1/auth/login", json=payload).status_code == 503
    response = client.post("/api/v1/auth/login", json=payload)

    assert response.status_code == 200
    assert response.json()["access_token"] == "test-access-token"
    login_dependencies.audit.assert_called_once()
