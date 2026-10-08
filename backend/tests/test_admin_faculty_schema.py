"""Admin faculty endpoints handle pending migrations and preserve authorization."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api import admin
from app.core.security import get_current_user
from app.main import app
from app.services import faculty_responsibilities, phase81_rbac

TENANT = "30000000-0000-0000-0000-000000000001"
ACTOR = "10000000-0000-0000-0000-000000000001"
FACULTY = "10000000-0000-0000-0000-000000000002"
SECTION = "20000000-0000-0000-0000-000000000001"
ASSIGNMENT = "40000000-0000-0000-0000-000000000001"


def database_error(code, message):
    return APIError({"code": code, "message": message, "details": None, "hint": None})


@pytest.fixture
def admin_database(monkeypatch):
    actor = {
        "user_id": ACTOR, "roles": ["admin"], "status": "active",
        "institution_id": TENANT, "permissions_resolved": True,
        "effective_permissions": ["faculty.assignments.manage"],
        "role_assignments": [{
            "role": "admin", "scope_type": "institution", "scope_id": TENANT,
            "is_active": True,
        }],
    }
    db = MagicMock()
    query = db.table.return_value
    for method in ("select", "eq", "is_", "order", "range", "maybe_single"):
        getattr(query, method).return_value = query
    query.execute.return_value.data = []
    monkeypatch.setattr(phase81_rbac, "get_admin_client", lambda: db)
    monkeypatch.setattr(faculty_responsibilities, "get_admin_client", lambda: db)
    monkeypatch.setattr(phase81_rbac.admin_memberships, "list_roster", lambda *_args, **_kwargs: SimpleNamespace(members=[]))
    app.dependency_overrides[get_current_user] = lambda: actor
    app.dependency_overrides[admin._ADMIN] = lambda: actor
    try:
        yield db, query, actor
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(admin._ADMIN, None)


def assert_schema_unavailable(response, diagnostic):
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "FACULTY_SCHEMA_UNAVAILABLE"
    assert "database update" in response.json()["error"]["message"]
    assert diagnostic not in response.text


@pytest.mark.parametrize("code,message", [
    ("42703", "column faculty_section_assignments.start_at does not exist"),
    ("PGRST204", "Could not find the 'start_at' column of 'faculty_section_assignments' in the schema cache"),
    ("PGRST205", "Could not find the table 'public.faculty_section_assignments' in the schema cache"),
])
def test_assignment_list_reports_pending_schema(admin_database, caplog, code, message):
    db, query, _actor = admin_database
    query.execute.side_effect = database_error(code, message)
    response = TestClient(app).get("/api/v1/admin/faculty-assignments")
    assert_schema_unavailable(response, message)
    db.table.assert_called_once_with("faculty_section_assignments")
    query.eq.assert_called_with("institution_id", TENANT)
    assert "20261011000000_faculty_responsibilities_and_validity.sql" in caplog.text


@pytest.mark.parametrize("code,message", [
    ("PGRST205", "Could not find the table 'public.responsibility_definitions' in the schema cache"),
    ("PGRST200", "Could not find a relationship between 'responsibility_definitions' and 'responsibility_permissions' in the schema cache"),
])
def test_responsibility_list_reports_pending_schema(admin_database, code, message):
    db, query, _actor = admin_database

    def table(name):
        if name == "responsibility_definitions":
            raise database_error(code, message)
        return query

    db.table.side_effect = table
    response = TestClient(app).get("/api/v1/admin/faculty-responsibilities")
    assert_schema_unavailable(response, message)


@pytest.mark.parametrize("method,path,payload,function", [
    ("POST", "/faculty-assignments", {"faculty_user_id": FACULTY, "section_id": SECTION}, "phase81_manage_faculty_section_assignment"),
    ("POST", "/faculty-assignments", {"faculty_user_id": FACULTY, "section_id": SECTION, "start_at": "2026-10-07T12:00:00Z"}, "create_faculty_teaching_assignment"),
    ("PATCH", f"/faculty-assignments/{ASSIGNMENT}", {"start_at": "2026-10-07T12:00:00Z"}, "update_faculty_teaching_validity"),
    ("POST", "/faculty-responsibilities", {"faculty_user_id": FACULTY, "responsibility_code": "hod", "scope_type": "department", "scope_id": SECTION, "start_at": "2026-10-07T12:00:00Z"}, "manage_faculty_responsibility"),
])
def test_mutations_report_missing_faculty_functions(admin_database, method, path, payload, function):
    db, _query, _actor = admin_database
    message = f"Could not find the function public.{function} in the schema cache"
    db.rpc.return_value.execute.side_effect = database_error("PGRST202", message)
    response = TestClient(app).request(method, f"/api/v1/admin{path}", json=payload)
    assert_schema_unavailable(response, message)
    assert db.rpc.call_args.args[0] == function


@pytest.mark.parametrize("path", ["faculty-assignments", "faculty-responsibilities"])
def test_revocation_reports_missing_faculty_table(admin_database, path):
    _db, query, _actor = admin_database
    table = "faculty_section_assignments" if path == "faculty-assignments" else "faculty_responsibilities"
    message = f"Could not find the table 'public.{table}' in the schema cache"
    query.execute.side_effect = database_error("PGRST205", message)
    response = TestClient(app).delete(f"/api/v1/admin/{path}/{ASSIGNMENT}")
    assert_schema_unavailable(response, message)


@pytest.mark.parametrize("path", ["faculty-assignments", "faculty-responsibilities"])
def test_missing_permission_is_denied_before_database_access(admin_database, path):
    db, _query, actor = admin_database
    actor["effective_permissions"] = []
    response = TestClient(app).get(f"/api/v1/admin/{path}")
    assert response.status_code == 403
    db.table.assert_not_called()
    db.rpc.assert_not_called()


def test_ready_database_returns_the_assignment_contract(admin_database):
    response = TestClient(app).get("/api/v1/admin/faculty-assignments")
    assert response.status_code == 200
    assert response.json() == {"faculty": [], "sections": [], "assignments": []}


@pytest.mark.parametrize("code,message", [
    ("PGRST205", "Could not find the table 'public.departments' in the schema cache"),
    ("42501", "permission denied for table faculty_section_assignments"),
    ("PGRST000", "connection failed while querying faculty_section_assignments"),
])
def test_unrelated_database_errors_propagate(admin_database, code, message):
    _db, query, _actor = admin_database
    error = database_error(code, message)
    query.execute.side_effect = error
    with pytest.raises(APIError) as caught:
        TestClient(app).get("/api/v1/admin/faculty-assignments")
    assert caught.value is error
