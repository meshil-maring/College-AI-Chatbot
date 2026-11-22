"""Administrator-chosen Staff or Faculty role for institution members."""

from unittest.mock import ANY, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.schemas.admin.admin_memberships import MembershipDecisionResult
from app.services.admin import member_departments, member_roles as service

INST_A = UUID("40000000-0000-0000-0000-000000000001")
ADMIN_A = "10000000-0000-0000-0000-000000000001"
USER_A = UUID("20000000-0000-0000-0000-000000000001")
REQUEST_A = UUID("30000000-0000-0000-0000-000000000001")
DEPT_A = UUID("60000000-0000-0000-0000-000000000001")
IDS = {"staff": "role-staff", "faculty": "role-faculty"}
client = TestClient(app, raise_server_exceptions=False)


def _actor() -> dict:
    return {"user_id": ADMIN_A, "institution_id": str(INST_A), "roles": ["admin"]}


def _grant(role: str) -> dict:
    return {"user_id": str(USER_A), "role_id": IDS[role], "roles": {"name": role}}


@pytest.fixture
def db():
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service, "record_admin_action"
    ) as audit, patch.object(service.repo, "role_ids", return_value=IDS), patch.object(
        service.repo, "switch_role", return_value=[{"user_id": str(USER_A)}]
    ) as switch, patch.object(service.repo, "is_current_department_head", return_value=False), patch.object(
        service.repo, "has_direct_staff_grants", return_value=False
    ):
        yield {"audit": audit, "switch": switch}


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize(("current", "target"), [("faculty", "staff"), ("staff", "faculty")])
def test_admin_switches_member_between_staff_and_faculty(db, current: str, target: str) -> None:
    with patch.object(service.repo, "member_grant", return_value=_grant(current)):
        result = service.change_role(_actor(), INST_A, USER_A, target)
    assert result.role == target and not result.already_applied
    assert db["switch"].call_args.kwargs == {
        "institution_id": INST_A, "user_id": USER_A, "from_role_id": IDS[current], "to_role_id": IDS[target],
    }
    assert db["audit"].call_args.args[1].record_data == {"from": current, "to": target}


@pytest.mark.parametrize("role", ["admin", "super_admin", "student", "university_admin"])
def test_only_staff_or_faculty_can_be_chosen(db, role: str) -> None:
    with pytest.raises(AppError) as error:
        service.change_role(_actor(), INST_A, USER_A, role)
    assert error.value.code == "INVALID_MEMBERSHIP_ROLE"
    db["switch"].assert_not_called()


def test_accounts_without_a_member_role_in_this_institution_cannot_be_changed(db) -> None:
    with patch.object(service.repo, "member_grant", return_value=None):
        with pytest.raises(AppError) as error:
            service.change_role(_actor(), INST_A, USER_A, "staff")
    assert error.value.code == "MEMBER_NOT_FOUND"
    db["switch"].assert_not_called()


def test_same_role_is_a_no_op(db) -> None:
    with patch.object(service.repo, "member_grant", return_value=_grant("staff")):
        result = service.change_role(_actor(), INST_A, USER_A, "staff")
    assert result.already_applied
    db["switch"].assert_not_called()


def test_current_head_of_department_cannot_become_staff(db) -> None:
    with patch.object(service.repo, "member_grant", return_value=_grant("faculty")), patch.object(
        service.repo, "is_current_department_head", return_value=True
    ):
        with pytest.raises(AppError) as error:
            service.change_role(_actor(), INST_A, USER_A, "staff")
    assert error.value.code == "MEMBER_IS_DEPARTMENT_HEAD"
    db["switch"].assert_not_called()


def test_staff_with_extra_permissions_cannot_become_faculty(db) -> None:
    with patch.object(service.repo, "member_grant", return_value=_grant("staff")), patch.object(
        service.repo, "has_direct_staff_grants", return_value=True
    ):
        with pytest.raises(AppError) as error:
            service.change_role(_actor(), INST_A, USER_A, "faculty")
    assert error.value.code == "MEMBER_HAS_STAFF_PERMISSIONS"
    db["switch"].assert_not_called()


def test_concurrent_role_change_is_reported(db) -> None:
    db["switch"].return_value = []
    with patch.object(service.repo, "member_grant", return_value=_grant("staff")):
        with pytest.raises(AppError) as error:
            service.change_role(_actor(), INST_A, USER_A, "faculty")
    assert error.value.code == "MEMBER_ROLE_CONFLICT"


def test_approval_uses_the_role_the_admin_chose() -> None:
    row = {"request_id": str(REQUEST_A), "status": "pending", "user_id": str(USER_A), "requested_role": "faculty"}
    set_role = MagicMock(return_value=[row])
    approved = MembershipDecisionResult(request_id=REQUEST_A, status="approved", message="Approved.")
    with patch.object(member_departments, "get_admin_client", return_value=object()), patch.object(
        member_departments.membership_repo, "get_request_for_institution", return_value=row
    ), patch.object(member_departments.repo, "get_department", return_value={
        "department_id": str(DEPT_A), "name": "Admin Office", "code": "AO", "is_active": True,
    }), patch.object(member_departments, "_save") as save, patch.object(
        service.repo, "set_pending_request_role", set_role
    ), patch.object(service, "record_admin_action"), patch.object(
        member_departments.admin_memberships, "decide_request", return_value=approved
    ) as decide:
        save.return_value.message = "Department set to Admin Office."
        member_departments.approve_request(_actor(), INST_A, REQUEST_A, department_id=DEPT_A, reason=None, role="staff")
    set_role.assert_called_once_with(ANY, INST_A, str(REQUEST_A), "staff")
    decide.assert_called_once()


def test_decided_request_role_cannot_be_rewritten(db) -> None:
    row = {"request_id": str(REQUEST_A), "status": "approved", "requested_role": "faculty"}
    with pytest.raises(AppError) as error:
        service.prepare_request_role(object(), _actor(), INST_A, row, "staff")
    assert error.value.code == "MEMBERSHIP_REQUEST_ALREADY_DECIDED"


@pytest.mark.parametrize("role", ["staff", "faculty", "student"])
def test_non_admins_cannot_change_roles(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": ADMIN_A,
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "roles": [role],
        "status": "active",
        "role_assignments": [],
    }
    response = client.put(f"/api/v1/admin/memberships/{USER_A}/role", json={"role": "faculty"})
    assert response.status_code == 403



def test_only_active_direct_grants_block_the_switch_to_faculty() -> None:
    """Revoked grants are history; unticking every permission must unblock the switch."""
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.eq.return_value = query
    query.is_.return_value = query
    query.limit.return_value.execute.return_value.data = []
    assert service.repo.has_direct_staff_grants(client, INST_A, USER_A) is False
    client.table.assert_called_with("user_permission_grants")
    query.is_.assert_called_once_with("revoked_at", "null")
