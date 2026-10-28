"""Shared authorization principals and test doubles."""

from contextlib import ExitStack, contextmanager

from types import SimpleNamespace

from unittest.mock import ANY, AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

import pytest

from fastapi.testclient import TestClient

from app.core.security import SUPPORTED_ROLES, resolve_primary_role

from app.main import app
from tests.auth_fixtures.principals import resolved_principal

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"

INSTITUTION_B = "30000000-0000-0000-0000-000000000002"

USER_ID = "30000000-0000-0000-0000-000000000701"

STUDENT_A = "30000000-0000-0000-0000-000000000101"

STUDENT_B = "30000000-0000-0000-0000-000000000102"

RESULT_B = "30000000-0000-0000-0000-000000000202"

ATTENDANCE_B = "30000000-0000-0000-0000-000000000303"

KNOWLEDGE_SOURCE_B = "30000000-0000-0000-0000-000000000404"

NOTICE_B = "30000000-0000-0000-0000-000000000505"

FAQ_B = "30000000-0000-0000-0000-000000000606"

AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}

CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "principal@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}


def _user(role: str | None, institution_id: str | None = INSTITUTION_A) -> dict:
    """One authenticated principal for a server-resolved role.

    Phase 7.20: institution scope is carried by the server-owned ``user_roles``
    grant (``role_assignments``); a tenant-less account holds a platform grant.
    """
    roles = [] if role is None else [role]
    return resolved_principal({
        "user_id": USER_ID,
        "auth_user_id": CLAIMS["sub"],
        "email": f"{role or 'unsupported'}@college.edu",
        "roles": roles,
        "status": "active",
        "institution_id": institution_id,
        "role_assignments": [
            {
                "role": role,
                "scope_type": "institution" if institution_id else "platform",
                "scope_id": institution_id,
                "scope_organization_id": None,
                "is_active": True,
            }
            for role in roles
        ],
    })


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    """Provide an ACTIVE institution to the scoped admin dependency only."""
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={
            "institution_id": INSTITUTION_A,
            "status": "active",
            "is_active": True,
        }
    )
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=db),
        patch("app.services.auth.identity.get_admin_client", return_value=db),
    ):
        yield


USERS = {
    "admin": _user("admin"),
    "staff": _user("staff"),
    "faculty": _user("faculty"),
    "student": _user("student"),
    # A platform-level account (no students profile -> no tenant).
    "platform_admin": _user("admin", None),
    # Privileged role without a tenant: approval authority must stay closed.
    "tenantless_staff": _user("staff", None),
    "tenantless_faculty": _user("faculty", None),
    # Authenticated account with no supported role.
    "unsupported": _user(None),
}

ALL_FOUR_ROLES = ("student", "faculty", "staff", "admin")

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
def _auth(role: str, user: dict | None = None):
    """Authenticate every request as one server-resolved principal.

    ``user`` overrides the fixture for that role, which lets a test move the
    SAME role between tenants (Institution A -> Institution B) without changing
    anything else about the principal.
    """
    principal = user if user is not None else USERS[role]
    claims = dict(CLAIMS, email=principal["email"])
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.tokens.verify_jwt", return_value=claims)
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=principal),
            )
        )
        yield


def _assert_forbidden(role: str, method: str, path: str, **kwargs) -> None:
    """A privileged surface must answer 403 FORBIDDEN for this role."""
    with _auth(role):
        response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, (
        f"{role} {method} {path}: {response.status_code}"
    )
    assert response.json()["error"]["code"] == "FORBIDDEN"


def _assert_tenant_mismatch(role: str, method: str, path: str, **kwargs) -> None:
    """A cross-tenant request must answer 403 TENANT_MISMATCH."""
    with _auth(role):
        response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, (
        f"{role} {method} {path}: {response.status_code}"
    )
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


ADMIN_ONLY_REQUESTS: tuple[tuple[str, str, dict], ...] = (
    ("GET", "/api/v1/admin/me", {}),
    ("GET", "/api/v1/admin/dashboard", {}),
    ("GET", "/api/v1/admin/notices", {}),
    ("POST", "/api/v1/admin/notices", {"json": {"institution_id": INSTITUTION_A}}),
    ("PATCH", f"/api/v1/admin/notices/{NOTICE_B}", {"json": {}}),
    ("DELETE", f"/api/v1/admin/notices/{NOTICE_B}", {}),
    ("GET", "/api/v1/admin/faqs", {}),
    ("POST", "/api/v1/admin/faqs", {"json": {"institution_id": INSTITUTION_A}}),
    ("PATCH", f"/api/v1/admin/faqs/{FAQ_B}", {"json": {}}),
    ("DELETE", f"/api/v1/admin/faqs/{FAQ_B}", {}),
    (
        "GET",
        "/api/v1/admin/knowledge-sources",
        {"params": {"institution_id": INSTITUTION_A}},
    ),
    (
        "POST",
        "/api/v1/admin/knowledge-sources",
        {"json": {"institution_id": INSTITUTION_A}},
    ),
    (
        "GET",
        f"/api/v1/admin/knowledge-sources/{KNOWLEDGE_SOURCE_B}",
        {},
    ),
    ("GET", f"/api/v1/admin/documents/{RESULT_B}", {}),
    (
        "POST",
        "/api/v1/admin/documents",
        {
            "files": {"file": ("a.txt", b"x", "text/plain")},
            "data": {"knowledge_source_id": KNOWLEDGE_SOURCE_B},
        },
    ),
    (
        "POST",
        f"/api/v1/admin/documents/{RESULT_B}/versions",
        {"files": {"file": ("a.txt", b"x", "text/plain")}},
    ),
    ("DELETE", f"/api/v1/admin/documents/{RESULT_B}", {}),
    ("GET", "/api/v1/admin/audit-logs", {}),
)
