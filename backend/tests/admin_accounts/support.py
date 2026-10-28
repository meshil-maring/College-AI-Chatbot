"""Shared authorization principals and test doubles."""

from contextlib import ExitStack, contextmanager

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

from fastapi.testclient import TestClient

from app.core.security import SUPPORTED_ROLES, resolve_primary_role

from app.main import app

from tests.dashboard_contract import build_dashboard
from tests.auth_fixtures.principals import resolved_principal

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"

INSTITUTION_B = "30000000-0000-0000-0000-000000000002"

USER_ID = "30000000-0000-0000-0000-000000000301"

STUDENT_A = "30000000-0000-0000-0000-000000000101"

STUDENT_B = "30000000-0000-0000-0000-000000000102"

ADMIN_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "admin@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}


def _assignment(role: str) -> dict:
    return {
        "role": role,
        "scope_type": "institution",
        "scope_id": INSTITUTION_A,
        "scope_organization_id": None,
        "is_active": True,
    }


ADMIN_USER = resolved_principal({
    "user_id": USER_ID,
    "auth_user_id": ADMIN_CLAIMS["sub"],
    "email": ADMIN_CLAIMS["email"],
    "status": "active",
    "roles": ["admin"],
    "institution_id": INSTITUTION_A,
    "role_assignments": [_assignment("admin")],
})

NON_ADMIN_USERS = {
    "student": {
        "user_id": USER_ID,
        "auth_user_id": ADMIN_CLAIMS["sub"],
        "email": "student@college.edu",
        "status": "active",
        "roles": ["student"],
        "institution_id": INSTITUTION_A,
        "role_assignments": [_assignment("student")],
    },
    "faculty": {
        "user_id": USER_ID,
        "auth_user_id": ADMIN_CLAIMS["sub"],
        "email": "faculty@college.edu",
        "status": "active",
        "roles": ["faculty"],
        "institution_id": INSTITUTION_A,
        "role_assignments": [_assignment("faculty")],
    },
    "staff": {
        "user_id": USER_ID,
        "auth_user_id": ADMIN_CLAIMS["sub"],
        "email": "staff@college.edu",
        "status": "active",
        "roles": ["staff"],
        "institution_id": INSTITUTION_A,
        "role_assignments": [_assignment("staff")],
    },
}

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}

PENDING_STUDENT_ROW = {
    "student_id": STUDENT_A,
    "user_id": "u-1",
    "institution_id": INSTITUTION_A,
    "student_number": "STU-0001",
    "email": "student@college.edu",
    "register_number": "REG-001",
    "university_roll_number": None,
    "approval_status": "pending",
    "status": "active",
    "is_active": True,
    "enrollment_date": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@contextmanager
def _patch_admin_auth(user=ADMIN_USER):
    """Authenticate every request as the admin principal."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.tokens.verify_jwt", return_value=ADMIN_CLAIMS)
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=user),
            )
        )
        stack.enter_context(
            patch(
                "app.services.auth.authorization.get_admin_client",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(
            patch("app.services.auth.identity.get_admin_client", return_value=MagicMock())
        )
        stack.enter_context(
            patch(
                "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
                return_value={
                    "institution_id": INSTITUTION_A,
                    "code": "ALPHA",
                    "status": "active",
                    "is_active": True,
                },
            )
        )
        yield


@contextmanager
def _patch_role_auth(role: str):
    """Authenticate every request as a non-admin principal."""
    user = resolved_principal(NON_ADMIN_USERS[role])
    claims = dict(ADMIN_CLAIMS, email=user["email"])
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.tokens.verify_jwt", return_value=claims)
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=user),
            )
        )
        stack.enter_context(
            patch(
                "app.services.auth.authorization.get_admin_client",
                return_value=MagicMock(),
            )
        )
        stack.enter_context(
            patch(
                "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
                return_value={
                    "institution_id": INSTITUTION_A,
                    "status": "active",
                    "is_active": True,
                },
            )
        )
        yield
