"""Program deletion shares strict authority while preserving its own conflicts."""

from unittest.mock import patch

import pytest

from app.services.academics import academic_setup as service
from ..support import FOREIGN_TENANT, PROGRAM, TENANT, setup_rows
from ..test_api import api


URL = f"/api/v1/admin/academic-setup/programs/{PROGRAM}"


def test_unused_program_uses_server_actor_and_department_derived_tenant(api):
    client, user, _, database = api
    row = setup_rows()["programs"]
    with (
        patch.object(service.repository, "get_record", return_value=row) as lookup,
        patch.object(service.repository, "delete_program", return_value=row) as writer,
    ):
        response = client.delete(URL)
    assert response.status_code == 200
    assert response.json() == row
    assert lookup.call_args.args[1:] == (TENANT, service.AcademicEntity.programs, PROGRAM)
    writer.assert_called_once_with(database.return_value, user["user_id"], TENANT, PROGRAM)


@pytest.mark.parametrize("permissions", [[], ["departments.read"], ["courses.manage"], ["programs.manage"]])
def test_only_existing_department_management_grant_authorizes_program_deletion(api, permissions):
    client, user, _, database = api
    user["role_assignments"][0]["permissions"] = permissions
    assert client.delete(URL).status_code == 403
    database.assert_not_called()


@pytest.mark.parametrize("role,scope", [
    ("student", "institution"), ("faculty", "institution"), ("staff", "institution"),
    ("admin", "organization"), ("admin", "platform"),
])
def test_program_delete_rejects_other_roles_or_scopes(api, role, scope):
    client, user, _, database = api
    user["roles"] = [role]
    user["role_assignments"][0].update(role=role, scope_type=scope)
    assert client.delete(URL).status_code == 403
    database.assert_not_called()


def test_missing_or_foreign_program_is_not_disclosed(api):
    client, _, _, _ = api
    with (
        patch.object(service.repository, "get_record", return_value=None),
        patch.object(service.repository, "delete_program") as writer,
    ):
        response = client.delete(URL)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACADEMIC_NOT_FOUND"
    writer.assert_not_called()


@pytest.mark.parametrize("code,details,label", [
    ("P2002", "program_courses", "subject mappings"),
    ("P2002", "course_offerings", "course offerings"),
    ("P2002", "program_semesters", "program semesters"),
    ("P2002", "curriculum_versions", "curricula"),
    ("P2002", "admission_cohorts", "batches"),
    ("P2002", "private_consumer", "records"), ("23503", None, "records"),
])
def test_program_dependencies_return_safe_conflicts(api, code, details, label):
    client, _, _, _ = api
    failure = Exception("Private database error")
    failure.code, failure.details = code, details
    with (
        patch.object(service.repository, "get_record", return_value=setup_rows()["programs"]),
        patch.object(service.repository, "delete_program", side_effect=failure),
    ):
        response = client.delete(URL)
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "PROGRAM_IN_USE"
    assert f"linked {label}" in error["message"]
    assert "inactive" in error["message"]
    assert "private_consumer" not in error["message"]
    assert "Private database" not in error["message"]


@pytest.mark.parametrize("row", [
    None, {}, {"program_id": PROGRAM, "institution_id": FOREIGN_TENANT},
    {"program_id": "wrong-id", "institution_id": TENANT},
])
def test_program_response_must_match_verified_id_and_tenant(api, row):
    client, _, _, _ = api
    with (
        patch.object(service.repository, "get_record", return_value=setup_rows()["programs"]),
        patch.object(service.repository, "delete_program", return_value=row),
    ):
        assert client.delete(URL).status_code == 500


def test_program_schema_absence_and_bad_ids_fail_closed(api):
    client, _, _, _ = api
    failure = Exception("RPC missing")
    failure.code = "PGRST202"
    with (
        patch.object(service.repository, "get_record", return_value=setup_rows()["programs"]),
        patch.object(service.repository, "delete_program", side_effect=failure),
    ):
        response = client.delete(URL)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ACADEMIC_SCHEMA_UNAVAILABLE"
    assert client.delete("/api/v1/admin/academic-setup/programs/bad-id").status_code == 422
