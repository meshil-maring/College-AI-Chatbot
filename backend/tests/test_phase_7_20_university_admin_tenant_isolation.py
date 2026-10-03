"""Phase 7.20 — authoritative University Admin scope and tenant isolation."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api.admin import _ADMIN, _APPROVAL
from app.core.security import get_current_user
from app.main import app


client = TestClient(app, raise_server_exceptions=False)

INST_A = "71000000-0000-0000-0000-00000000000a"
INST_B = "71000000-0000-0000-0000-00000000000b"
ADMIN_A = "72000000-0000-0000-0000-00000000000a"
ADMIN_B = "72000000-0000-0000-0000-00000000000b"
STUDENT_A = "73000000-0000-0000-0000-00000000000a"
STUDENT_B = "73000000-0000-0000-0000-00000000000b"
RESOURCE_ID = "74000000-0000-0000-0000-000000000001"


def _grant(role: str, institution_id: str, scope_type: str = "institution") -> dict:
    return {
        "role": role,
        "scope_type": scope_type,
        "scope_id": institution_id,
        "scope_organization_id": None,
        "is_active": True,
    }


def _principal(
    user_id: str,
    role: str,
    institution_id: str | None,
    *,
    status: str = "active",
    scope_type: str = "institution",
) -> dict:
    assignments = (
        [_grant(role, institution_id, scope_type)]
        if institution_id is not None
        else []
    )
    return {
        "user_id": user_id,
        "auth_user_id": user_id,
        "email": f"{role}@example.edu",
        "status": status,
        "roles": [role],
        # Deliberately None: the dependency must use role_assignments.scope_id.
        "institution_id": None,
        "role_assignments": assignments,
    }


ADMIN_A_USER = _principal(ADMIN_A, "admin", INST_A)
ADMIN_B_USER = _principal(ADMIN_B, "admin", INST_B)


def _active_institution(institution_id: UUID | str) -> dict:
    return {
        "institution_id": str(institution_id),
        "status": "active",
        "is_active": True,
    }


@contextmanager
def _authenticated(principal: dict, *, institution_active: bool = True):
    app.dependency_overrides[get_current_user] = lambda: principal
    institution = (
        _active_institution(principal["role_assignments"][0]["scope_id"])
        if institution_active and principal.get("role_assignments")
        else {"status": "suspended", "is_active": False}
    )
    with (
        patch("app.services.authorization.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.authorization.tenancy_repo.get_institution_by_id",
            return_value=institution,
        ),
    ):
        yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _clean_dependencies():
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)
    yield
    for dependency in (get_current_user, _ADMIN, _APPROVAL):
        app.dependency_overrides.pop(dependency, None)


def test_auth_me_projects_admin_scope_from_user_roles_without_student_profile() -> None:
    user = dict(ADMIN_A_USER)
    claims = {"sub": ADMIN_A, "email": user["email"]}
    with (
        patch("app.core.security.verify_jwt", return_value=claims),
        patch(
            "app.db.supabase.get_user_by_auth_id",
            new=AsyncMock(return_value=user),
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
        with _authenticated(principal), patch(
            "app.api.admin.admin_academics.list_students", return_value=[]
        ) as list_students:
            response = client.get(f"/api/v1/admin/students?institution_id={expected}")
        assert response.status_code == 200
        assert list_students.call_args.args[0] == UUID(expected)


@pytest.mark.parametrize(
    ("principal", "expected_code"),
    [
        (_principal(ADMIN_A, "admin", None), "SCOPE_MISSING"),
        (_principal(ADMIN_A, "admin", INST_A, scope_type="organization"), "FORBIDDEN"),
        (_principal(ADMIN_A, "admin", INST_A, status="inactive"), "ACCOUNT_INACTIVE"),
        (_principal(ADMIN_A, "super_admin", INST_A, scope_type="platform"), "FORBIDDEN"),
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


def test_staff_keeps_only_the_institution_scoped_approval_exception() -> None:
    staff = _principal("72000000-0000-0000-0000-0000000000aa", "staff", INST_A)
    with _authenticated(staff), patch(
        "app.api.admin.admin_academics.list_pending_approvals", return_value=[]
    ) as pending:
        allowed = client.get("/api/v1/admin/students/pending")
        denied = client.get("/api/v1/admin/me")
    assert allowed.status_code == 200
    assert pending.call_args.args[0] == UUID(INST_A)
    assert denied.status_code == 403


def test_forged_institution_query_and_code_cannot_change_scope() -> None:
    with _authenticated(ADMIN_A_USER), patch(
        "app.api.admin.admin_academics.list_students", return_value=[]
    ) as list_students:
        foreign = client.get(f"/api/v1/admin/students?institution_id={INST_B}")
        own = client.get(
            f"/api/v1/admin/students?institution_id={INST_A}&institution_code=FORGED"
        )
    assert foreign.status_code == 403
    assert foreign.json()["error"]["code"] == "TENANT_MISMATCH"
    assert own.status_code == 200
    assert list_students.call_args.args[0] == UUID(INST_A)


def test_forged_student_create_body_is_denied_before_write() -> None:
    with _authenticated(ADMIN_A_USER), patch(
        "app.api.admin.admin_academics.create_student"
    ) as create_student:
        response = client.post(
            "/api/v1/admin/students",
            json={
                "user_id": "75000000-0000-0000-0000-000000000001",
                "institution_id": INST_B,
                "student_number": "B-001",
                "enrollment_date": "2026-10-03",
            },
        )
    assert response.status_code == 403
    create_student.assert_not_called()


def test_cross_tenant_knowledge_source_and_document_are_denied() -> None:
    foreign_source = {"knowledge_source_id": RESOURCE_ID, "institution_id": INST_B}
    document = {"document_id": RESOURCE_ID, "knowledge_source_id": RESOURCE_ID}
    with _authenticated(ADMIN_A_USER), (
        patch(
            "app.api.admin.knowledge_repo.get_document_with_versions",
            return_value=document,
        )
    ), patch(
        "app.api.admin.knowledge_repo.get_knowledge_source_detail",
        return_value=foreign_source,
    ):
        response = client.get(f"/api/v1/admin/documents/{RESOURCE_ID}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_unknown_knowledge_source_is_denied_with_not_found() -> None:
    with _authenticated(ADMIN_A_USER), patch(
        "app.api.admin.knowledge_repo.get_knowledge_source_detail", return_value=None
    ):
        response = client.get(
            f"/api/v1/admin/knowledge-sources/{RESOURCE_ID}/documents"
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "KNOWLEDGE_SOURCE_NOT_FOUND"


@pytest.mark.parametrize(
    ("method", "path", "service_name", "row"),
    [
        (
            "PATCH",
            f"/api/v1/admin/faqs/{RESOURCE_ID}",
            "admin_faq.get_faq",
            {"faq_id": RESOURCE_ID, "institution_id": INST_B},
        ),
        (
            "DELETE",
            f"/api/v1/admin/notices/{RESOURCE_ID}",
            "admin_notices.get_notice",
            {"notice_id": RESOURCE_ID, "institution_id": INST_B},
        ),
    ],
)
def test_cross_tenant_faq_and_notice_mutations_are_denied(
    method: str, path: str, service_name: str, row: dict
) -> None:
    payload = {"question": "changed"} if method == "PATCH" else None
    with _authenticated(ADMIN_A_USER), patch(
        f"app.api.admin.{service_name}", return_value=row
    ):
        response = client.request(method, path, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_global_faq_mutation_is_not_tenant_admin_authority() -> None:
    with _authenticated(ADMIN_A_USER), patch(
        "app.api.admin.admin_faq.get_faq",
        return_value={"faq_id": RESOURCE_ID, "institution_id": None},
    ):
        response = client.patch(
            f"/api/v1/admin/faqs/{RESOURCE_ID}", json={"question": "changed"}
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/admin/students/{STUDENT_B}/results",
        f"/api/v1/admin/students/{STUDENT_B}/test-results",
        f"/api/v1/admin/students/{STUDENT_B}/attendance",
    ],
)
def test_cross_tenant_academic_resource_families_are_denied(path: str) -> None:
    with _authenticated(ADMIN_A_USER), patch(
        "app.api.admin.admin_academics.get_student",
        return_value={"student_id": STUDENT_B, "institution_id": INST_B},
    ):
        response = client.get(path)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"


def test_audit_list_is_forced_to_current_actor() -> None:
    with _authenticated(ADMIN_A_USER), patch(
        "app.api.admin.list_audit_entries", return_value=[]
    ) as audit:
        response = client.get("/api/v1/admin/audit-logs")
    assert response.status_code == 200
    assert audit.call_args.kwargs["actor_user_id"] == ADMIN_A


def test_cross_actor_audit_detail_and_filter_are_denied() -> None:
    with _authenticated(ADMIN_A_USER), patch(
        "app.api.admin.get_audit_entry",
        return_value={"audit_id": RESOURCE_ID, "actor_user_id": ADMIN_B},
    ):
        detail = client.get(f"/api/v1/admin/audit-logs/{RESOURCE_ID}")
        filtered = client.get(f"/api/v1/admin/audit-logs?actor_user_id={ADMIN_B}")
    assert detail.status_code == 403
    assert filtered.status_code == 403


def test_super_admin_platform_authorization_regression_is_unchanged() -> None:
    super_admin = {
        "user_id": "76000000-0000-0000-0000-000000000001",
        "auth_user_id": "76000000-0000-0000-0000-000000000002",
        "email": "super@example.edu",
        "roles": ["super_admin"],
        "status": "active",
        "institution_id": None,
        "role_assignments": [
            {
                "role": "super_admin",
                "scope_type": "platform",
                "scope_id": None,
                "is_active": True,
            }
        ],
    }
    app.dependency_overrides[get_current_user] = lambda: super_admin
    with patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
    ):
        platform = client.get("/api/v1/platform/me")
        admin = client.get("/api/v1/admin/me")
    assert platform.status_code == 200
    assert admin.status_code == 403

