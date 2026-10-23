"""Test compatibility."""

from __future__ import annotations

from .support import STAFF_EMAIL, ORGANIZATION_ID

from app.services.auth.student_auth import SafeAuthFailure

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

from .credentials import (
    auth_client,
    login_api,
    student_login_api,
)

from .identity import (
    _active_institution_authorization,
    _as_authenticated,
    _auth_user,
)

from .support import (
    ADMIN_EMAIL,
    APPROVED_EMAIL,
    APPROVED_REGISTER,
    APPROVED_ROLL,
    FAKE_CLAIMS,
    INSTITUTION_A,
    INSTITUTION_CODE,
    client,
    student_account,
    student_row,
)


def test_24a_phase_6_email_login_response_shape_unchanged():
    response = login_api(account=student_account())
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "access_token",
        "refresh_token",
        "expires_in",
        "message",
        "user",
    }
    assert body["message"] == "Login successful."
    assert set(body["user"]) == {"id", "email"}


def test_24b_phase_6_email_login_wrong_password_contract_unchanged():
    response = login_api(account=student_account(), auth=auth_client(success=False))
    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["message"] == "Invalid login credentials"


def test_24c_phase_6_5_student_login_failure_contract_unchanged():
    response = student_login_api(
        student=student_row(),
        identifier=APPROVED_EMAIL,
        auth=auth_client(success=False),
    )
    assert response.status_code == 401, response.text
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["error"]["message"] == "Invalid identifier or password"


def test_24d_phase_6_5_student_login_success_contract_unchanged():
    for identifier, extra in (
        (APPROVED_EMAIL, {}),
        (APPROVED_REGISTER, {"institution_code": INSTITUTION_CODE}),
        (APPROVED_ROLL, {"institution_code": INSTITUTION_CODE}),
    ):
        response = student_login_api(
            student=student_row(), identifier=identifier, **extra
        )
        assert response.status_code == 200, f"{identifier}: {response.text}"
        body = response.json()
        assert set(body) == {
            "access_token",
            "refresh_token",
            "expires_in",
            "message",
            "user",
        }
        assert body["access_token"] == "mock-access-token"
        assert set(body["user"]) == {"id", "email"}


def test_24e_safe_auth_failure_shape_unchanged():
    exc = SafeAuthFailure()
    assert exc.status_code == 401
    assert exc.code == "INVALID_CREDENTIALS"
    assert exc.message == "Invalid identifier or password"


def test_24f_get_current_user_contract_unchanged():
    """No credentials -> 401 AUTH_REQUIRED (existing dependency untouched)."""
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"

    bad_scheme = client.get("/api/v1/admin/me", headers={"Authorization": "Basic abc"})
    assert bad_scheme.status_code == 401
    assert bad_scheme.json()["error"]["code"] == "INVALID_SCHEME"


def test_24g_get_current_user_still_requires_an_application_user():
    """A valid JWT with no public.users row -> 404 USER_NOT_FOUND (unchanged)."""
    with (
        patch("app.core.security.tokens.verify_jwt", return_value=FAKE_CLAIMS),
        patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=None)),
    ):
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


def test_24h_get_current_user_projections_still_drive_rbac():
    """roles + institution_id still come from get_user_by_auth_id."""
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": ADMIN_EMAIL,
    }
    projection = _auth_user(user, roles=("admin",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db:
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 200, response.text
    assert response.json()["roles"] == ["admin"]
    assert response.json()["is_admin"] is True


def test_20d_legacy_unscoped_tenant_row_is_not_widened_to_platform():
    """A pre-6.13 tenant-bound role row keeps institution scope (no escalation)."""
    from app.services.auth.authorization import (
        INSTITUTION,
        resolve_authorization_context,
    )

    rows = [
        {
            "role_id": uuid4(),
            "role_name": "staff",
            "is_active": True,
            "scope_type": None,
            "scope_id": None,
            "scope_organization_id": None,
        }
    ]
    user = {
        "user_id": uuid4(),
        "email": STAFF_EMAIL,
        "institution_id": str(INSTITUTION_A),
    }
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.repositories.platform.tenancy.get_user_role_scope_rows",
            return_value=rows,
        ),
        patch(
            "app.repositories.platform.tenancy.get_institution_organization",
            return_value=ORGANIZATION_ID,
        ),
    ):
        context = resolve_authorization_context(user)

    assert context["scope_type"] == INSTITUTION
    assert context["scope_id"] == str(INSTITUTION_A)
