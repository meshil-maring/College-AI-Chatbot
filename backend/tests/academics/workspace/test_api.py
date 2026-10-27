from unittest.mock import patch
from uuid import uuid4

import pytest

from app.schemas.academics.academic_structure import StructureEntity as Entity
from app.services.academics import academic_structure as service
from .test_contracts import payloads
from ..support import TENANT


@pytest.mark.parametrize("entity", list(Entity))
def test_creates_all_structure_entities_with_server_scope(api, entity):
    client, user, _ = api
    record_id = str(uuid4())
    record = {**payloads()[entity], service.repository.PRIMARY_KEYS[entity]: record_id, "institution_id": TENANT}
    with patch.object(service.repository, "manage_record", return_value=record) as writer:
        response = client.post(f"/api/v1/admin/academic-structure/{entity}", json=payloads()[entity])
    assert response.status_code == 201
    assert response.json()["institution_id"] == TENANT
    assert writer.call_args.args[1:3] == (user["user_id"], TENANT)


@pytest.mark.parametrize("role,scope", [("student","institution"),("faculty","institution"),("staff","institution"),("admin","organization"),("admin","platform")])
def test_only_exact_institution_admins_reach_database(api, role, scope):
    client, user, database = api
    user["roles"] = [role]
    user["role_assignments"][0].update(role=role, scope_type=scope)
    assert client.get("/api/v1/admin/academic-structure").status_code == 403
    database.assert_not_called()


def test_revoked_manage_and_read_only_grants_cannot_write(api):
    client, user, database = api
    user["role_assignments"][0]["permissions"] = ["courses.read"]
    assert client.post("/api/v1/admin/academic-structure/academic_sections", json={}).status_code == 403
    database.assert_not_called()


def test_catalogue_excludes_unreadable_entities_and_advertises_no_write_access(api):
    client, user, _ = api
    user["role_assignments"][0]["permissions"] = ["departments.read"]
    with patch.object(service.repository, "list_records", return_value=[]), patch.object(service.repository, "activities", return_value=[]):
        response = client.get("/api/v1/admin/academic-structure")
    assert response.status_code == 200
    assert set(response.json()["records"]) == {"program_semesters", "admission_cohorts"}
    assert response.json()["manageable"] == []


def test_foreign_record_is_not_found_and_cannot_reach_writer(api):
    client, _, _ = api
    with patch.object(service.repository, "get_record", return_value=None), patch.object(service.repository, "manage_record") as writer:
        response = client.patch(f"/api/v1/admin/academic-structure/academic_sections/{uuid4()}", json={"is_active": False})
    assert response.status_code == 404
    writer.assert_not_called()


def test_bad_inputs_and_unknown_entities_are_validation_errors(api):
    client, _, _ = api
    assert client.post("/api/v1/admin/academic-structure/curriculum_versions", json={}).status_code == 422
    assert client.post("/api/v1/admin/academic-structure/unknown", json={}).status_code == 422
