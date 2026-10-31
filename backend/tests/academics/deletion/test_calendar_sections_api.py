"""Delete authority, current-period protection and tenant-safe conflicts."""

from unittest.mock import patch

import pytest

from app.services.academics import academic_setup, academic_structure
from ..support import YEAR, SEMESTER, SECTION, TENANT, FOREIGN_TENANT
from ..test_api import api as setup_api
from ..workspace.conftest import api as structure_api


@pytest.fixture(params=["academic_years", "semesters", "academic_sections"])
def target(request):
    entity = request.param
    section = entity == "academic_sections"
    state = request.getfixturevalue("structure_api" if section else "setup_api")
    client, user = state[:2]
    service = academic_structure if section else academic_setup
    permission = {"academic_years": "academic_years.manage", "semesters": "semesters.manage",
                  "academic_sections": "courses.manage"}[entity]
    user["role_assignments"][0]["permissions"] = [permission]
    identifier = {"academic_years": YEAR, "semesters": SEMESTER, "academic_sections": SECTION}[entity]
    key = entity.removesuffix("s") + "_id"
    row = {key: identifier, "institution_id": TENANT, "name": "Unused record", "code": "QA"}
    if not section:
        row["is_current"] = False
    return {
        "client": client, "user": user, "database": state[-1], "service": service,
        "entity": entity, "id": identifier, "row": row,
        "writer": "delete_section" if section else "delete_period",
        "url": f"/api/v1/admin/{'academic-structure' if section else 'academic-setup'}/{entity}/{identifier}",
        "code": {"academic_years": "ACADEMIC_YEAR", "semesters": "SEMESTER", "academic_sections": "SECTION"}[entity],
    }


def test_deletes_only_with_server_actor_and_tenant(target):
    repo = target["service"].repository
    with (patch.object(repo, "get_record", return_value=target["row"]),
          patch.object(repo, target["writer"], return_value=target["row"]) as writer):
        response = target["client"].delete(target["url"])
    assert response.status_code == 200
    assert response.json() == target["row"]
    args = writer.call_args.args
    assert args[:3] == (target["database"].return_value, target["user"]["user_id"], TENANT)
    assert args[-1] == target["id"]
    if target["entity"] != "academic_sections":
        assert args[3] == target["entity"]


@pytest.mark.parametrize("role,scope", [("student", "institution"), ("faculty", "institution"),
    ("staff", "institution"), ("admin", "organization"), ("admin", "platform")])
def test_other_roles_and_scopes_cannot_delete(target, role, scope):
    target["user"]["roles"] = [role]
    target["user"]["role_assignments"][0].update(role=role, scope_type=scope)
    assert target["client"].delete(target["url"]).status_code == 403
    target["database"].assert_not_called()


@pytest.mark.parametrize("permissions", [[], ["departments.manage"], ["academic_years.read"]])
def test_wrong_or_revoked_manage_grants_fail_before_database(target, permissions):
    target["user"]["role_assignments"][0]["permissions"] = permissions
    assert target["client"].delete(target["url"]).status_code == 403
    target["database"].assert_not_called()


def test_foreign_and_missing_records_are_not_disclosed(target):
    repo = target["service"].repository
    with (patch.object(repo, "get_record", return_value=None),
          patch.object(repo, target["writer"]) as writer):
        response = target["client"].delete(target["url"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ACADEMIC_NOT_FOUND"
    writer.assert_not_called()


@pytest.mark.parametrize("code,details", [("P2003", "student_semester_registrations"),
    ("P2003", "private_table"), ("23503", None)])
def test_hidden_or_concurrent_links_return_safe_conflicts(target, code, details):
    failure = Exception("Private SQL details")
    failure.code, failure.details = code, details
    repo = target["service"].repository
    with (patch.object(repo, "get_record", return_value=target["row"]),
          patch.object(repo, target["writer"], side_effect=failure)):
        response = target["client"].delete(target["url"])
    error = response.json()["error"]
    assert response.status_code == 409
    assert error["code"] == target["code"] + "_IN_USE"
    assert "inactive" in error["message"]
    assert "private_table" not in error["message"]
    assert "Private SQL details" not in error["message"]


@pytest.mark.parametrize("target", ["academic_years", "semesters"], indirect=True)
def test_current_year_or_semester_cannot_reach_delete_rpc(target):
    row = {**target["row"], "is_current": True}
    repo = target["service"].repository
    with (patch.object(repo, "get_record", return_value=row),
          patch.object(repo, target["writer"]) as writer):
        response = target["client"].delete(target["url"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACADEMIC_CURRENT_PERIOD"
    writer.assert_not_called()


@pytest.mark.parametrize("target", ["academic_years", "semesters"], indirect=True)
def test_database_current_flag_race_is_also_a_conflict(target):
    failure = Exception("Current flag changed concurrently")
    failure.code = "P2004"
    repo = target["service"].repository
    with (patch.object(repo, "get_record", return_value=target["row"]),
          patch.object(repo, target["writer"], side_effect=failure)):
        response = target["client"].delete(target["url"])
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACADEMIC_CURRENT_PERIOD"


@pytest.mark.parametrize("changes", [{"institution_id": FOREIGN_TENANT}, {"institution_id": None}])
def test_deleted_response_must_match_verified_tenant(target, changes):
    repo = target["service"].repository
    with (patch.object(repo, "get_record", return_value=target["row"]),
          patch.object(repo, target["writer"], return_value={**target["row"], **changes})):
        assert target["client"].delete(target["url"]).status_code == 500


def test_missing_rpc_fails_closed(target):
    failure = Exception("Not deployed")
    failure.code = "PGRST202"
    repo = target["service"].repository
    with (patch.object(repo, "get_record", return_value=target["row"]),
          patch.object(repo, target["writer"], side_effect=failure)):
        response = target["client"].delete(target["url"])
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ACADEMIC_SCHEMA_UNAVAILABLE"
