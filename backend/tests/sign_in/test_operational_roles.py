"""Test operational roles."""

from __future__ import annotations

from app.core.errors import AppError

from supabase_auth.errors import AuthApiError

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import pytest

from .credentials import (
    login_api,
)

from .identity import (
    _active_institution_authorization,
    _as_authenticated,
    _auth_user,
)

from .support import (
    ADMIN_EMAIL,
    FACULTY_EMAIL,
    FAKE_CLAIMS,
    INSTITUTION_A,
    STAFF_EMAIL,
    client,
    institution_db,
    sign_in_account,
)


def test_13_faculty_login_succeeds_with_existing_email_identity():
    """Faculty sign in with the existing email + password identity model."""
    response = login_api(
        account=sign_in_account(status="active"),
        email=FACULTY_EMAIL,
        db=institution_db(),
    )
    assert response.status_code == 200, response.text


def test_unconfirmed_pending_faculty_gets_pending_message_not_invalid_credentials():
    """GoTrue's verified-password email-confirmation block remains actionable."""
    auth = MagicMock()
    auth.auth.sign_in_with_password.side_effect = AuthApiError(
        "Email not confirmed", 400, "email_not_confirmed"
    )
    pending = {
        "request_id": str(uuid4()),
        "requested_role": "faculty",
        "status": "pending",
    }
    with (
        patch(
            "app.repositories.platform.tenancy.get_user_by_email",
            return_value={"user_id": str(uuid4()), "email": FACULTY_EMAIL},
        ),
        patch(
            "app.repositories.platform.tenancy.get_pending_membership_request_for_user",
            return_value=pending,
        ),
    ):
        response = login_api(
            account=None,
            auth=auth,
            email=FACULTY_EMAIL,
            db=institution_db(),
        )

    assert response.status_code == 403
    assert response.json()["error"] == {
        "code": "REGISTRATION_PENDING",
        "message": (
            "Your faculty registration is pending. Contact your institution "
            "administrator to continue."
        ),
    }


def test_13b_pending_faculty_has_no_role_so_protected_access_denied():
    """Pending faculty hold NO role yet (Phase 6.13.5) -> 403 FORBIDDEN."""
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FACULTY_EMAIL,
    }
    verify, db = _as_authenticated(
        _auth_user(user, roles=(), institution_id=INSTITUTION_A)
    )
    with verify, db:
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_13c_approved_faculty_role_resolved_server_side():
    """Once approved, the 'faculty' role comes from trusted records only."""
    import asyncio

    from app.core.security import require_roles

    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": FACULTY_EMAIL,
        "roles": ["faculty"],
        "institution_id": str(INSTITUTION_A),
    }
    # Faculty passes the existing ingestion RBAC (admin/staff/faculty)...
    allowed = require_roles("admin", "staff", "faculty")
    assert asyncio.run(allowed(current_user=user)) is user
    # ...and is still denied the admin-only boundary (no escalation).
    denied = require_roles("admin")
    with pytest.raises(AppError) as exc:
        asyncio.run(denied(current_user=user))
    assert exc.value.status_code == 403
    assert exc.value.code == "FORBIDDEN"


def test_14_staff_login_succeeds_with_existing_email_identity():
    response = login_api(
        account=sign_in_account(status="active"),
        email=STAFF_EMAIL,
        db=institution_db(),
    )
    assert response.status_code == 200, response.text


def test_14b_pending_staff_has_no_role_so_protected_access_denied():
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": STAFF_EMAIL,
    }
    verify, db = _as_authenticated(
        _auth_user(user, roles=(), institution_id=INSTITUTION_A)
    )
    with verify, db:
        response = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert response.status_code == 403


def test_14c_approved_staff_role_resolved_server_side():
    """Staff role + institution scope come from trusted records, not the client."""
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": STAFF_EMAIL,
    }
    projection = _auth_user(user, roles=("staff",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with (
        verify,
        db,
        patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as listing,
    ):
        response = client.get(
            "/api/v1/admin/students/pending",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 200, response.text
    # The staff member's OWN institution was used as the tenant — never a
    # client-supplied value.
    assert UUID(str(listing.call_args.args[0])) == INSTITUTION_A


def test_15_admin_login_remains_compatible():
    """Existing admin authentication keeps working (Phase 5.4 / 6.6 intact)."""
    response = login_api(
        account=sign_in_account(status="active"),
        email=ADMIN_EMAIL,
        db=institution_db(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["user"]["email"] == ADMIN_EMAIL

    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": ADMIN_EMAIL,
    }
    verify, db = _as_authenticated(
        _auth_user(user, roles=("admin",), institution_id=INSTITUTION_A)
    )
    with verify, db:
        me = client.get(
            "/api/v1/admin/me", headers={"Authorization": "Bearer valid.token.here"}
        )
    assert me.status_code == 200, me.text
    assert me.json()["is_admin"] is True
    assert me.json()["roles"] == ["admin"]
