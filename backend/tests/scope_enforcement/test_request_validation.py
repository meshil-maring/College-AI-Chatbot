"""Test request validation."""

from __future__ import annotations

from app.core.errors import AppError

from app.core.security import (
    assert_tenant_object,
    get_current_user,
    require_roles,
    scope_tenant,
)

from app.services.auth import authorization as authz

from app.services.platform import tenancy as tenancy_svc

from unittest.mock import AsyncMock, MagicMock, patch

import asyncio

import pytest

from .database import (
    _db,
)

from .fixtures import (
    _active_institution_authorization,
)

from .state import (
    _base_state,
)

from .support import (
    JR_A,
    ORG_A,
    ORG_ADMIN,
    ORG_B,
    TENANT_A,
    _as,
    _authz_patches,
    _clear,
    _login,
    _logout,
    _role_row,
    _user,
    client,
)


def test_08_correct_role_enforcement_matrix():
    """admin / staff / faculty / student pass their authorized boundaries."""
    # admin passes the admin boundary.
    admin = _user(TENANT_A, roles=("admin",))
    assert asyncio.run(require_roles("admin")(current_user=admin)) is admin
    # staff passes the approval boundary (admin + staff).
    staff = _user(TENANT_A, roles=("staff",))
    assert asyncio.run(require_roles("admin", "staff")(current_user=staff)) is staff
    # faculty passes the ingestion boundary (admin + staff + faculty).
    faculty = _user(TENANT_A, roles=("faculty",))
    assert (
        asyncio.run(require_roles("admin", "staff", "faculty")(current_user=faculty))
        is faculty
    )
    # student passes the student-only boundary and nothing above it.
    student = _user(TENANT_A, roles=("student",))
    assert asyncio.run(require_roles("student")(current_user=student)) is student
    with pytest.raises(AppError) as admin_err:
        asyncio.run(require_roles("admin")(current_user=student))
    assert admin_err.value.code == "FORBIDDEN"


def test_09_unauthorized_role_denied():
    """Faculty cannot reach admin-only operations (403 FORBIDDEN)."""
    faculty = _user(TENANT_A, roles=("faculty",))
    _as(faculty)
    try:
        with patch(
            "app.services.admin.admin_academics.list_pending_approvals"
        ) as list_students:
            resp = client.get("/api/v1/admin/me")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN"
        list_students.assert_not_called()
    finally:
        _clear()


def test_10_client_role_injection_denied():
    """Login / registration schemas forbid client-supplied role fields."""
    base_login = {"email": "user@example.com", "password": "secret123"}
    for extra in ({"role": "admin"}, {"roles": ["admin"]}, {"scope_type": "platform"}):
        resp = client.post("/api/v1/auth/login", json={**base_login, **extra})
        assert resp.status_code == 422, (extra, resp.text)

    base_student_login = {"identifier": "student@college.edu", "password": "pw"}
    for extra in (
        {"role": "admin"},
        {"institution_id": TENANT_A},
        {"scope_id": TENANT_A},
    ):
        resp = client.post(
            "/api/v1/auth/student/login", json={**base_student_login, **extra}
        )
        assert resp.status_code == 422, (extra, resp.text)

    base_registration = {
        "institution_id": TENANT_A,
        "email": "new@college.edu",
        "password": "secret123",
        "first_name": "New",
        "last_name": "Student",
        "register_number": "REG137",
    }
    for extra in (
        {"role": "admin"},
        {"roles": ["admin"]},
        {"approval_status": "approved"},
    ):
        resp = client.post("/api/v1/registration", json={**base_registration, **extra})
        assert resp.status_code == 422, (extra, resp.text)


def test_11_client_scope_injection_denied():
    """Decision bodies cannot carry scope/status fields (extra='forbid')."""
    state = _base_state()
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        for extra in (
            {"status": "approved", "scope_type": "platform"},
            {"role": "admin", "scope_id": ORG_B},
            {"organization_id": ORG_B},
        ):
            resp = client.post(
                f"/api/v1/institutions/join-requests/{JR_A}/decision",
                json={"decision": "approve", **extra},
            )
            assert resp.status_code == 422, (extra, resp.text)
            assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    _logout()
    assert state["institution_join_requests"][JR_A]["status"] == "pending"
