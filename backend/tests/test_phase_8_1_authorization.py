import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import faculty, institutions, organizations
from app.api.admin import _ADMIN_ROUTE_PERMISSIONS, router as admin_router
from app.api.platform import _PLATFORM_ROUTE_PERMISSIONS, router as platform_router
from app.core.errors import AppError
from app.core.permissions import DELEGABLE_STAFF_PERMISSIONS
from app.core.security import get_current_user
from app.db import supabase
from app.services import phase81_rbac
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
TENANT_A = "30000000-0000-0000-0000-000000000001"
TENANT_B = "30000000-0000-0000-0000-000000000002"
ACTOR = "10000000-0000-0000-0000-000000000001"
TARGET = "10000000-0000-0000-0000-000000000002"
SECTION = "20000000-0000-0000-0000-000000000001"


def _resolved_user(role: str, permission_codes: list[str], institution_id: str = TENANT_A) -> dict:
    return {
        "user_id": ACTOR,
        "auth_user_id": "auth-actor",
        "email": "actor@example.test",
        "roles": [role],
        "status": "active",
        "institution_id": institution_id,
        "role_assignments": [{
            "role": role,
            "scope_type": "institution",
            "scope_id": institution_id,
            "scope_organization_id": None,
            "is_active": True,
        }],
        "permissions_resolved": True,
        "effective_permissions": permission_codes,
    }


def test_all_admin_and_platform_methods_have_permission_policies() -> None:
    for router, policies, prefix in (
        (admin_router, _ADMIN_ROUTE_PERMISSIONS, "/admin"),
        (platform_router, _PLATFORM_ROUTE_PERMISSIONS, "/platform"),
    ):
        for route in router.routes:
            route_path = getattr(route, "path", "")
            if not route_path.startswith(prefix):
                continue
            normalized = route_path[route_path.rfind(prefix):]
            for method in route.methods - {"HEAD", "OPTIONS"}:
                assert (method, normalized) in policies


def test_organization_decision_permission_inventory_covers_protected_routes() -> None:
    routes = {
        (method, route.path)
        for route in organizations.router.routes
        for method in route.methods - {"HEAD", "OPTIONS"}
        if "/decision" in route.path
    }
    assert routes == set(organizations.ORGANIZATION_PERMISSION_POLICIES)


def test_institution_decision_permission_inventory_covers_protected_routes() -> None:
    routes = {
        (method, route.path)
        for route in institutions.router.routes
        for method in route.methods - {"HEAD", "OPTIONS"}
        if "/decision" in route.path
    }
    assert routes == set(institutions.INSTITUTION_PERMISSION_POLICIES)


@pytest.mark.parametrize(
    ("role", "grants", "scope", "expected"),
    [
        ("staff", [{"institution_id": TENANT_A, "permission": "attendance.manage"}], TENANT_A, ["attendance.manage"]),
        ("staff", [{"institution_id": TENANT_B, "permission": "attendance.manage"}], TENANT_A, []),
        ("admin", [{"institution_id": TENANT_A, "permission": "attendance.manage"}], TENANT_A, []),
    ],
)
def test_direct_staff_grants_require_matching_active_staff_institution_scope(
    role: str, grants: list[dict], scope: str, expected: list[str]
) -> None:
    user_record = {
        "user_id": ACTOR,
        "auth_user_id": "auth-actor",
        "email": "actor@example.test",
        "status": "active",
        "roles": [role],
        "institution_id": None,
        "student_institution_id": None,
        "role_assignments": [
            {
                "role": role,
                "scope_type": "institution",
                "scope_id": scope,
                "scope_organization_id": None,
                "is_active": True,
            }
        ],
        "effective_permissions": [],
        "direct_permission_grants": grants,
        "permissions_resolved": True,
    }
    with (
        patch("app.core.security.verify_jwt", return_value={"sub": "auth-actor"}),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(return_value=user_record),
        ),
    ):
        resolved = asyncio.run(get_current_user("Bearer token"))
    assert resolved["effective_permissions"] == expected


@pytest.mark.parametrize(
    ("scope_type", "expected_permissions"),
    [
        ("institution", ["faculty.assignments.manage"]),
        ("organization", ["organizations.manage"]),
        ("platform", ["faculty.assignments.manage", "organizations.manage"]),
    ],
)
def test_database_permission_projection_enforces_permission_scope(
    scope_type: str, expected_permissions: list[str]
) -> None:
    row = {
        "user_id": ACTOR,
        "auth_user_id": "auth-actor",
        "email": "actor@example.test",
        "status": "active",
        "user_roles": [{
            "scope_type": scope_type,
            "scope_id": TENANT_A,
            "scope_organization_id": TENANT_B if scope_type == "organization" else None,
            "roles": {
                "name": "admin",
                "is_active": True,
                "role_permissions": [
                    {"permissions": {
                        "code": "faculty.assignments.manage",
                        "scope": "institution",
                        "is_active": True,
                    }},
                    {"permissions": {
                        "code": "organizations.manage",
                        "scope": "organization",
                        "is_active": True,
                    }},
                ],
            },
        }],
        "user_permission_grants": [{
            "institution_id": TENANT_A,
            "revoked_at": None,
            "permissions": {"code": "attendance.manage", "is_active": True},
        }],
        "students": [],
    }

    class Query:
        def select(self, projection):
            self.projection = projection
            return self

        def eq(self, *_args):
            return self

        def maybe_single(self):
            return self

        def execute(self):
            return SimpleNamespace(data=row)

    query = Query()
    db = SimpleNamespace(table=lambda _name: query)
    with patch("app.db.supabase.get_admin_client", return_value=db):
        resolved = asyncio.run(
            supabase.get_user_by_auth_id("auth-actor", include_permissions=True)
        )
    assert resolved is not None
    assert resolved["effective_permissions"] == expected_permissions
    assert resolved["direct_permission_grants"] == [
        {"institution_id": TENANT_A, "permission": "attendance.manage"}
    ]
    assert (
        "user_permission_grants!user_permission_grants_user_id_fkey("
        in query.projection
    )


def test_staff_permission_api_rejects_non_delegable_permission_before_rpc() -> None:
    with pytest.raises(AppError) as error:
        phase81_rbac.change_staff_permissions(
            _resolved_user("admin", ["permissions.manage"]),
            UUID(TENANT_A),
            UUID(TARGET),
            ["platform.manage"],
            grant=True,
        )
    assert error.value.code == "PERMISSION_NOT_DELEGABLE"


def test_staff_permission_api_requires_staff_target_in_same_institution() -> None:
    with (
        patch(
            "app.services.phase81_rbac._staff_member",
            side_effect=AppError("Active Staff member not found", 404, "STAFF_MEMBER_NOT_FOUND"),
        ),
        patch("app.services.phase81_rbac.get_admin_client") as get_client,
    ):
        with pytest.raises(AppError) as error:
            phase81_rbac.change_staff_permissions(
                _resolved_user("admin", ["permissions.manage"]),
                UUID(TENANT_A),
                UUID(TARGET),
                ["attendance.manage"],
                grant=True,
            )
    assert error.value.code == "STAFF_MEMBER_NOT_FOUND"
    get_client.assert_not_called()


def test_staff_grant_mutation_uses_atomic_rpc_and_returns_effective_sources() -> None:
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = 1
    expected = {
        "user_id": TARGET,
        "institution_id": TENANT_A,
        "permissions": [],
        "delegable_permissions": ["attendance.manage"],
    }
    with (
        patch("app.services.phase81_rbac._staff_member", return_value={"id": TARGET}),
        patch("app.services.phase81_rbac.get_admin_client", return_value=db),
        patch("app.services.phase81_rbac.list_staff_permissions", return_value=expected),
    ):
        result = phase81_rbac.change_staff_permissions(
            _resolved_user("admin", ["permissions.manage"]),
            UUID(TENANT_A),
            UUID(TARGET),
            ["attendance.manage"],
            grant=True,
        )
    db.rpc.assert_called_once_with(
        "phase81_manage_staff_permission_grants",
        {
            "p_actor_user_id": ACTOR,
            "p_institution_id": TENANT_A,
            "p_target_user_id": TARGET,
            "p_permission_codes": ["attendance.manage"],
            "p_grant": True,
        },
    )
    assert result["changed"] == 1
    assert result["permissions"] == expected


def test_faculty_assignment_mutation_uses_atomic_rpc() -> None:
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = "assignment-id"
    with patch("app.services.phase81_rbac.get_admin_client", return_value=db):
        result = phase81_rbac.manage_faculty_assignment(
            _resolved_user("admin", ["faculty.assignments.manage"]),
            UUID(TENANT_A),
            UUID(TARGET),
            UUID(SECTION),
            revoke=False,
        )
    assert result == {"assignment_id": "assignment-id"}
    db.rpc.assert_called_once_with(
        "phase81_manage_faculty_section_assignment",
        {
            "p_actor_user_id": ACTOR,
            "p_institution_id": TENANT_A,
            "p_faculty_user_id": TARGET,
            "p_section_id": SECTION,
            "p_revoke": False,
        },
    )


def test_faculty_assignment_endpoint_denies_resolved_principal_without_permission() -> None:
    app.dependency_overrides[faculty._FACULTY] = lambda: _resolved_user("faculty", [])
    try:
        response = client.get("/api/v1/faculty/assignments")
    finally:
        app.dependency_overrides.pop(faculty._FACULTY, None)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_notification_read_permission_cannot_authorize_read_state_mutation() -> None:
    user = _resolved_user("student", ["notifications.own.read"])
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with (
            patch(
                "app.api.student_notifications.student_context_service.get_student_context",
                return_value={"student_id": TARGET},
            ),
            patch(
                "app.api.student_notifications.notifications_service.mark_own_notification_read"
            ) as mark_read,
        ):
            response = client.patch(
                "/api/v1/students/me/notifications/"
                "20000000-0000-0000-0000-000000000004/read"
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 403
    mark_read.assert_not_called()


def test_organization_decision_denies_platform_role_without_permission() -> None:
    user = _resolved_user("super_admin", [])
    user["institution_id"] = None
    user["role_assignments"] = [{
        "role": "super_admin",
        "scope_type": "platform",
        "scope_id": None,
        "scope_organization_id": None,
        "is_active": True,
    }]
    app.dependency_overrides[get_current_user] = lambda: user
    with (
        patch(
            "app.api.organizations.get_authorization_context_for_user",
            return_value=object(),
        ),
        patch("app.api.organizations.decide_organization") as decide,
    ):
        response = client.post(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000009/decision",
            json={"decision": "approve"},
        )
    app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 403
    decide.assert_not_called()


def test_institution_decision_requires_organization_scoped_permission() -> None:
    app.dependency_overrides[get_current_user] = lambda: _resolved_user("admin", [])
    try:
        with (
            patch(
                "app.api.institutions.get_authorization_context_for_user",
                return_value=object(),
            ),
            patch("app.api.institutions.decide_join_request") as decide,
        ):
            response = client.post(
                "/api/v1/institutions/join-requests/"
                "00000000-0000-0000-0000-000000000009/decision",
                json={"decision": "approve"},
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 403
    decide.assert_not_called()


def test_staff_permission_catalogue_is_narrow_and_never_platform_administrative() -> None:
    assert DELEGABLE_STAFF_PERMISSIONS
    assert not any(
        code.startswith(("platform.", "institutions.", "roles.", "permissions.", "users."))
        for code in DELEGABLE_STAFF_PERMISSIONS
    )


def test_phase_8_1_migration_has_rls_atomic_audit_and_scoped_constraints() -> None:
    from pathlib import Path

    migration = (
        Path(__file__).resolve().parents[2]
        / "supabase"
        / "migrations"
        / "20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql"
    ).read_text(encoding="utf-8")
    assert 'CREATE TABLE IF NOT EXISTS "public"."user_permission_grants"' in migration
    assert 'CREATE TABLE IF NOT EXISTS "public"."faculty_section_assignments"' in migration
    assert 'ENABLE ROW LEVEL SECURITY' in migration
    assert '"phase81_manage_staff_permission_grants"' in migration
    assert '"phase81_manage_faculty_section_assignment"' in migration
    assert '"phase81_assign_institution_role_audited"' in migration
    assert "'permission.grant'" in migration
    assert "'permission.revoke'" in migration
    assert "'faculty.assignment.assign'" in migration
    assert "'faculty.assignment.revoke'" in migration
    assert "phase81_admin_audit_append_only" in migration
