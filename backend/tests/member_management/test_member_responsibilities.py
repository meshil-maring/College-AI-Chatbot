"""Class In-Charge and Subject Coordinator: contracts, service, routes, migration."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
from app.api.admin.members import responsibilities as routes
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.schemas.admin.member_responsibilities import MemberResponsibilityAssign
from app.services.admin import member_responsibilities as service

INST_A = UUID("40000000-0000-0000-0000-000000000001")
FACULTY = "30000000-0000-0000-0000-000000000001"
TARGET = "60000000-0000-0000-0000-000000000001"
RECORD = "70000000-0000-0000-0000-000000000001"
ADMIN = {"user_id": "10000000-0000-0000-0000-000000000001", "institution_id": str(INST_A)}
MIGRATION = Path(__file__).resolve().parents[3] / "supabase/migrations/20261129010000_member_responsibilities.sql"
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def assignment(**changes) -> MemberResponsibilityAssign:
    return MemberResponsibilityAssign(**{"faculty_user_id": FACULTY, "responsibility": "class_in_charge",
                                         "target_id": TARGET, **changes})


def test_contract_accepts_only_the_two_responsibilities_and_no_tenant() -> None:
    assert assignment(responsibility="subject_coordinator").responsibility == "subject_coordinator"
    for bad in ({"responsibility": "hod"}, {"institution_id": str(INST_A)},
                {"planned_end_on": str(date.today() - timedelta(days=1))}):
        with pytest.raises(ValidationError):
            assignment(**bad)


def test_assign_reports_new_and_repeated_appointments() -> None:
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.repo, "assign", return_value={"responsibility_id": RECORD, "already_applied": False}) as write:
        result = service.assign(ADMIN, INST_A, assignment())
    assert result.message == "Class In-Charge assigned." and not result.already_applied
    kwargs = write.call_args.kwargs
    assert (kwargs["institution_id"], kwargs["responsibility"], str(kwargs["target_id"])) == (
        INST_A, "class_in_charge", TARGET)
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.repo, "assign", return_value={"responsibility_id": RECORD, "already_applied": True}):
        assert service.assign(ADMIN, INST_A, assignment()).already_applied


@pytest.mark.parametrize("sqlstate,status,code", [
    ("P1301", 422, "RESPONSIBILITY_TARGET_INVALID"), ("P1302", 422, "RESPONSIBILITY_FACULTY_INVALID"),
    ("22023", 422, "RESPONSIBILITY_TERM_INVALID"), ("P0002", 404, "RESPONSIBILITY_NOT_FOUND"),
    ("42501", 403, "FORBIDDEN"), ("XX000", 502, "RESPONSIBILITY_WRITE_FAILED"),
])
def test_database_errors_become_safe_api_errors(sqlstate, status, code) -> None:
    failure = Exception("database")
    failure.code = sqlstate
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.repo, "end", side_effect=failure):
        with pytest.raises(AppError) as caught:
            service.end(ADMIN, INST_A, UUID(RECORD))
    assert (caught.value.status_code, caught.value.code) == (status, code)


def test_listing_parses_current_and_ended_rows() -> None:
    rows = [{"responsibility_id": RECORD, "responsibility": "subject_coordinator", "faculty_user_id": FACULTY,
             "faculty_name": "Ada", "course_id": TARGET, "target_code": "CS201", "target_name": "Databases",
             "starts_on": "2026-07-01", "planned_end_on": None, "ended_at": None, "is_current": True}]
    with patch.object(service, "get_admin_client", return_value=object()), \
            patch.object(service.repo, "list_responsibilities", return_value=rows):
        listed = service.list_responsibilities(ADMIN, INST_A)
    assert listed.total == 1 and listed.responsibilities[0].target_code == "CS201"


def test_routes_have_policies_and_take_the_institution_from_the_administrator() -> None:
    assert _ADMIN_ROUTE_PERMISSIONS[("GET", "/admin/memberships/responsibilities")] == ("users.read",)
    assert _ADMIN_ROUTE_PERMISSIONS[("POST", "/admin/memberships/responsibilities")] == ("users.update",)
    assert ("POST", "/admin/memberships/responsibilities/{responsibility_id}/end") in _ADMIN_ROUTE_PERMISSIONS
    body = assignment()
    with patch.object(routes.common, "required_institution", return_value=INST_A) as scope, \
            patch.object(routes.member_responsibilities, "assign", return_value="saved") as assign:
        assert routes.assign_member_responsibility(body, ADMIN) == "saved"
    scope.assert_called_once_with(ADMIN)
    assign.assert_called_once_with(ADMIN, INST_A, body)


@pytest.mark.parametrize("role", ["staff", "faculty", "student"])
def test_non_admins_cannot_manage_responsibilities(role) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": ADMIN["user_id"], "auth_user_id": "70000000-0000-0000-0000-000000000009",
        "roles": [role], "status": "active", "role_assignments": [],
    }
    assert client.get("/api/v1/admin/memberships/responsibilities").status_code == 403
    response = client.post("/api/v1/admin/memberships/responsibilities", json=assignment().model_dump(mode="json"))
    assert response.status_code == 403


def test_migration_keeps_one_current_holder_and_only_service_role_access() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert len(sql.splitlines()) <= 250
    assert "ON public.member_responsibilities (academic_section_id)" in sql
    assert "ON public.member_responsibilities (course_id)" in sql
    assert "FROM PUBLIC, anon, authenticated, service_role" in sql
    for name in ("read_member_responsibilities", "assign_member_responsibility", "end_member_responsibility"):
        function = sql.split(f"FUNCTION public.{name}(", 1)[1].split("$$;", 1)[0]
        assert "phase81_assert_institution_admin(p_actor, p_tenant)" in function, name
    assign = sql.split("FUNCTION public.assign_member_responsibility(", 1)[1].split("$$;", 1)[0]
    assert "transfer_is_active_faculty(p_faculty, p_tenant)" in assign
    assert "d.institution_id = p_tenant" in assign and "INSERT INTO public.admin_audit_log" in assign
