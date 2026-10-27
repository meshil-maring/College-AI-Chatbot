"""Authentication hardening regressions: dev routes."""

from __future__ import annotations

from .support import (
    ADMIN_USER,
    DEV_ROUTES,
    _dev_flag_off_and_no_overrides,
    app,
    client,
    get_current_user,
    patch,
    pytest,
    settings,
    uuid4,
)


# ===========================================================================
# 2. Dev route gating — 404 for every shape, before auth and before Supabase
# ===========================================================================


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_return_404_for_a_valid_body(route):
    response = client.post(
        route,
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_return_404_for_unexpected_fields(route):
    """An extra field must NOT turn the hidden route into a 422 disclosure."""
    response = client.post(
        route,
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
            "role": "admin",
            "user_id": str(uuid4()),
            "approval_status": "approved",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_handle_malformed_bodies_without_side_effects(route):
    """Route existence is never turned into a handler/DB disclosure.

    Verified behaviour (FastAPI ordering):
      * a body that cannot be DECODED is rejected by the framework's parser
        before any dependency runs, for every body route in the API — it
        returns the standardized 422 envelope and executes nothing;
      * an absent body or a non-object body is gated first → 404 NOT_FOUND.
    In both cases the dev handler never runs and no Supabase client is built.
    """
    malformed = None
    with patch("app.api.auth.dev_auth.create_supabase_client") as auth_client, patch(
        "app.api.auth.dev_auth.get_admin_client"
    ) as admin_client:
        malformed = client.post(
            route,
            content=b"{not-json",
            headers={"content-type": "application/json"},
        )
        empty = client.post(route)
        scalar = client.post(route, json="just-a-string")

    auth_client.assert_not_called()
    admin_client.assert_not_called()

    for response in (empty, scalar):
        assert response.status_code == 404, response.text
        assert response.json()["error"]["code"] == "NOT_FOUND"

    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "VALIDATION_ERROR"
    assert malformed.json()["error"]["message"] == "Request validation failed"
    for leak in ("Traceback", "File \"", "site-packages", "RuntimeError"):
        assert leak not in malformed.text


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_disabled_dev_routes_never_create_a_supabase_client(route):
    """Fail closed: a disabled route must not touch auth infrastructure."""
    with patch("app.api.auth.dev_auth.create_supabase_client") as auth_client, patch(
        "app.api.auth.dev_auth.get_admin_client"
    ) as admin_client:
        response = client.post(
            route,
            json={
                "email": "student@college.edu",
                "current_password": "oldpass123",
                "new_password": "newpass123",
                "confirm_password": "newpass123",
            },
        )
    assert response.status_code == 404
    auth_client.assert_not_called()
    admin_client.assert_not_called()


def test_disabled_admin_reset_route_hides_existence_from_unauthenticated_caller():
    """No Authorization header + flag off → 404, never 401 (route is hidden)."""
    response = client.post(
        "/api/v1/dev/auth/admin/reset-student-password",
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("route", DEV_ROUTES)
def test_enabled_dev_routes_reject_unexpected_fields_with_422(route):
    """Flag ON: the dev schemas are strict (extra="forbid")."""
    settings.dev_test_mode = True
    app.dependency_overrides[get_current_user] = lambda: ADMIN_USER
    response = client.post(
        route,
        json={
            "email": "student@college.edu",
            "current_password": "oldpass123",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
            "role": "admin",
            "user_id": str(uuid4()),
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_enabled_admin_reset_still_requires_the_admin_role():
    """The dev flag never replaces the existing RBAC boundary."""
    settings.dev_test_mode = True
    app.dependency_overrides[get_current_user] = lambda: {
        **ADMIN_USER,
        "roles": ["student"],
    }
    response = client.post(
        "/api/v1/dev/auth/admin/reset-student-password",
        json={
            "email": "student@college.edu",
            "new_password": "newpass123",
            "confirm_password": "newpass123",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
