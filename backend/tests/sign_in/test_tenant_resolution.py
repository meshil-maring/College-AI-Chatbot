"""Test tenant resolution."""

from __future__ import annotations

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID, uuid4

from .credentials import (
    student_login_api,
)

from .identity import (
    _active_institution_authorization,
    _as_authenticated,
    _auth_user,
)

from .support import (
    APPROVED_EMAIL,
    APPROVED_REGISTER,
    FAKE_CLAIMS,
    INSTITUTION_A,
    INSTITUTION_B,
    INSTITUTION_CODE,
    ORGANIZATION_ID,
    STAFF_EMAIL,
    STUDENT_B,
    client,
    institution_db,
    student_row,
)


def test_19_cross_institution_access_denied():
    """Institution A staff cannot reach institution B student records."""
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": STAFF_EMAIL,
    }
    projection = _auth_user(user, roles=("staff",), institution_id=INSTITUTION_A)
    target = {
        "student_id": str(STUDENT_B),
        "institution_id": str(INSTITUTION_B),
        "approval_status": "pending",
    }
    verify, db = _as_authenticated(projection)
    with (
        verify,
        db,
        patch(
            "app.services.admin.admin_academics.get_admin_client",
            return_value=MagicMock(),
        ),
        patch(
            "app.repositories.admin.admin_academics.get_student_for_approval",
            return_value=target,
        ),
    ):
        response = client.post(
            f"/api/v1/admin/students/{STUDENT_B}/approve",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_19b_cross_institution_login_requires_correct_institution_code():
    """An academic identifier only resolves inside its own institution."""
    response = student_login_api(
        student=None,  # not present in the OTHER institution
        identifier=APPROVED_REGISTER,
        institution_code="OTHER-CODE",
        institution={
            "institution_id": str(INSTITUTION_B),
            "name": "Other College",
            "code": "OTHER-CODE",
            "status": "active",
            "is_active": True,
        },
        db=institution_db(),
        by_register=None,
        by_roll=None,
    )
    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_19c_cross_institution_student_lookup_uses_scoped_query():
    """The repository lookup is always filtered by institution_id."""
    from app.repositories.admin import admin_academics as academics_repo

    db = MagicMock()
    table = MagicMock()
    db.table.return_value = table
    for method in ("select", "eq", "limit", "maybe_single", "execute"):
        getattr(table, method).return_value = table
    table.execute.return_value = SimpleNamespace(data=None)

    academics_repo.get_student_by_register_number(db, INSTITUTION_A, "REG-1")

    scoped = {call.args[0] for call in table.eq.call_args_list}
    assert scoped == {"institution_id", "register_number"}


def test_20a_tenant_resolution_after_email_login():
    """After email login the student profile is resolved server-side from the JWT.

    ``get_current_user`` (JWT ``sub`` -> ``get_user_by_auth_id``) supplies the
    tenant; the endpoint then asserts the returned profile belongs to that same
    tenant. Nothing tenant-related is accepted from the client.
    """
    user = {
        "user_id": uuid4(),
        "auth_user_id": FAKE_CLAIMS["sub"],
        "email": APPROVED_EMAIL,
    }
    projection = _auth_user(user, roles=("student",), institution_id=INSTITUTION_A)
    profile = {"email": APPROVED_EMAIL, "institution_name": "My institution"}
    verify, db = _as_authenticated(projection)
    with (
        verify,
        db,
        patch(
            "app.api.students.students.student_data.get_own_profile",
            return_value=profile,
        ) as get_profile,
    ):
        response = client.get(
            "/api/v1/students/me/profile",
            headers={"Authorization": "Bearer valid.token.here"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["institution_name"] == "My institution"
    assert "institution_id" not in response.json()
    # The profile was resolved from the JWT-derived user_id, never a client id.
    assert UUID(str(get_profile.call_args.args[0])) == UUID(str(user["user_id"]))


def test_20b_tenant_resolution_after_academic_identifier_login():
    """Register-number login resolves the student + tenant server-side.

    The response shape is the LOCKED Phase 6.5 contract (``access_token`` /
    ``message`` / ``user``); internal tenant/student ids are never exposed.
    """
    student = student_row()
    response = student_login_api(
        student=student,
        identifier=APPROVED_REGISTER,
        institution_code=INSTITUTION_CODE,
        by_register=student,
        by_roll=None,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {
        "access_token",
        "refresh_token",
        "expires_in",
        "message",
        "user",
    }
    assert body["user"]["email"] == APPROVED_EMAIL
    assert str(INSTITUTION_A) not in response.text
    assert str(student["student_id"]) not in response.text


def test_20c_authorization_context_resolves_scope_from_user_roles():
    """Post-login scope resolution reads user_roles, not the JWT or the client."""
    from app.services.auth.authorization import (
        INSTITUTION,
        resolve_authorization_context,
    )

    rows = [
        {
            "role_id": uuid4(),
            "role_name": "staff",
            "is_active": True,
            "scope_type": INSTITUTION,
            "scope_id": str(INSTITUTION_A),
            "scope_organization_id": str(ORGANIZATION_ID),
        }
    ]
    user = {
        "user_id": uuid4(),
        "email": STAFF_EMAIL,
        "institution_id": str(INSTITUTION_A),
    }
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.repositories.platform.tenancy.get_user_role_scope_rows",
            return_value=rows,
        ),
        patch(
            "app.repositories.platform.tenancy.get_institution_organization",
            return_value=ORGANIZATION_ID,
        ),
    ):
        context = resolve_authorization_context(user)

    assert context["scope_type"] == INSTITUTION
    assert context["institution_id"] == str(INSTITUTION_A)
    assert context["roles"] == ["staff"]
