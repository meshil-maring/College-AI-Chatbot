"""Deletion must retain exact scoped authorization and safe conflict responses."""

from unittest.mock import patch

import pytest

from app.services.academics import academic_setup as service
from ..support import DEPARTMENT, FOREIGN_TENANT, TENANT, setup_rows
from ..test_api import api


URL = f"/api/v1/admin/academic-setup/departments/{DEPARTMENT}"


def test_unused_department_deletion_uses_authenticated_actor_and_tenant(api):
    client, user, _, database = api
    row = setup_rows()["departments"]
    with (
        patch.object(service.repository, "get_record", return_value=row) as lookup,
        patch.object(service.repository, "delete_department", return_value=row) as writer,
    ):
        response = client.delete(URL)
    assert response.status_code == 200
    assert response.json() == row
    assert lookup.call_args.args[1:] == (TENANT, service.AcademicEntity.departments, DEPARTMENT)
    writer.assert_called_once_with(database.return_value, user["user_id"], TENANT, DEPARTMENT)


@pytest.mark.parametrize("role,scope", [
    ("student", "institution"), ("faculty", "institution"), ("staff", "institution"),
    ("admin", "organization"), ("admin", "platform"),
])
def test_other_roles_and_scopes_cannot_delete(api, role, scope):
    client, user, _, database = api
    user["roles"] = [role]
    user["role_assignments"][0].update(role=role, scope_type=scope)
    assert client.delete(URL).status_code == 403
    database.assert_not_called()


@pytest.mark.parametrize("permissions", [[], ["departments.read"], ["courses.manage"]])
def test_manage_permission_is_required_before_database_access(api, permissions):
    client, user, _, database = api
    user["role_assignments"][0]["permissions"] = permissions
    assert client.delete(URL).status_code == 403
    database.assert_not_called()


def test_foreign_or_missing_department_is_not_found_without_writing(api):
    client, _, _, _ = api
    with (
        patch.object(service.repository, "get_record", return_value=None),
        patch.object(service.repository, "delete_department") as writer,
    ):
        response = client.delete(URL)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACADEMIC_NOT_FOUND"
    writer.assert_not_called()


@pytest.mark.parametrize("organization", [None, {"status": "suspended"}])
def test_parent_lifecycle_prevents_deletion(api, organization):
    client, _, _, _ = api
    with (
        patch.object(service.repository, "get_organization_lifecycle", return_value=organization),
        patch.object(service.repository, "delete_department") as writer,
    ):
        assert client.delete(URL).status_code == 403
    writer.assert_not_called()


@pytest.mark.parametrize("code,details,label", [
    ("P2001", "programs", "programs"), ("P2001", "courses", "subjects"),
    ("P2001", "private_table_name", "records"), ("23503", None, "records"),
])
def test_dependencies_are_safe_conflicts_including_concurrent_fk_writes(api, code, details, label):
    client, _, _, _ = api
    failure = Exception("Internal database text must not be exposed")
    failure.code, failure.details = code, details
    with (
        patch.object(service.repository, "get_record", return_value=setup_rows()["departments"]),
        patch.object(service.repository, "delete_department", side_effect=failure),
    ):
        response = client.delete(URL)
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "DEPARTMENT_IN_USE"
    assert f"linked {label}" in error["message"]
    assert "inactive" in error["message"]
    assert "private_table_name" not in error["message"]
    assert "Internal database" not in error["message"]


def test_missing_migration_fails_closed(api):
    client, _, _, _ = api
    failure = Exception("RPC missing")
    failure.code = "PGRST202"
    with (
        patch.object(service.repository, "get_record", return_value=setup_rows()["departments"]),
        patch.object(service.repository, "delete_department", side_effect=failure),
    ):
        response = client.delete(URL)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ACADEMIC_SCHEMA_UNAVAILABLE"


@pytest.mark.parametrize("row", [None, {}, {"department_id": DEPARTMENT, "institution_id": FOREIGN_TENANT}])
def test_unverified_deletion_response_is_rejected(api, row):
    client, _, _, _ = api
    with (
        patch.object(service.repository, "get_record", return_value=setup_rows()["departments"]),
        patch.object(service.repository, "delete_department", return_value=row),
    ):
        assert client.delete(URL).status_code == 500


def test_invalid_id_and_other_entity_deletion_are_rejected(api):
    client, _, _, database = api
    assert client.delete("/api/v1/admin/academic-setup/departments/invalid").status_code == 422
    assert client.delete(f"/api/v1/admin/academic-setup/courses/{DEPARTMENT}").status_code == 405
    database.assert_not_called()
