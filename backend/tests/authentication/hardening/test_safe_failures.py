"""Authentication hardening regressions: safe failures."""

from __future__ import annotations

from .support import (
    AuthApiError,
    MagicMock,
    SUBMITTED_PASSWORD,
    UUID,
    _dev_flag_off_and_no_overrides,
    client,
    patch,
)


# ===========================================================================
# 4. Error sanitization
# ===========================================================================


def test_unhandled_exception_returns_a_sanitized_500():
    """No traceback, exception name, file path, or internal value on a 500."""
    with patch(
        "app.api.auth.common.create_supabase_client",
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
    with patch("app.api.auth.common.create_supabase_client", return_value=auth_client):
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
