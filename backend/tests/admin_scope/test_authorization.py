"""Test authorization."""

from __future__ import annotations

from app.core.errors import AppError

from app.services.auth.authorization import resolve_institution_authorization_context

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

import pytest

from .support import (
    ADMIN_A,
    ADMIN_A_USER,
    ADMIN_B_USER,
    INST_A,
    INST_B,
    RESOURCE_ID,
    STUDENT_A,
    _authenticated,
    _clean_dependencies,
    _principal,
    client,
    conflicting_admin,
)


def test_auth_me_projects_admin_scope_from_user_roles_without_student_profile() -> None:
    user = dict(ADMIN_A_USER)
    user["permissions_resolved"] = True
    user["scoped_permissions_resolved"] = True
    user["role_assignments"] = [
        dict(grant, permissions=[]) for grant in user["role_assignments"]
    ]
    claims = {"sub": ADMIN_A, "email": user["email"]}
    with (
        patch("app.core.security.tokens.verify_jwt", return_value=claims),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(return_value=user),
        ),
        patch("app.services.auth.identity.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.auth.identity.tenancy_repo.get_institution_by_id",
            return_value={"institution_id": INST_A, "code": "ALPHA"},
        ),
    ):
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer phase720.token"},
        )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["institution_id"] == INST_A


def test_admin_a_and_admin_b_each_receive_their_authoritative_scope() -> None:
    for principal, expected in ((ADMIN_A_USER, INST_A), (ADMIN_B_USER, INST_B)):
        with _authenticated(principal):
            response = client.get("/api/v1/admin/me")
        assert response.status_code == 200
        assert response.json()["is_admin"] is True
        # The endpoint does not expose scope, so prove it through a scoped call.
        with (
            _authenticated(principal),
            patch(
                "app.services.admin.admin_academics.list_pending_approvals",
                return_value=[],
            ) as list_students,
        ):
            response = client.get(
                f"/api/v1/admin/students/pending?institution_id={expected}"
            )
        assert response.status_code == 200
        assert list_students.call_args.args[0] == UUID(expected)


@pytest.mark.parametrize(
    ("principal", "expected_code"),
    [
        (_principal(ADMIN_A, "admin", None), "SCOPE_MISSING"),
        (_principal(ADMIN_A, "admin", INST_A, scope_type="organization"), "FORBIDDEN"),
        (_principal(ADMIN_A, "admin", INST_A, status="inactive"), "ACCOUNT_INACTIVE"),
        (
            _principal(ADMIN_A, "super_admin", INST_A, scope_type="platform"),
            "FORBIDDEN",
        ),
        (_principal(STUDENT_A, "student", INST_A), "FORBIDDEN"),
        (_principal(ADMIN_A, "faculty", INST_A), "FORBIDDEN"),
        (_principal(ADMIN_A, "staff", INST_A), "FORBIDDEN"),
    ],
)
def test_admin_dependency_fails_closed_for_invalid_role_or_scope(
    principal: dict, expected_code: str
) -> None:
    with _authenticated(principal):
        response = client.get("/api/v1/admin/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == expected_code


def test_inactive_institution_is_denied() -> None:
    with _authenticated(ADMIN_A_USER, institution_active=False):
        response = client.get("/api/v1/admin/me")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_INACTIVE"


def test_conflicting_institution_grants_fail_context_resolution(
    conflicting_admin: dict,
) -> None:
    with patch("app.services.auth.authorization.get_admin_client") as get_admin_client:
        with pytest.raises(AppError) as exc_info:
            resolve_institution_authorization_context(
                conflicting_admin, allowed_roles=("admin",)
            )
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "SCOPE_INCONSISTENT"
    get_admin_client.assert_not_called()


@pytest.mark.parametrize("method", ["GET", "PATCH"])
def test_conflicting_institution_grants_are_denied_before_resource_access(
    conflicting_admin: dict, method: str
) -> None:
    with (
        _authenticated(conflicting_admin),
        patch("app.services.admin.admin_faq.get_faq") as get_faq,
        patch("app.services.admin.admin_faq.update_faq") as update_faq,
        patch("app.api.admin.common.record_audit") as record_audit,
    ):
        response = client.request(
            method,
            f"/api/v1/admin/faqs/{RESOURCE_ID}",
            json={"question": "changed"} if method == "PATCH" else None,
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SCOPE_INCONSISTENT"
    get_faq.assert_not_called()
    update_faq.assert_not_called()
    record_audit.assert_not_called()
