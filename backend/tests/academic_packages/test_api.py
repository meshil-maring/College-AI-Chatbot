"""Authenticated scope and database-final authorization using isolated doubles."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.academics.academic_packages import router
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user
from app.services.academics import academic_packages as service
from app.services.auth import authorization
from .test_contracts import ID, OTHER, PAYLOADS

BASE = "/api/v1/academic-packages"


@pytest.fixture
def api(monkeypatch):
    actor = {"user_id": ID, "roles": ["admin"], "status": "active", "institution_id": OTHER,
             "permissions_resolved": True, "effective_permissions": [],
             "role_assignments": [{"role": "admin", "scope_type": "institution", "scope_id": ID}]}
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {"records": {}, "capabilities": []}
    monkeypatch.setattr(service, "get_admin_client", lambda: db)
    monkeypatch.setattr(authorization, "get_admin_client", lambda: db)
    institution = {"status": "active", "is_active": True}
    monkeypatch.setattr(authorization.tenancy_repo, "get_institution_by_id", lambda *_: institution)
    student = MagicMock(return_value={"institution_id": ID})
    monkeypatch.setattr(service, "get_student_context", student)
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: actor
    return TestClient(app), db, actor, institution, student


def test_catalogue_uses_authenticated_actor_and_grant_institution(api):
    client, db, *_ = api
    assert client.get(BASE + f"?institution_id={OTHER}&actor_user_id={OTHER}").status_code == 200
    db.rpc.assert_called_once_with("academic_package_catalogue", {
        "p_actor_user_id": ID, "p_institution_id": ID,
    })


@pytest.mark.parametrize("operation", PAYLOADS)
def test_commands_use_one_authoritative_rpc_and_no_direct_writes(api, operation):
    client, db, *_ = api
    assert client.post(f"{BASE}/{operation}", json=PAYLOADS[operation]).status_code == 200
    db.rpc.assert_called_once_with("academic_package_command", {
        "p_actor_user_id": ID, "p_institution_id": ID,
        "p_operation": operation, "p_payload": PAYLOADS[operation],
    })
    db.table.assert_not_called()


@pytest.mark.parametrize("role", ["admin", "staff", "faculty", "student"])
def test_actor_boundary_does_not_invent_unscoped_faculty_or_staff_grants(api, role):
    client, db, actor, _, student = api
    actor["roles"] = [role]
    actor["role_assignments"][0]["role"] = role
    db.rpc.return_value.execute.side_effect = APIError({"code": "42501", "message": "private SQL", "details": "", "hint": ""})
    response = client.post(f"{BASE}/assign_package", json=PAYLOADS["assign_package"])
    assert response.status_code == 403 and "private SQL" not in response.text
    assert bool(student.call_count) == (role == "student")


@pytest.mark.parametrize("scope", ["platform", "organization", None])
def test_noninstitution_grants_fail_before_rpc(api, scope):
    client, db, actor, *_ = api
    actor["role_assignments"][0]["scope_type"] = scope
    assert client.get(BASE).status_code == 403
    db.rpc.assert_not_called()


def test_account_and_institution_lifecycle_fail_closed(api):
    client, db, actor, institution, _ = api
    actor["status"] = "inactive"
    assert client.get(BASE).status_code == 403
    actor["status"] = "active"
    institution["is_active"] = False
    assert client.get(BASE).status_code == 403
    db.rpc.assert_not_called()


def test_student_eligibility_failure_prevents_choice(api):
    client, db, actor, _, student = api
    actor["roles"] = ["student"]
    actor["role_assignments"][0]["role"] = "student"
    student.side_effect = AppError("Student account is not approved", 403, "STUDENT_NOT_APPROVED")
    assert client.post(f"{BASE}/assign_package", json=PAYLOADS["assign_package"]).status_code == 403
    db.rpc.assert_not_called()


def test_unknown_or_forged_commands_do_not_reach_rpc(api):
    client, db, *_ = api
    assert client.post(f"{BASE}/sql", json={}).status_code == 404
    assert client.post(f"{BASE}/assign_package", json={**PAYLOADS["assign_package"], "institution_id": OTHER}).status_code == 422
    db.rpc.assert_not_called()


@pytest.mark.parametrize("code,status", [("PGRST202", 503), ("P0001", 409), ("23505", 409),
                                         ("23514", 422), ("P0002", 404), ("XX000", 500)])
def test_database_failures_are_stable_and_sanitized(api, code, status):
    client, db, *_ = api
    db.rpc.return_value.execute.side_effect = APIError({"code": code, "message": "private row/SQL", "details": "", "hint": ""})
    response = client.get(BASE)
    assert response.status_code == status
    assert "private row/SQL" not in response.text


def test_closed_package_changes_return_a_specific_conflict(api):
    client, db, *_ = api
    db.rpc.return_value.execute.side_effect = APIError({
        "code": "23514", "message": "Package changes are closed for this class",
        "details": "", "hint": "",
    })
    response = client.post(f"{BASE}/change_package", json=PAYLOADS["change_package"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACADEMIC_PACKAGE_CLOSED"
