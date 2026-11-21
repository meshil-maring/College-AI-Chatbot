"""Administrator-chosen departments for Staff and Faculty members."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.schemas.admin.admin_memberships import (
    MembershipDecisionResult,
    MembershipRoster,
    MembershipRosterEntry,
)
from app.services.admin import member_departments as service

INST_A = UUID("40000000-0000-0000-0000-000000000001")
INST_B = UUID("40000000-0000-0000-0000-000000000002")
ADMIN_A = "10000000-0000-0000-0000-000000000001"
USER_A = UUID("20000000-0000-0000-0000-000000000001")
REQUEST_A = UUID("30000000-0000-0000-0000-000000000001")
DEPT_A = UUID("60000000-0000-0000-0000-000000000001")
DEPARTMENT = {
    "department_id": str(DEPT_A),
    "institution_id": str(INST_A),
    "code": "CSE",
    "name": "Computer Science",
    "is_active": True,
}
PENDING = {"status": "pending", "user_id": str(USER_A)}
client = TestClient(app, raise_server_exceptions=False)


def _actor() -> dict:
    return {"user_id": ADMIN_A, "institution_id": str(INST_A), "roles": ["admin"]}


def _grant(role: str, scope: UUID = INST_A) -> dict:
    return {"scope_type": "institution", "scope_id": str(scope), "roles": {"name": role}}


@pytest.fixture
def db():
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service, "record_admin_action"
    ) as audit, patch.object(service.repo, "upsert_assignment") as upsert:
        yield {"audit": audit, "upsert": upsert}


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_assign_saves_department_for_member_of_same_institution(db) -> None:
    with patch.object(service.repo, "get_department", return_value=DEPARTMENT), patch.object(
        service.membership_repo, "list_user_grants", return_value=[_grant("staff")]
    ):
        result = service.assign(_actor(), INST_A, USER_A, DEPT_A)
    assert result.department_name == "Computer Science"
    db["upsert"].assert_called_once()
    assert db["upsert"].call_args.kwargs["institution_id"] == INST_A
    assert db["audit"].call_args.args[1].action == "member.department.assign"


def test_department_from_another_institution_is_rejected(db) -> None:
    with patch.object(service.repo, "get_department", return_value=None):
        with pytest.raises(AppError) as error:
            service.assign(_actor(), INST_A, USER_A, DEPT_A)
    assert error.value.code == "DEPARTMENT_NOT_FOUND"
    db["upsert"].assert_not_called()


def test_inactive_department_is_rejected(db) -> None:
    inactive = {**DEPARTMENT, "is_active": False}
    with patch.object(service.repo, "get_department", return_value=inactive):
        with pytest.raises(AppError) as error:
            service.assign(_actor(), INST_A, USER_A, DEPT_A)
    assert error.value.code == "DEPARTMENT_INACTIVE"
    db["upsert"].assert_not_called()


@pytest.mark.parametrize(
    "grants",
    [[], [_grant("student")], [_grant("admin")], [_grant("staff", INST_B)]],
)
def test_only_staff_or_faculty_of_this_institution_get_a_department(db, grants) -> None:
    with patch.object(service.repo, "get_department", return_value=DEPARTMENT), patch.object(
        service.membership_repo, "list_user_grants", return_value=grants
    ):
        with pytest.raises(AppError) as error:
            service.assign(_actor(), INST_A, USER_A, DEPT_A)
    assert error.value.code == "MEMBER_NOT_FOUND"
    db["upsert"].assert_not_called()


def test_pending_request_cannot_be_approved_without_department(db) -> None:
    decide = MagicMock()
    with patch.object(
        service.membership_repo, "get_request_for_institution", return_value=PENDING
    ), patch.object(service.admin_memberships, "decide_request", decide):
        with pytest.raises(AppError) as error:
            service.approve_request(_actor(), INST_A, REQUEST_A, department_id=None, reason=None)
    assert error.value.code == "DEPARTMENT_REQUIRED"
    decide.assert_not_called()


def test_invalid_department_blocks_approval_before_anything_changes(db) -> None:
    decide = MagicMock()
    with patch.object(
        service.membership_repo, "get_request_for_institution", return_value=PENDING
    ), patch.object(service.repo, "get_department", return_value=None), patch.object(
        service.admin_memberships, "decide_request", decide
    ):
        with pytest.raises(AppError):
            service.approve_request(_actor(), INST_A, REQUEST_A, department_id=DEPT_A, reason=None)
    decide.assert_not_called()
    db["upsert"].assert_not_called()


def test_approval_places_member_in_chosen_department(db) -> None:
    approved = MembershipDecisionResult(request_id=REQUEST_A, status="approved", message="Approved.")
    with patch.object(
        service.membership_repo, "get_request_for_institution", return_value=PENDING
    ), patch.object(service.repo, "get_department", return_value=DEPARTMENT), patch.object(
        service.admin_memberships, "decide_request", return_value=approved
    ):
        result = service.approve_request(_actor(), INST_A, REQUEST_A, department_id=DEPT_A, reason=None)
    assert result.message == "Approved. Department set to Computer Science."
    assert db["upsert"].call_args.kwargs["user_id"] == str(USER_A)


def test_retrying_sign_in_setup_needs_no_department(db) -> None:
    approved = MembershipDecisionResult(request_id=REQUEST_A, status="approved", message="Already.")
    with patch.object(
        service.membership_repo,
        "get_request_for_institution",
        return_value={"status": "approved", "user_id": str(USER_A)},
    ), patch.object(service.admin_memberships, "decide_request", return_value=approved):
        result = service.approve_request(_actor(), INST_A, REQUEST_A, department_id=None, reason=None)
    assert result.message == "Already."
    db["upsert"].assert_not_called()


def test_roster_shows_each_member_department() -> None:
    roster = MembershipRoster(
        total=2,
        members=[
            MembershipRosterEntry(user_id=USER_A, name="A", email="a@x", role="staff", status="active"),
            MembershipRosterEntry(user_id=UUID(int=9), name="B", email="b@x", role="faculty", status="active"),
        ],
    )
    rows = [
        {
            "user_id": str(USER_A),
            "department_id": str(DEPT_A),
            "departments": {"code": "CSE", "name": "Computer Science"},
        }
    ]
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "list_assignments", return_value=rows
    ):
        result = service.with_departments(INST_A, roster)
    assert result.members[0].department_name == "Computer Science"
    assert result.members[1].department_id is None


@pytest.mark.parametrize("role", ["staff", "faculty", "student"])
def test_non_admins_cannot_change_a_member_department(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": ADMIN_A,
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "roles": [role],
        "status": "active",
        "role_assignments": [],
    }
    response = client.put(
        f"/api/v1/admin/memberships/{USER_A}/department",
        json={"department_id": str(DEPT_A)},
    )
    assert response.status_code == 403


def test_migration_keeps_member_departments_inside_the_institution() -> None:
    from pathlib import Path

    sql = (
        Path(__file__).resolve().parents[3]
        / "supabase/migrations/20261125000000_member_departments.sql"
    ).read_text(encoding="utf-8")
    assert "PRIMARY KEY (institution_id, user_id)" in sql
    assert "d.institution_id = NEW.institution_id" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "REVOKE ALL ON TABLE public.institution_member_departments FROM PUBLIC, anon, authenticated" in sql
