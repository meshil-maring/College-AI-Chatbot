"""HTTP regression using real scope dependencies and exclusively mocked clients."""

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.academics.academic_setup import router
from app.core.errors import AppError, app_error_handler
from app.core.security import get_current_user
from app.repositories.platform import tenancy
from app.services.academics import academic_setup as service
from app.services.auth import authorization
from .support import DEPARTMENT, FOREIGN_TENANT, ORGANIZATION, PROGRAM, TENANT, YEAR, principal


@pytest.fixture
def api():
    application = FastAPI()
    application.add_exception_handler(AppError, app_error_handler)
    application.include_router(router, prefix="/api/v1")
    user = principal()
    application.dependency_overrides[get_current_user] = lambda: user
    with (
        patch.object(authorization, "get_admin_client", return_value=MagicMock()),
        patch.object(tenancy, "get_institution_by_id", return_value={
            "institution_id": TENANT, "status": "active", "is_active": True,
        }) as lifecycle,
        patch.object(service.repository, "get_institution_lifecycle", return_value={
            "institution_id": TENANT, "organization_id": ORGANIZATION,
            "status": "active", "is_active": True,
        }),
        patch.object(service.repository, "get_organization_lifecycle", return_value={
            "organization_id": ORGANIZATION, "status": "active",
        }),
        patch.object(service, "get_admin_client", return_value=MagicMock()) as database,
        TestClient(application, raise_server_exceptions=True) as client,
    ):
        yield client, user, lifecycle, database


@pytest.mark.parametrize("role,scope", [
    ("staff", "institution"), ("faculty", "institution"), ("student", "institution"),
    ("admin", "organization"), ("admin", "platform"),
])
def test_only_institution_admins_reach_academic_database(api, role, scope):
    client, user, _, database = api
    user["roles"] = [role]
    user["role_assignments"][0].update(role=role, scope_type=scope)
    assert client.get("/api/v1/admin/academic-setup").status_code == 403
    database.assert_not_called()


def test_inactive_institution_denied_before_academic_queries(api):
    client, _, lifecycle, database = api
    lifecycle.return_value = {"status": "suspended", "is_active": False}
    response = client.get("/api/v1/admin/academic-setup")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "TENANT_INACTIVE"
    database.assert_not_called()


def test_revoked_exact_scope_grants_cannot_fall_back_to_role_defaults(api):
    client, user, _, database = api
    user["role_assignments"][0]["permissions"] = []
    response = client.get("/api/v1/admin/academic-setup")
    assert response.status_code == 403
    database.assert_not_called()


def test_foreign_institution_grant_cannot_supply_own_scope_permission(api):
    client, user, _, database = api
    user["role_assignments"][0]["permissions"] = []
    user["role_assignments"].append({
        "role": "staff", "scope_type": "institution", "scope_id": FOREIGN_TENANT,
        "permissions": ["departments.read"], "is_active": True,
    })
    user["roles"].append("staff")
    assert client.get("/api/v1/admin/academic-setup").status_code == 403
    database.assert_not_called()


@pytest.mark.parametrize("body", [
    {"name": "CSE", "code": "CSE", "institution_id": FOREIGN_TENANT},
    {"name": "CSE", "code": "CSE", "actor_user_id": "spoofed"},
    {"name": "CSE", "code": " "},
])
def test_invalid_payload_never_reaches_writer(api, body):
    client, _, _, database = api
    with patch.object(service.repository, "manage_record") as writer:
        response = client.post("/api/v1/admin/academic-setup/departments", json=body)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][0] == "body"
    writer.assert_not_called()
    database.assert_not_called()


def test_foreign_record_update_fails_without_disclosing_existence(api):
    client, _, _, _ = api
    with (
        patch.object(service.repository, "get_record", return_value=None),
        patch.object(service.repository, "manage_record") as writer,
    ):
        response = client.patch(
            f"/api/v1/admin/academic-setup/departments/{DEPARTMENT}",
            json={"is_active": False},
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACADEMIC_NOT_FOUND"
    writer.assert_not_called()


@pytest.mark.parametrize("organization", [None, {"status": "suspended"}, {"status": "pending"}])
@pytest.mark.parametrize("method", ["get", "post"])
def test_inactive_or_missing_parent_organization_blocks_academic_queries(api, organization, method):
    client, _, _, _ = api
    with (
        patch.object(service.repository, "get_organization_lifecycle", return_value=organization),
        patch.object(service.repository, "list_records") as listing,
        patch.object(service.repository, "manage_record") as writer,
    ):
        response = (
            client.get("/api/v1/admin/academic-setup") if method == "get" else
            client.post("/api/v1/admin/academic-setup/departments", json={"name": "CSE", "code": "CSE"})
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ORGANIZATION_INACTIVE"
    listing.assert_not_called()
    writer.assert_not_called()


@pytest.mark.parametrize("organization_id", [None, FOREIGN_TENANT])
@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_or_mismatched_grant_organization_blocks_academic_queries(api, organization_id, method):
    client, user, _, _ = api
    user["role_assignments"][0]["scope_organization_id"] = organization_id
    with (
        patch.object(service.repository, "list_records") as listing,
        patch.object(service.repository, "manage_record") as writer,
    ):
        response = (
            client.get("/api/v1/admin/academic-setup") if method == "get" else
            client.post("/api/v1/admin/academic-setup/departments", json={"name": "CSE", "code": "CSE"})
        )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    listing.assert_not_called()
    writer.assert_not_called()


def test_stage_one_example_creation_and_catalogue(api):
    """Validate CSE -> B.Tech CSE and 2026–2027; later hierarchy is out of stage."""
    client, _, _, _ = api
    records = {"departments": [], "programs": [], "academic_years": []}
    identifiers = {"departments": DEPARTMENT, "programs": PROGRAM, "academic_years": YEAR}
    keys = {"departments": "department_id", "programs": "program_id", "academic_years": "academic_year_id"}

    def write(_db, _actor, tenant, entity, _record_id, payload):
        assert tenant == TENANT
        row = {**payload, keys[entity]: identifiers[entity], "institution_id": tenant, "is_active": True}
        records[entity].append(row)
        return row

    def lookup(_db, tenant, entity, record_id):
        assert tenant == TENANT
        return next((row for row in records[entity] if row[keys[entity]] == record_id), None)

    with (
        patch.object(service.repository, "manage_record", side_effect=write),
        patch.object(service.repository, "get_record", side_effect=lookup),
        patch.object(service.repository, "list_records", side_effect=lambda db, tenant, entity: records[entity]),
    ):
        department = client.post("/api/v1/admin/academic-setup/departments", json={
            "name": "Computer Science and Engineering", "code": "CSE",
        })
        assert department.status_code == 201
        program = client.post("/api/v1/admin/academic-setup/programs", json={
            "name": "B.Tech Computer Science Engineering", "code": "BTCSE",
            "department_id": department.json()["department_id"],
            "degree_type": "B.Tech", "duration_years": 4,
        })
        assert program.status_code == 201
        year = client.post("/api/v1/admin/academic-setup/academic_years", json={
            "name": "2026–2027", "code": "2026-27",
            "start_date": "2026-07-01", "end_date": "2027-06-30", "is_current": True,
        })
        assert year.status_code == 201
        catalogue = client.get("/api/v1/admin/academic-setup")
    assert catalogue.status_code == 200
    body = catalogue.json()
    assert body["institution_id"] == TENANT
    assert len(body["manageable"]) == 3
    assert body["records"]["programs"][0]["department_id"] == DEPARTMENT
    assert body["records"]["academic_years"][0]["name"] == "2026–2027"
