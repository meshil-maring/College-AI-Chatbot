from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.admin import _ADMIN_ROUTE_PERMISSIONS, router as admin_router
from app.api.platform import _PLATFORM_ROUTE_PERMISSIONS, router as platform_router
from app.core.errors import AppError
from app.core.permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    PERMISSIONS,
    permission_matches,
)
from app.core.security import (
    authorize_permissions,
    get_current_user,
    has_permission,
    require_permission,
)
from app.db.supabase import get_user_by_auth_id
from app.main import app


def test_permission_catalog_has_safe_role_defaults() -> None:
    assert set(DEFAULT_ROLE_PERMISSIONS["student"]).isdisjoint(
        {"users.delete", "roles.manage", "permissions.manage", "platform.manage"}
    )
    assert "platform.manage" in DEFAULT_ROLE_PERMISSIONS["super_admin"]
    assert "attendance.manage" not in DEFAULT_ROLE_PERMISSIONS["super_admin"]
    assert set().union(*DEFAULT_ROLE_PERMISSIONS.values()).issubset(set(PERMISSIONS))


def test_permission_matching_supports_only_resource_wildcards() -> None:
    assert permission_matches({"students.read"}, "students.read")
    assert permission_matches({"students.*"}, "students.read")
    assert permission_matches({"*"}, "results.manage")
    assert not permission_matches({"students.read"}, "students.delete")
    assert not permission_matches({"student.*"}, "students.read")


def test_resolved_empty_database_grants_never_fall_back_to_role_defaults() -> None:
    user = {
        "roles": ["admin"],
        "permissions_resolved": True,
        "effective_permissions": [],
    }

    assert not has_permission(user, "students.read")


@pytest.mark.asyncio
async def test_permission_dependency_denies_ungranted_permission() -> None:
    dependency = require_permission("students.read")
    user = {
        "user_id": "test-user",
        "roles": ["student"],
        "permissions_resolved": True,
        "effective_permissions": ["profile.own.read"],
    }

    with pytest.raises(AppError) as error:
        await dependency(current_user=user)

    assert error.value.status_code == 403
    assert error.value.code == "FORBIDDEN"


def test_authorize_permissions_requires_every_permission() -> None:
    user = {
        "roles": ["admin"],
        "permissions_resolved": True,
        "effective_permissions": ["students.read"],
    }

    with pytest.raises(AppError) as error:
        authorize_permissions(user, "students.read", "users.read")

    assert error.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_database_projection_resolves_only_active_role_permissions() -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "user_id": "user-1",
        "auth_user_id": "auth-1",
        "email": "student@example.test",
        "status": "active",
        "user_roles": [
            {
                "scope_type": "institution",
                "scope_id": "institution-1",
                "scope_organization_id": None,
                "roles": {
                    "name": "student",
                    "is_active": True,
                    "role_permissions": [
                        {
                            "permissions": {
                                "code": "results.own.read",
                                "is_active": True,
                            }
                        },
                        {
                            "permissions": {
                                "code": "platform.manage",
                                "is_active": False,
                            }
                        },
                    ],
                },
            },
            {
                "scope_type": "institution",
                "scope_id": "institution-1",
                "scope_organization_id": None,
                "roles": {
                    "name": "inactive-role",
                    "is_active": False,
                    "role_permissions": [
                        {
                            "permissions": {
                                "code": "users.delete",
                                "is_active": True,
                            }
                        }
                    ],
                },
            },
        ],
        "students": {"institution_id": "institution-1"},
    }

    with patch("app.db.supabase.get_admin_client", return_value=client):
        user = await get_user_by_auth_id("auth-1", include_permissions=True)

    assert user is not None
    assert user["effective_permissions"] == ["results.own.read"]
    assert user["permissions_resolved"] is True


def test_admin_api_denies_resolved_user_without_required_permission() -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "test-user",
        "auth_user_id": "auth-user",
        "email": "admin@example.test",
        "roles": ["admin"],
        "status": "active",
        "institution_id": "institution-1",
        "role_assignments": [],
        "permissions_resolved": True,
        "effective_permissions": [],
    }
    try:
        response = TestClient(app).get("/api/v1/admin/students")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_auth_me_exposes_effective_permissions_from_authenticated_context() -> None:
    effective_permissions = ["ai.chat", "results.own.read"]
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": "test-user",
        "auth_user_id": "auth-user",
        "email": "student@example.test",
        "roles": ["student"],
        "institution_id": "institution-1",
        "effective_permissions": effective_permissions,
    }
    try:
        response = TestClient(app).get("/api/v1/auth/me")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["effective_permissions"] == effective_permissions


@pytest.mark.parametrize(
    ("router", "policies", "marker"),
    [
        (admin_router, _ADMIN_ROUTE_PERMISSIONS, "/admin"),
        (platform_router, _PLATFORM_ROUTE_PERMISSIONS, "/platform"),
    ],
)
def test_every_admin_and_platform_route_has_an_explicit_permission_policy(
    router,
    policies: dict[tuple[str, str], tuple[str, ...]],
    marker: str,
) -> None:
    protected_routes = [
        route
        for route in router.routes
        if getattr(route, "path", "").startswith(marker)
    ]
    assert protected_routes
    for route in protected_routes:
        normalized_path = route.path[route.path.rfind(marker):]
        for method in route.methods - {"HEAD", "OPTIONS"}:
            assert (method, normalized_path) in policies
