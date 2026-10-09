"""Academic master API security and validation; isolated database doubles only."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.core.security import get_current_user
from app.main import app
from app.services import academic_setup as service
from app.services import authorization

TENANT = "30000000-0000-0000-0000-000000000001"
FOREIGN = "30000000-0000-0000-0000-000000000002"
ACTOR = "10000000-0000-0000-0000-000000000001"
ID = "20000000-0000-0000-0000-000000000001"
BASE = "/api/v1/admin/academic-setup"
PAYLOADS = {
    "departments": {"name": "Science", "code": "SCI"},
    "programs": {"name": "Science degree", "code": "BS", "department_id": ID, "degree_type": "BSc", "duration_years": 3},
    "academic_years": {"name": "2026-27", "code": "Y26", "start_date": "2026-07-01", "end_date": "2027-06-30"},
    "semesters": {"name": "Semester 1", "code": "S1", "academic_year_id": ID, "semester_number": 1, "start_date": "2026-07-01", "end_date": "2026-12-31"},
    "courses": {"name": "Mathematics", "code": "MATH", "department_id": ID},
    "program_courses": {"program_id": ID, "course_id": ID, "course_type": "core"},
    "course_offerings": {"program_id": ID, "course_id": ID, "academic_year_id": ID, "semester_id": ID},
    "sections": {"name": "Section A", "code": "A", "course_offering_id": ID},
}


@pytest.fixture
def api(monkeypatch):
    user = {
        "user_id": ACTOR, "roles": ["admin"], "status": "active", "institution_id": FOREIGN,
        "permissions_resolved": True,
        "effective_permissions": [f"{resource}.{action}" for resource in set(service.RESOURCES.values()) for action in ("read", "manage")],
        "role_assignments": [{"role": "admin", "scope_type": "institution", "scope_id": TENANT, "is_active": True}],
    }
    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = {"saved": True}
    monkeypatch.setattr(service, "get_admin_client", lambda: db)
    monkeypatch.setattr(authorization, "get_admin_client", lambda: db)
    institution = {"status": "active", "is_active": True}
    monkeypatch.setattr(authorization.tenancy_repo, "get_institution_by_id", lambda *_: institution)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield TestClient(app), db, user, institution
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("entity", PAYLOADS)
def test_creates_existing_entity_with_server_actor_and_scope(api, entity):
    client, db, _, _ = api
    response = client.post(f"{BASE}/{entity}?institution_id={FOREIGN}&actor_user_id={ID}", json=PAYLOADS[entity])
    assert response.status_code == 201
    name, args = db.rpc.call_args.args
    assert name == "manage_academic_master_record"
    assert args["p_actor_user_id"] == ACTOR
    assert args["p_institution_id"] == TENANT
    assert args["p_entity"] == entity
    assert args["p_record_id"] is None


@pytest.mark.parametrize("entity", PAYLOADS)
def test_safe_update_and_deactivation_preserve_identity(api, entity):
    client, db, _, _ = api
    assert client.patch(f"{BASE}/{entity}/{ID}", json={"is_active": False}).status_code == 200
    assert db.rpc.call_args.args[1]["p_record_id"] == ID
    assert db.rpc.call_args.args[1]["p_payload"] == {"is_active": False}
    assert client.delete(f"{BASE}/{entity}/{ID}").status_code == 405


@pytest.mark.parametrize("role", ["faculty", "student", "staff", "super_admin", "class_in_charge"])
def test_other_roles_cannot_use_academic_management_even_with_forged_permissions(api, role):
    client, db, user, _ = api
    user["roles"] = [role]
    user["role_assignments"][0]["role"] = role
    assert client.post(f"{BASE}/departments", json=PAYLOADS["departments"]).status_code == 403
    assert client.get(BASE).status_code == 403
    db.rpc.assert_not_called()


@pytest.mark.parametrize("scope", ["platform", "organization", None])
def test_admin_requires_institution_grant(api, scope):
    client, db, user, _ = api
    user["role_assignments"][0]["scope_type"] = scope
    assert client.get(BASE).status_code == 403
    db.table.assert_not_called()


@pytest.mark.parametrize("entity", PAYLOADS)
def test_revoked_management_permission_denies_before_write(api, entity):
    client, db, user, _ = api
    user["effective_permissions"] = []
    assert client.post(f"{BASE}/{entity}", json=PAYLOADS[entity]).status_code == 403
    db.rpc.assert_not_called()


def test_inactive_account_and_institution_fail_closed(api):
    client, db, user, institution = api
    user["status"] = "inactive"
    assert client.get(BASE).status_code == 403
    user["status"] = "active"
    institution["is_active"] = False
    assert client.get(BASE).status_code == 403
    db.rpc.assert_not_called()


@pytest.mark.parametrize("entity,fields", [
    ("departments", {"institution_id": FOREIGN}), ("departments", {"actor_user_id": ID}),
    ("departments", {"name": "   "}), ("departments", {"code": None}),
    ("programs", {"duration_years": 0}), ("semesters", {"semester_number": 1.2}),
    ("courses", {"credits": -1}), ("course_offerings", {"capacity": 0}),
    ("sections", {"capacity": 1.5}), ("program_courses", {"course_type": "forged"}),
])
def test_invalid_create_payloads_never_reach_database(api, entity, fields):
    client, db, _, _ = api
    assert client.post(f"{BASE}/{entity}", json={**PAYLOADS[entity], **fields}).status_code == 422
    db.rpc.assert_not_called()


@pytest.mark.parametrize("entity,fields", [
    ("programs", {"department_id": FOREIGN}), ("semesters", {"academic_year_id": FOREIGN}),
    ("courses", {"department_id": FOREIGN}), ("program_courses", {"program_id": FOREIGN}),
    ("course_offerings", {"semester_id": FOREIGN}), ("sections", {"code": "B"}),
    ("departments", {"name": None}), ("departments", {"is_active": None}),
    ("departments", {}),
])
def test_reparenting_null_required_fields_and_empty_updates_are_rejected(api, entity, fields):
    client, db, _, _ = api
    assert client.patch(f"{BASE}/{entity}/{ID}", json=fields).status_code == 422
    db.rpc.assert_not_called()


@pytest.mark.parametrize("code,status", [("23505", 409), ("23P01", 409), ("23514", 422), ("23503", 422), ("P0002", 404), ("42501", 403), ("PGRST202", 503), ("42703", 503), ("PGRST204", 503), ("XX000", 500)])
def test_database_conflicts_and_foreign_ids_return_safe_errors(api, code, status):
    client, db, _, _ = api
    db.rpc.return_value.execute.side_effect = APIError({"code": code, "message": "PRIVATE_DATABASE_DIAGNOSTIC", "details": None, "hint": None})
    response = client.patch(f"{BASE}/departments/{ID}", json={"name": "Updated"})
    assert response.status_code == status
    assert "PRIVATE_DATABASE_DIAGNOSTIC" not in response.text


def test_catalogue_queries_follow_tenant_ancestors_and_filter_corrupt_links(api):
    client, db, user, _ = api
    source = {
        "departments": [{"department_id": "d", "is_active": True}],
        "programs": [{"program_id": "p", "department_id": "d"}],
        "courses": [{"course_id": "c", "department_id": "d"}],
        "academic_years": [{"academic_year_id": "y"}],
        "semesters": [{"semester_id": "s", "academic_year_id": "y"}],
        "program_courses": [{"program_id": "p", "course_id": "foreign", "semester_id": None}],
        "course_offerings": [
            {"course_offering_id": "o", "program_id": "p", "course_id": "c", "academic_year_id": "y", "semester_id": "s"},
            {"course_offering_id": "foreign", "program_id": "p", "course_id": "foreign", "academic_year_id": "y", "semester_id": "s"},
        ],
        "sections": [{"section_id": "section", "course_offering_id": "o"}],
    }
    queries = {}
    def table(entity):
        query = MagicMock()
        for method in ("select", "order", "eq", "in_", "range"):
            getattr(query, method).return_value = query
        query.execute.return_value = SimpleNamespace(data=source[entity])
        queries[entity] = query
        return query
    db.table.side_effect = table
    result = client.get(f"{BASE}?institution_id={FOREIGN}").json()
    assert result["institution_id"] == TENANT
    assert result["records"]["program_courses"] == []
    assert len(result["records"]["course_offerings"]) == 1
    queries["departments"].eq.assert_called_once_with("institution_id", TENANT)
    queries["semesters"].in_.assert_called_once_with("academic_year_id", ["y"])
    queries["sections"].in_.assert_called_once_with("course_offering_id", ["o"])
    user["effective_permissions"] = ["departments.read"]
    result = client.get(BASE).json()
    assert set(result["records"]) == {"departments", "programs"}
    assert result["manageable"] == []


def test_empty_catalogue_contains_no_fabricated_records(api):
    client, db, _, _ = api
    query = db.table.return_value
    for method in ("select", "order", "eq", "range"):
        getattr(query, method).return_value = query
    query.execute.return_value = SimpleNamespace(data=[])
    response = client.get(BASE)
    assert response.status_code == 200
    assert all(rows == [] for rows in response.json()["records"].values())
    assert db.table.call_count == 2


@pytest.mark.parametrize("code", ["42703", "42P01", "PGRST204", "PGRST205"])
def test_catalogue_missing_curriculum_schema_returns_a_safe_update_error(api, code, caplog):
    client, db, _, _ = api

    def table(entity):
        query = MagicMock()
        for method in ("select", "order", "eq", "in_", "range"):
            getattr(query, method).return_value = query
        if entity == "program_courses":
            query.execute.side_effect = APIError({
                "code": code, "message": "column program_courses.semester_id does not exist: PRIVATE_DATABASE_DIAGNOSTIC",
                "details": None, "hint": None,
            })
        else:
            source = {
                "departments": [{"department_id": "d"}],
                "programs": [{"program_id": "p", "department_id": "d"}],
                "courses": [], "academic_years": [{"academic_year_id": "y"}],
                "semesters": [],
            }
            query.execute.return_value = SimpleNamespace(data=source[entity])
        return query

    db.table.side_effect = table
    response = client.get(BASE)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ACADEMIC_SCHEMA_UNAVAILABLE"
    assert "database update" in response.json()["error"]["message"]
    assert "PRIVATE_DATABASE_DIAGNOSTIC" not in response.text
    assert "academic_schema_unavailable" in caplog.text
    assert "20261016010000_academic_curriculum_semester_convergence.sql" in caplog.text


def test_catalogue_other_database_errors_are_not_reported_as_missing_schema(api):
    client, db, _, _ = api
    query = db.table.return_value
    for method in ("select", "order", "eq", "range"):
        getattr(query, method).return_value = query
    query.execute.side_effect = APIError({"code": "XX000", "message": "unrelated database error", "details": None, "hint": None})
    with pytest.raises(APIError):
        client.get(BASE)
