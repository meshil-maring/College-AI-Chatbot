"""Test membership."""

from __future__ import annotations

import pytest

from .principals import (
    ADMIN_A_USER,
    AUTH_HEADERS,
    STAFF_A,
    STAFF_AND_FACULTY_USERS,
    client,
)

from .support import (
    _as,
    _clean_dependencies,
    _error_code,
    _route_paths,
)


def test_no_generic_role_editing_interface_exists() -> None:
    """There is deliberately no generic `PATCH /users/{id}` role interface."""
    paths = _route_paths()
    assert "/api/v1/users/{user_id}" not in paths
    assert "/api/v1/users/{user_id}/role" not in paths
    assert "/api/v1/admin/roles" not in paths


@pytest.mark.parametrize(
    "field", ["institution_id", "requested_role", "user_id", "role", "organization_id"]
)
def test_membership_decision_body_forbids_role_and_institution_input(
    field: str,
) -> None:
    """A client can never name a role or an institution on a decision request."""
    with _as(ADMIN_A_USER):
        response = client.post(
            "/api/v1/admin/memberships/requests/"
            "00000000-0000-0000-0000-000000000001/approve",
            headers=AUTH_HEADERS,
            json={field: "staff"},
        )
    assert response.status_code == 422, field


@pytest.mark.parametrize("principal,label", STAFF_AND_FACULTY_USERS)
def test_staff_and_faculty_cannot_reach_the_onboarding_lifecycle(
    principal: dict, label: str
) -> None:
    """The Phase 7.23 request queue, roster and lifecycle are admin-only."""
    for method, path in (
        ("GET", "/api/v1/admin/memberships/requests"),
        ("GET", "/api/v1/admin/memberships"),
        ("POST", f"/api/v1/admin/memberships/{STAFF_A}/deactivate"),
        ("POST", f"/api/v1/admin/memberships/{STAFF_A}/reactivate"),
    ):
        with _as(principal):
            response = client.request(method, path, headers=AUTH_HEADERS)
        assert response.status_code == 403, (label, method, path, response.status_code)
        assert _error_code(response) == "FORBIDDEN", (label, method, path)
