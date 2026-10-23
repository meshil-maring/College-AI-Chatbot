"""Test scope input."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

from .identity import (
    _active_institution_authorization,
    _as_authenticated,
    _auth_user,
    _login_payload,
)

from .support import (
    ADMIN_EMAIL,
    FAKE_CLAIMS,
    INSTITUTION_A,
    INSTITUTION_B,
    LOGIN_URL,
    ORGANIZATION_ID,
    STUDENT_LOGIN_URL,
    client,
)


def test_17_institution_scope_cannot_be_overridden():
    for field in ("institution_id", "scope_type", "scope_id"):
        for url in (LOGIN_URL, STUDENT_LOGIN_URL):
            payload = _login_payload(url)
            payload[field] = str(INSTITUTION_B) if field != "scope_type" else "platform"
            response = client.post(url, json=payload)
            assert response.status_code == 422, f"{url} {field}: {response.text}"


def test_17b_tenant_bound_admin_cannot_request_foreign_institution():
    """Tenant scope is enforced by the locked Phase 6 scope_tenant guard."""
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": ADMIN_EMAIL,
    }
    projection = _auth_user(user, roles=("admin",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with verify, db:
        response = client.get(
            f"/api/v1/admin/students/pending?institution_id={INSTITUTION_B}",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_17c_tenant_bound_admin_own_institution_is_scoped_not_substituted():
    """Same institution -> allowed, and the effective tenant is the caller's."""
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": ADMIN_EMAIL,
    }
    projection = _auth_user(user, roles=("admin",), institution_id=INSTITUTION_A)
    verify, db = _as_authenticated(projection)
    with (
        verify,
        db,
        patch(
            "app.services.admin.admin_academics.list_pending_approvals", return_value=[]
        ) as listing,
    ):
        response = client.get(
            f"/api/v1/admin/students/pending?institution_id={INSTITUTION_A}",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 200, response.text
    assert UUID(str(listing.call_args.args[0])) == INSTITUTION_A


def test_18_organization_scope_cannot_be_overridden():
    for field in ("organization_id", "organization", "scope_organization_id"):
        for url in (LOGIN_URL, STUDENT_LOGIN_URL):
            payload = _login_payload(url)
            payload[field] = str(ORGANIZATION_ID)
            response = client.post(url, json=payload)
            assert response.status_code == 422, f"{url} {field}: {response.text}"


def test_18b_organization_scope_comes_from_user_roles_only():
    """Client-declared scope fields are ignored; user_roles is authoritative."""
    from app.services.auth.authorization import (
        INSTITUTION,
        resolve_authorization_context,
    )

    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": ADMIN_EMAIL,
        "institution_id": str(INSTITUTION_A),
        # Deliberately client-ish injected values that MUST be ignored.
        "roles": ["admin"],
        "scope_type": "platform",
        "scope_id": str(ORGANIZATION_ID),
        "organization_id": str(ORGANIZATION_ID),
    }
    rows = [
        {
            "role_id": uuid4(),
            "role_name": "admin",
            "is_active": True,
            "scope_type": INSTITUTION,
            "scope_id": str(INSTITUTION_A),
            "scope_organization_id": str(ORGANIZATION_ID),
        }
    ]
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

    # The stored institution scope wins over the client-declared platform scope.
    assert context["scope_type"] == INSTITUTION
    assert UUID(context["scope_id"]) == INSTITUTION_A
    assert UUID(context["institution_id"]) == INSTITUTION_A
    assert UUID(context["organization_id"]) == ORGANIZATION_ID
    assert context["roles"] == ["admin"]
