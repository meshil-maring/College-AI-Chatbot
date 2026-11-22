"""Employee profile, extra department and account status services."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.schemas.admin.admin_memberships import MembershipRoster, MembershipRosterEntry
from app.schemas.admin.member_profiles import MemberAdditionalDepartmentsWrite, MemberProfileWrite
from app.services.admin import member_profiles as service
from app.services.admin import member_status

INST_A = UUID("40000000-0000-0000-0000-000000000001")
INST_B = UUID("40000000-0000-0000-0000-000000000002")
USER = UUID("30000000-0000-0000-0000-000000000001")
DEPT = "60000000-0000-0000-0000-000000000001"
ACTOR = {"user_id": "10000000-0000-0000-0000-000000000001"}
FACULTY = {"common": {"employee_id": "EMP-1", "designation": "Professor", "joining_date": "2026-01-05"},
           "faculty": {"employment_type": "permanent", "employment_start_date": "2026-01-05"}}


def grants(role: str, tenant: UUID = INST_A) -> list[dict]:
    return [{"scope_type": "institution", "scope_id": str(tenant), "roles": {"name": role}}]


def database_error(code: str) -> Exception:
    error = Exception("database")
    error.code = code
    return error


@pytest.fixture
def db():
    with (
        patch.object(service, "get_admin_client", return_value=object()),
        patch.object(service.membership_repo, "list_user_grants", return_value=grants("faculty")),
        patch.object(service.repo, "save_profile") as save,
    ):
        yield save


def test_save_sends_the_flat_profile_for_the_members_role(db) -> None:
    result = service.save_profile(ACTOR, INST_A, USER, MemberProfileWrite(**FACULTY))
    assert result.role == "faculty"
    kwargs = db.call_args.kwargs
    assert kwargs["institution_id"] == INST_A and kwargs["actor_id"] == ACTOR["user_id"]
    assert set(kwargs["profile"]) == {"common", "faculty"}


def test_save_rejects_details_for_another_role_before_writing(db) -> None:
    staff = {"common": FACULTY["common"], "staff": {
        "staff_category": "library", "employment_type": "permanent", "employment_start_date": "2026-01-05",
        "responsibilities": ["Issue desk"]}}
    with pytest.raises(AppError) as caught:
        service.save_profile(ACTOR, INST_A, USER, MemberProfileWrite(**staff))
    assert caught.value.code == "PROFILE_ROLE_MISMATCH"
    db.assert_not_called()


def test_member_of_another_institution_is_not_found(db) -> None:
    with patch.object(service.membership_repo, "list_user_grants", return_value=grants("faculty", INST_B)):
        with pytest.raises(AppError) as caught:
            service.save_profile(ACTOR, INST_A, USER, MemberProfileWrite(**FACULTY))
    assert caught.value.status_code == 404
    db.assert_not_called()


@pytest.mark.parametrize("sqlstate,status,code", [
    ("P1204", 409, "EMPLOYEE_ID_IN_USE"), ("P1201", 422, "DEPARTMENT_INVALID"),
    ("23514", 422, "PROFILE_INVALID"), ("42501", 403, "FORBIDDEN"), ("XX000", 502, "MEMBER_PROFILE_WRITE_FAILED"),
])
def test_database_errors_become_safe_api_errors(db, sqlstate, status, code) -> None:
    db.side_effect = database_error(sqlstate)
    with pytest.raises(AppError) as caught:
        service.save_profile(ACTOR, INST_A, USER, MemberProfileWrite(**FACULTY))
    assert (caught.value.status_code, caught.value.code) == (status, code)


def test_profile_view_derives_employment_status_and_departments(db) -> None:
    ended = (date.today() - timedelta(days=1)).isoformat()
    faculty_row = {"user_id": str(USER), "employment_type": "contractual",
                   "employment_start_date": "2025-01-01", "contract_end_date": ended}
    label = {"department_id": DEPT, "departments": {"code": "CSE", "name": "Computer Science"}}
    with (
        patch.object(service.repo, "list_common", return_value=[{"user_id": str(USER), **FACULTY["common"]}]),
        patch.object(service.repo, "list_faculty", return_value=[faculty_row]),
        patch.object(service.repo, "list_additional", return_value=[label]),
        patch.object(service.department_repo, "list_assignments",
                     return_value=[{"user_id": str(USER), **label}, {"user_id": "other", **label}]),
    ):
        view = service.get_profile(INST_A, USER)
    assert view.employment_status == "contract_ended" and view.staff is None
    assert view.common.employee_id == "EMP-1" and view.faculty.employment_type == "contractual"
    assert view.primary_department.code == "CSE" and len(view.additional_departments) == 1


def test_profile_view_without_details_is_not_set(db) -> None:
    with (
        patch.object(service.repo, "list_common", return_value=[]),
        patch.object(service.repo, "list_faculty", return_value=[]),
        patch.object(service.repo, "list_additional", return_value=[]),
        patch.object(service.department_repo, "list_assignments", return_value=[]),
    ):
        view = service.get_profile(INST_A, USER)
    assert (view.common, view.faculty, view.employment_status) == (None, None, "not_set")


def test_additional_departments_are_deduplicated_and_returned_with_labels(db) -> None:
    label = {"department_id": DEPT, "departments": {"code": "ME", "name": "Mechanical"}}
    with (
        patch.object(service.repo, "set_additional_departments") as write,
        patch.object(service.repo, "list_additional", return_value=[label]),
    ):
        result = service.set_additional_departments(
            ACTOR, INST_A, USER, MemberAdditionalDepartmentsWrite(department_ids=[DEPT, DEPT]))
    assert write.call_args.kwargs["department_ids"] == [UUID(DEPT)]
    assert [item.name for item in result.additional_departments] == ["Mechanical"]


def test_roster_shows_the_current_roles_employment_type() -> None:
    roster = MembershipRoster(total=1, members=[MembershipRosterEntry(
        user_id=USER, name="Ada", email="ada@example.com", role="staff", status="active")])
    with (
        patch.object(service, "get_admin_client", return_value=object()),
        patch.object(service.repo, "list_common", return_value=[{"user_id": str(USER), "employee_id": "E1",
                                                                 "designation": "Clerk"}]),
        patch.object(service.repo, "list_staff", return_value=[{"user_id": str(USER), "employment_type": "temporary"}]),
        patch.object(service.repo, "list_faculty", return_value=[{"user_id": str(USER), "employment_type": "guest"}]),
        patch.object(service.repo, "list_additional", return_value=[
            {"user_id": str(USER), "department_id": DEPT, "departments": {"code": "ME", "name": "Mechanical"}}]),
    ):
        member = service.with_profiles(INST_A, roster).members[0]
    assert (member.employee_id, member.designation, member.employment_type) == ("E1", "Clerk", "temporary")
    assert member.additional_department_names == ["Mechanical"]


@pytest.mark.parametrize("current,target,action", [
    ("active", "suspended", "staff_suspended"),
    ("suspended", "active", "staff_reactivated"),
    ("suspended", "deactivated", "staff_deactivated"),
])
def test_status_transitions_update_users_and_audit(current, target, action) -> None:
    update = MagicMock(return_value=True)
    with (
        patch.object(member_status, "get_admin_client", return_value=object()),
        patch.object(member_status.repo, "get_user", return_value={"id": str(USER), "status": current}),
        patch.object(member_status.repo, "list_user_grants", return_value=grants("staff")),
        patch.object(member_status.repo, "set_user_status", update),
        patch.object(member_status, "record_admin_action") as audit,
    ):
        result = member_status.set_status(ACTOR, INST_A, USER, target)
    assert result.status == target and update.call_args.kwargs["status"] == target
    assert audit.call_args.args[1].action == action


@pytest.mark.parametrize("current,target", [("deactivated", "suspended"), ("inactive", "suspended")])
def test_only_active_members_can_be_suspended(current, target) -> None:
    with (
        patch.object(member_status, "get_admin_client", return_value=object()),
        patch.object(member_status.repo, "get_user", return_value={"id": str(USER), "status": current}),
        patch.object(member_status.repo, "list_user_grants", return_value=grants("faculty")),
        patch.object(member_status.repo, "set_user_status") as update,
    ):
        with pytest.raises(AppError) as caught:
            member_status.set_status(ACTOR, INST_A, USER, target)
    assert caught.value.code == "MEMBERSHIP_STATUS_CONFLICT"
    update.assert_not_called()
