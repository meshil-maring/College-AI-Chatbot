from unittest.mock import MagicMock, patch

import pytest
from fastapi.routing import iter_route_contexts

from app.core.permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    DELEGABLE_STAFF_PERMISSIONS,
    PERMISSIONS,
)
from app.services.auth import phase81_rbac


def test_retired_permission_families_are_absent_from_account_policy():
    retired = (
        "departments.",
        "courses.",
        "subjects.",
        "semesters.",
        "academic_years.",
        "attendance.",
        "results.",
        "faculty.assignments.",
        "academic.",
    )
    assert not any(code.startswith(retired) for code in PERMISSIONS)
    assert not any(code.startswith(retired) for code in DELEGABLE_STAFF_PERMISSIONS)
    assert "students.approve" in DEFAULT_ROLE_PERMISSIONS["admin"]
    assert "faculty.update" in DEFAULT_ROLE_PERMISSIONS["admin"]
    assert "staff.update" in DEFAULT_ROLE_PERMISSIONS["admin"]
    assert "ai.chat" in DEFAULT_ROLE_PERMISSIONS["student"]


def test_retired_routes_are_unregistered_and_nonacademic_routes_remain():
    from app.main import app

    paths = set(app.openapi()["paths"])
    forbidden = (
        "/api/v1/admin/academic-setup",
        "/api/v1/academic-packages",
        "/api/v1/faculty",
        "/api/v1/admin/student-workspace",
        "/api/v1/admin/faculty-assignments",
        "/api/v1/admin/faculty-responsibilities",
        "/api/v1/admin/attendance",
        "/api/v1/admin/results",
        "/api/v1/admin/test-results",
        "/api/v1/students/me/academic-profile",
        "/api/v1/students/me/attendance",
        "/api/v1/students/me/results",
        "/api/v1/students/me/test-results",
        "/api/v1/students/me/assessments",
        "/api/v1/students/me/performance",
        "/api/v1/students/me/timeline",
    )
    assert not any(path.startswith(forbidden) for path in paths)
    assert not any("faculty-responsibilities" in path for path in paths)
    assert {
        "/api/v1/auth/me",
        "/api/v1/auth/student/login",
        "/api/v1/registration",
        "/api/v1/students/me/profile",
        "/api/v1/students/me/notices",
        "/api/v1/students/me/resources",
        "/api/v1/students/me/notifications",
        "/api/v1/admin/students/pending",
        "/api/v1/admin/students/{student_id}/approve",
        "/api/v1/admin/memberships",
        "/api/v1/admin/notices",
    }.issubset(paths)


def test_remaining_admin_and_platform_routes_still_have_explicit_permission_policies():
    from app.api.admin.admin import router as admin
    from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
    from app.api.platform.platform import router as platform
    from app.api.platform.dependencies import _PLATFORM_ROUTE_PERMISSIONS

    for router, policies, prefix in (
        (admin, _ADMIN_ROUTE_PERMISSIONS, "/admin"),
        (platform, _PLATFORM_ROUTE_PERMISSIONS, "/platform"),
    ):
        for route in iter_route_contexts(router.routes):
            if not route.path:
                continue
            for method in (route.methods or set()) - {"HEAD", "OPTIONS"}:
                assert (method, route.path) in policies, (method, route.path)


@pytest.mark.parametrize(
    "code", ["attendance.manage", "academic.package.assign", "results.manage"]
)
def test_staff_cannot_delegate_removed_permissions(code):
    with (
        patch.object(phase81_rbac, "get_admin_client") as database,
        pytest.raises(Exception) as error,
    ):
        phase81_rbac.change_staff_permissions({}, "tenant", "user", [code], grant=True)
    assert error.value.code == "PERMISSION_NOT_DELEGABLE"
    database.assert_not_called()
