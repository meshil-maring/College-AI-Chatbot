from .support import (
    TARGET,
    _ADMIN_ROUTE_PERMISSIONS,
    _PLATFORM_ROUTE_PERMISSIONS,
    _resolved_user,
    admin_router,
    app,
    client,
    get_current_user,
    institutions,
    iter_route_contexts,
    organizations,
    patch,
    platform_router,
)


def test_all_admin_and_platform_methods_have_permission_policies() -> None:
    for router, policies, prefix in (
        (admin_router, _ADMIN_ROUTE_PERMISSIONS, "/admin"),
        (platform_router, _PLATFORM_ROUTE_PERMISSIONS, "/platform"),
    ):
        for route in iter_route_contexts(router.routes):
            if not route.path or not route.path.startswith(prefix):
                continue
            normalized = route.path[route.path.rfind(prefix) :]
            for method in (route.methods or set()) - {"HEAD", "OPTIONS"}:
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


def test_notification_read_permission_cannot_authorize_read_state_mutation() -> None:
    user = _resolved_user("student", ["notifications.own.read"])
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with (
            patch(
                "app.api.students.student_notifications.student_context_service.get_student_context",
                return_value={"student_id": TARGET},
            ),
            patch(
                "app.api.students.student_notifications.notifications_service.mark_own_notification_read"
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
    user["role_assignments"] = [
        {
            "role": "super_admin",
            "scope_type": "platform",
            "scope_id": None,
            "scope_organization_id": None,
            "is_active": True,
        }
    ]
    app.dependency_overrides[get_current_user] = lambda: user
    with (
        patch(
            "app.api.platform.organizations.get_authorization_context_for_user",
            return_value=object(),
        ),
        patch("app.api.platform.organizations.decide_organization") as decide,
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
                "app.api.platform.institutions.get_authorization_context_for_user",
                return_value=object(),
            ),
            patch("app.api.platform.institutions.decide_join_request") as decide,
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
