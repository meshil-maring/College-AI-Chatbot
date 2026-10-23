"""Support."""

from __future__ import annotations

from app.api.admin.dependencies import _ADMIN

from app.api.admin.dependencies import _APPROVAL

from app.core.security import get_current_user

from app.main import app

from contextlib import contextmanager

from pathlib import Path

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .principals import (
    DEACTIVATED_FACULTY_USER,
    DEACTIVATED_STAFF_USER,
    KNOWLEDGE_SOURCE_B,
    _grant,
)


@contextmanager
def _as(principal: dict, *, institution_active: bool = True):
    """Authenticate as ``principal`` with a controlled institution lifecycle row."""
    app.dependency_overrides[get_current_user] = lambda: principal
    scope_ids = [
        grant["scope_id"]
        for grant in principal.get("role_assignments", [])
        if grant.get("scope_id")
    ]
    institution = {
        "institution_id": str(scope_ids[0] if scope_ids else None),
        "status": "active" if institution_active else "suspended",
        "is_active": institution_active,
    }
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            return_value=institution,
        ),
        patch(
            "app.db.supabase.get_super_admin_authorization",
            new=AsyncMock(
                return_value={"status": "active", "has_platform_grant": True}
            ),
        ),
    ):
        yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_dependencies():
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)
    yield
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)


def _error_code(response) -> str | None:
    """Read the stable AppError code out of a failure response."""
    body = response.json()
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return body["error"].get("code")
    return None


ADMIN_ONLY_ROUTES = [
    ("GET", "/api/v1/admin/me"),
    ("GET", "/api/v1/admin/dashboard"),
    ("GET", "/api/v1/admin/memberships"),
    ("GET", "/api/v1/admin/memberships/requests"),
    ("GET", "/api/v1/admin/faqs"),
    ("GET", "/api/v1/admin/notices"),
    ("GET", "/api/v1/admin/audit-logs"),
]


def _source_row(institution_id: str) -> dict:
    return {"knowledge_source_id": KNOWLEDGE_SOURCE_B, "institution_id": institution_id}


def _tenantless_principal(role: str) -> dict:
    """A role principal holding a PLATFORM grant with no institution scope."""
    uid = f"72800000-0000-0000-0000-0000000000{len(role):02d}"
    return {
        "user_id": uid,
        "auth_user_id": uid,
        "email": f"{role}@example.edu",
        "status": "active",
        "roles": [role],
        "institution_id": None,
        "role_assignments": [_grant(role, None)],
    }


DEACTIVATED_USERS = [
    (DEACTIVATED_STAFF_USER, "staff"),
    (DEACTIVATED_FACULTY_USER, "faculty"),
]


SUPER_ADMIN_MUST_NOT_REACH = [
    ("GET", "/api/v1/admin/students/pending"),
    ("GET", "/api/v1/admin/dashboard"),
    ("GET", "/api/v1/admin/memberships"),
    ("GET", "/api/v1/admin/students/pending"),
]


def _route_paths() -> set[str]:
    """Every registered path, including those on included sub-routers."""
    return {
        route.path
        for route in app.routes
        if isinstance(getattr(route, "path", None), str)
    }


_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"


def _migration_sql() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(_MIGRATIONS.glob("*.sql"))
    )
