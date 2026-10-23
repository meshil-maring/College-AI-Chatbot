"""Identity."""

from __future__ import annotations

from app.services.auth.auth_security import reset_auth_abuse_state

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .support import (
    ACCOUNT_PASSWORD,
    APPROVED_EMAIL,
    FAKE_CLAIMS,
    INSTITUTION_A,
    LOGIN_URL,
)


def _auth_user(user: dict, roles: tuple[str, ...], institution_id=None) -> dict:
    """The ``get_user_by_auth_id`` projection for a non-student account.

    Phase 7.20: the projection also carries the account lifecycle and the
    server-owned ``user_roles`` grants. Institution scope for a non-student role
    comes ONLY from that grant; a tenant-less account holds a platform grant.
    """
    scope_id = str(institution_id) if institution_id else None
    permissions = {
        "admin": ["profile.own.read", "students.read"],
        "staff": ["students.read", "students.approve"],
        "student": ["profile.own.read"],
    }
    return {
        "user_id": str(user["user_id"]),
        "auth_user_id": user["auth_user_id"],
        "email": user["email"],
        "status": "active",
        "roles": list(roles),
        "institution_id": scope_id,
        "role_assignments": [
            {
                "role": role,
                "scope_type": "institution" if scope_id else "platform",
                "scope_id": scope_id,
                "scope_organization_id": None,
                "is_active": True,
                "permissions": permissions.get(role, []),
            }
            for role in roles
        ],
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
        "direct_permission_grants": [],
    }


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    """Provide an ACTIVE institution to the scoped admin dependency only.

    ``require_institution_roles`` verifies institution lifecycle through the
    authorization module's service-role client; only that client is stubbed so
    the sign-in and tenant-resolution tests keep resolving their own rows.
    """
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={
            "institution_id": str(INSTITUTION_A),
            "status": "active",
            "is_active": True,
        }
    )
    reset_auth_abuse_state()
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=db),
        patch("app.api.auth.common.record_auth_security_event"),
        patch("app.api.auth.student_auth.record_auth_security_event"),
    ):
        yield
    reset_auth_abuse_state()


def _as_authenticated(fake_user: dict):
    """Patch JWT verification + public.users resolution (existing Phase 6)."""
    return (
        patch("app.core.security.tokens.verify_jwt", return_value=FAKE_CLAIMS),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(return_value=fake_user),
        ),
    )


def _login_payload(url: str) -> dict:
    if url == LOGIN_URL:
        return {"email": APPROVED_EMAIL, "password": ACCOUNT_PASSWORD}
    return {"identifier": APPROVED_EMAIL, "password": ACCOUNT_PASSWORD}
