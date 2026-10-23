"""Shared authorization principals and test doubles."""

from __future__ import annotations

from contextlib import contextmanager

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

import pytest

from fastapi.testclient import TestClient

from app.api.admin.dependencies import _ADMIN

from app.api.admin.dependencies import _APPROVAL

from app.core.security import get_current_user

from app.main import app

from tests.dashboard_contract import build_dashboard

client = TestClient(app, raise_server_exceptions=False)

INST_A = "71000000-0000-0000-0000-00000000000a"

INST_B = "71000000-0000-0000-0000-00000000000b"

ADMIN_A = "72000000-0000-0000-0000-00000000000a"

ADMIN_B = "72000000-0000-0000-0000-00000000000b"

STUDENT_A = "73000000-0000-0000-0000-00000000000a"

FACULTY_A = "73100000-0000-0000-0000-00000000000a"

STAFF_A = "73200000-0000-0000-0000-00000000000a"

SUPER_ADMIN = "73400000-0000-0000-0000-00000000000a"

AUTH_HEADERS = {"Authorization": "Bearer phase721.token"}

DASHBOARD_A = build_dashboard(
    name="Alpha University",
    code="ALPHA",
    total_students=11,
    pending_approvals=2,
    approved=9,
    active_students=8,
    sources_total=5,
    sources_active=4,
    documents_total=13,
    active_faqs=6,
    active_notices=3,
)

DASHBOARD_B = build_dashboard(
    name="Beta Institute",
    code="BETA",
    total_students=77,
    pending_approvals=9,
    approved=68,
    active_students=55,
    sources_total=21,
    sources_active=17,
    documents_total=88,
    active_faqs=31,
    active_notices=19,
)

DASHBOARD_BY_INSTITUTION = {
    INST_A: DASHBOARD_A,
    INST_B: DASHBOARD_B,
}


def _grant(
    role: str, institution_id: str | None, scope_type: str = "institution"
) -> dict:
    return {
        "role": role,
        "scope_type": scope_type,
        "scope_id": institution_id,
        "scope_organization_id": None,
        "is_active": True,
    }


def _principal(
    user_id: str,
    role: str,
    institution_id: str | None,
    *,
    status: str = "active",
    scope_type: str = "institution",
) -> dict:
    assignments = (
        [_grant(role, institution_id, scope_type)] if institution_id is not None else []
    )
    return {
        "user_id": user_id,
        "auth_user_id": user_id,
        "email": f"{role}@example.edu",
        "status": status,
        "roles": [role],
        # Deliberately None: the dependency must use role_assignments.scope_id.
        "institution_id": None,
        "role_assignments": assignments,
    }


ADMIN_A_USER = _principal(ADMIN_A, "admin", INST_A)

ADMIN_B_USER = _principal(ADMIN_B, "admin", INST_B)

STUDENT_USER = _principal(STUDENT_A, "student", INST_A)

FACULTY_USER = _principal(FACULTY_A, "faculty", INST_A)

STAFF_USER = _principal(STAFF_A, "staff", INST_A)

SUPER_ADMIN_USER = _principal(SUPER_ADMIN, "super_admin", None, scope_type="platform")

PLATFORM_SCOPED_ADMIN = _principal(ADMIN_A, "admin", INST_A, scope_type="platform")

TENANTLESS_ADMIN = _principal(ADMIN_A, "admin", None)

INACTIVE_ADMIN = _principal(ADMIN_A, "admin", INST_A, status="inactive")


@contextmanager
def _authenticated(
    principal: dict,
    *,
    institution_active: bool = True,
    dashboard_response=None,
):
    """Run as ``principal``, with the dashboard service replaced by a mock.

    Only the data layer is stubbed. The Phase 7.20 dependency
    (``require_institution_roles``) and its lifecycle verification run for
    real, so these tests exercise the production authorization guard.
    """
    app.dependency_overrides[get_current_user] = lambda: principal
    grants = principal.get("role_assignments") or []
    institution = (
        {"status": "active", "is_active": True}
        if institution_active and grants
        else {"status": "suspended", "is_active": False}
    )

    def _tenant_scoped_dashboard(*, institution_id, **_kwargs):
        """Return the fixture belonging to the tenant the API layer resolved."""
        return DASHBOARD_BY_INSTITUTION.get(
            str(institution_id), build_dashboard(name="Unknown", code="UNK")
        )

    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            return_value=institution,
        ),
        patch(
            "app.services.admin.admin_dashboard.get_admin_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.services.admin.admin_dashboard.knowledge_repo.list_notices",
            return_value=[],
        ),
        patch(
            "app.services.admin.admin_dashboard.get_dashboard_summary",
            side_effect=dashboard_response or _tenant_scoped_dashboard,
        ) as service,
    ):
        yield service
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_dependencies():
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)
    yield
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)


EXPECTED_TOP_LEVEL = {
    "institution",
    "students",
    "knowledge",
    "communication",
    "quick_actions",
}

FORBIDDEN_KEYS = {
    "institution_id",
    "organization_id",
    "user_id",
    "auth_user_id",
    "actor_user_id",
    "audit_id",
    "notice_id",
    "faq_id",
    "student_id",
    "record_id",
    "record_data",
    "ip_address",
    "user_agent",
    "scope_type",
    "scope_id",
    "roles",
    "role_assignments",
    "service_role",
    "service_role_key",
    "password",
    "token",
    "api_key",
    "authorization_context",
    "counts",
    "recent_audit",
}


def _walk_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _walk_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_keys(item)


def _dashboard_routes() -> list:
    """Inspect the feature router; the public prefix is checked in OpenAPI."""
    from app.api.admin.overview import router

    return [route for route in router.routes if route.path.endswith("/dashboard")]
