"""HTTP workflow covers setup in dependency order using the supplied model."""
from unittest.mock import patch

import pytest

from app.repositories.academics.academic_setup import PRIMARY_KEYS
from app.schemas.academics.academic_setup import AcademicEntity as Entity
from app.services.academics import academic_setup as service
from .support import SETUP_PERMISSIONS, TENANT, setup_rows
from .test_api import api


def test_full_setup_create_catalogue_and_partial_update(api):
    client, user, _, _ = api
    user["role_assignments"][0]["permissions"] = SETUP_PERMISSIONS
    templates = setup_rows()
    stored = {entity: [] for entity in Entity}
    def lookup(db, tenant, entity, identifier):
        assert tenant == TENANT
        return next((row for row in stored[entity] if row[PRIMARY_KEYS[entity]] == str(identifier)), None)
    def write(db, actor, tenant, entity, identifier, fields):
        assert tenant == TENANT and actor == user["user_id"]
        row = {**templates[entity], **fields}
        if not identifier:
            stored[entity].append(row)
        return {key:value for key,value in row.items() if key != "institution_id"}
    with patch.object(service.repository, "get_record", side_effect=lookup), patch.object(
        service.repository, "list_records", side_effect=lambda db, tenant, entity: stored[entity]
    ), patch.object(service.repository, "manage_record", side_effect=write) as writer:
        for entity in Entity:
            payload = {key:value for key,value in templates[entity].items() if key not in {PRIMARY_KEYS[entity], "institution_id"}}
            response = client.post(f"/api/v1/admin/academic-setup/{entity}", json=payload)
            assert response.status_code == 201, response.text
            assert response.json()["institution_id"] == TENANT
        catalogue = client.get("/api/v1/admin/academic-setup").json()
        assert set(catalogue["records"]) == set(Entity)
        assert all(len(rows)==1 for rows in catalogue["records"].values())
        section = templates["sections"]
        response = client.patch(f"/api/v1/admin/academic-setup/sections/{section['section_id']}", json={"capacity":25})
        assert response.status_code == 200
        assert writer.call_args.args[-1] == {"capacity":25}


@pytest.mark.parametrize("entity", ["subjects", "study_semesters", "class_sections"])
def test_superseded_entity_routes_are_rejected(api, entity):
    client, _, _, database = api
    assert client.post(f"/api/v1/admin/academic-setup/{entity}", json={}).status_code == 422
    database.assert_not_called()


def test_course_read_grant_covers_only_export_course_resources(api):
    client, user, _, _ = api
    user["role_assignments"][0]["permissions"] = ["courses.read"]
    with patch.object(service.repository, "list_records", return_value=[]):
        body = client.get("/api/v1/admin/academic-setup").json()
    assert set(body["records"]) == {"courses", "program_courses", "course_offerings", "sections"}
    assert body["manageable"] == []
