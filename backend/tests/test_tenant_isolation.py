"""Tenant isolation tests — institution_id is the tenant key.

Multi-tenancy model under test:

    College A (tenant A) -> institution_id = A
    College B (tenant B) -> institution_id = B
    Student of A -> resolved tenant A (students.institution_id)
    Student of B -> resolved tenant B

A tenant-bound user may only ever touch rows of their own institution;
accounts without a tenant (platform-level, e.g. admins without a students
profile) keep the previous unrestricted behaviour.
"""

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.admin import _ADMIN
from app.core.errors import AppError
from app.core.security import (
    assert_tenant_object,
    get_current_user,
    scope_tenant,
    user_tenant_id,
)
from app.main import app
from app.schemas.chat import ChatResponse

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "30000000-0000-0000-0000-000000000001"
TENANT_B = "30000000-0000-0000-0000-000000000002"


def _user(tenant: str | None = None, roles: tuple[str, ...] = ("student",)) -> dict:
    return {
        "user_id": str(uuid4()),
        "auth_user_id": str(uuid4()),
        "email": "tenant-test@example.com",
        "roles": list(roles),
        "institution_id": tenant,
    }


# ---------------------------------------------------------------------------
# Unit tests — guard primitives
# ---------------------------------------------------------------------------


def test_user_tenant_id_resolves_and_normalises():
    assert user_tenant_id(_user(TENANT_A)) == UUID(TENANT_A)
    assert user_tenant_id(_user(None)) is None


def test_scope_tenant_allows_own_institution():
    assert scope_tenant(_user(TENANT_A), UUID(TENANT_A)) == UUID(TENANT_A)


def test_scope_tenant_defaults_to_own_institution_when_none_requested():
    assert scope_tenant(_user(TENANT_A), None) == UUID(TENANT_A)


def test_scope_tenant_rejects_other_institution():
    with pytest.raises(AppError) as excinfo:
        scope_tenant(_user(TENANT_A), UUID(TENANT_B))
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_MISMATCH"


def test_scope_tenant_platform_account_passthrough():
    assert scope_tenant(_user(None), UUID(TENANT_B)) == UUID(TENANT_B)
    assert scope_tenant(_user(None), None) is None


def test_assert_tenant_object_allows_own_and_global_rows():
    assert_tenant_object(_user(TENANT_A), TENANT_A)
    assert_tenant_object(_user(TENANT_A), None)  # global row


# ---------------------------------------------------------------------------
# Chat endpoint — the client-supplied institution_id cannot cross tenants
# ---------------------------------------------------------------------------


def _chat_response(session_id: UUID) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        conversation_id=session_id,
        message_id=None,
        status="insufficient_context",
        model_used="test/model",
    )


@pytest.fixture(autouse=True)
def _tenant_auth_override():
    """Bind the authenticated user to tenant A for the endpoint tests below."""
    app.dependency_overrides[get_current_user] = lambda: _user(TENANT_A)
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_chat_rejects_cross_tenant_institution():
    with patch("app.main.process_chat_request") as process:
        response = client.post(
            "/api/v1/generation/chat",
            json={"user_query": "What is the hostel fee?", "institution_id": TENANT_B},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    process.assert_not_called()


def test_chat_allows_own_tenant_and_propagates_it():
    captured = {}

    def process(request, context, provider, user_id):
        captured["institution_id"] = request.institution_id
        return _chat_response(context.session_id)

    with patch("app.main.process_chat_request", side_effect=process):
        response = client.post(
            "/api/v1/generation/chat",
            json={"user_query": "What is the hostel fee?", "institution_id": TENANT_A},
        )

    assert response.status_code == 200
    assert captured["institution_id"] == UUID(TENANT_A)


# ---------------------------------------------------------------------------
# Admin endpoints — tenant-bound admins are forced to their own institution
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant_admin_override():
    app.dependency_overrides[_ADMIN] = lambda: _user(TENANT_A, roles=("admin",))
    yield
    app.dependency_overrides.pop(_ADMIN, None)


def test_admin_list_students_rejects_foreign_institution(tenant_admin_override):
    with patch("app.api.admin.admin_academics.list_students") as list_students:
        response = client.get(f"/api/v1/admin/students?institution_id={TENANT_B}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_MISMATCH"
    list_students.assert_not_called()


def test_admin_list_students_forced_to_own_institution(tenant_admin_override):
    with patch(
        "app.api.admin.admin_academics.list_students", return_value=[]
    ) as list_students:
        response = client.get(f"/api/v1/admin/students?institution_id={TENANT_A}")

    assert response.status_code == 200
    assert list_students.call_args.args[0] == UUID(TENANT_A)


def test_platform_admin_can_list_any_institution():
    """Platform-level admins (no tenant) keep the previous unrestricted scope."""
    app.dependency_overrides[_ADMIN] = lambda: _user(None, roles=("admin",))
    try:
        with patch(
            "app.api.admin.admin_academics.list_students", return_value=[]
        ) as list_students:
            response = client.get(f"/api/v1/admin/students?institution_id={TENANT_B}")
    finally:
        app.dependency_overrides.pop(_ADMIN, None)

    assert response.status_code == 200
    assert list_students.call_args.args[0] == UUID(TENANT_B)
    assert_tenant_object(_user(None), TENANT_B)  # platform account


def test_assert_tenant_object_rejects_cross_tenant_row():
    with pytest.raises(AppError) as excinfo:
        assert_tenant_object(_user(TENANT_A), TENANT_B)
    assert excinfo.value.status_code == 403