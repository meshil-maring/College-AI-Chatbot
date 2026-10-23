from .support import (
    AUTH_HEADERS,
    AsyncMock,
    FACULTY_USER,
    MagicMock,
    PLATFORM_SCOPED_ADMIN,
    STAFF_USER,
    STUDENT_USER,
    SUPER_ADMIN_USER,
    _ADMIN,
    _authenticated,
    _clean_dependencies,
    app,
    client,
    get_current_user,
    patch,
    pytest,
)


def test_platform_scoped_admin_is_denied() -> None:
    """A platform `admin` role row is NOT a University Admin grant.

    The role matches, so Phase 7.20 raises FORBIDDEN (the role exists but its
    scope is insufficient) rather than SCOPE_MISSING. Either way it is 403 and
    the dashboard is unreachable — platform authority is not inherited.
    """
    with _authenticated(PLATFORM_SCOPED_ADMIN):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] in (
        "FORBIDDEN",
        "SCOPE_MISSING",
        "SCOPE_INCONSISTENT",
    )


@pytest.mark.parametrize(
    ("principal", "label"),
    [
        (STUDENT_USER, "student"),
        (STAFF_USER, "staff"),
        (FACULTY_USER, "faculty"),
    ],
)
def test_non_admin_roles_cannot_access_the_admin_dashboard(principal, label) -> None:
    """§15 — student/staff/faculty are not defined as dashboard consumers.

    Staff keeps its Phase 6.4/6.18 approval-queue exception only; it gains no
    dashboard access from this phase.
    """
    with _authenticated(principal):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403, label
    assert response.json()["error"]["code"] in ("FORBIDDEN", "SCOPE_MISSING")


def test_super_admin_does_not_inherit_university_admin_dashboard() -> None:
    """§15 — platform authority is a separate surface, never inherited."""
    with _authenticated(SUPER_ADMIN_USER):
        response = client.get("/api/v1/admin/dashboard", headers=AUTH_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] in ("FORBIDDEN", "SCOPE_MISSING")


def test_super_admin_platform_surface_is_unchanged() -> None:
    """The dashboard work must not disturb the separate Super Admin surface."""
    db = MagicMock()
    db.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])
    app.dependency_overrides[get_current_user] = lambda: SUPER_ADMIN_USER
    with (
        patch(
            "app.db.supabase.get_super_admin_authorization",
            new=AsyncMock(
                return_value={"status": "active", "has_platform_grant": True}
            ),
        ),
        patch(
            "app.services.platform.platform_institutions.get_admin_client",
            return_value=db,
        ),
    ):
        response = client.get("/api/v1/platform/institutions", headers=AUTH_HEADERS)
    app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 200
    assert response.json() == {"institutions": []}


def test_unauthenticated_dashboard_request_is_rejected() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(_ADMIN, None)
    response = client.get("/api/v1/admin/dashboard")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
