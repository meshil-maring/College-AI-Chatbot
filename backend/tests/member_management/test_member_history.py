"""Account history and the directory's employment status."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
from app.core.errors import AppError
from app.repositories.admin import admin_audit
from app.schemas.admin.admin_memberships import MembershipRoster, MembershipRosterEntry
from app.services.admin import member_history as service
from app.services.admin import member_profiles

INST_A = UUID("40000000-0000-0000-0000-000000000001")
INST_B = UUID("40000000-0000-0000-0000-000000000002")
USER = UUID("30000000-0000-0000-0000-000000000001")
ADMIN = "10000000-0000-0000-0000-000000000001"


def grants(role: str, tenant: UUID = INST_A) -> list[dict]:
    return [{"scope_type": "institution", "scope_id": str(tenant), "roles": {"name": role}}]


def users_client(rows: list[dict]) -> MagicMock:
    client = MagicMock()
    client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = rows
    return client


@pytest.mark.parametrize("role", ["staff", "faculty", "admin"])
def test_history_labels_entries_and_names_the_actor(role) -> None:
    rows = [
        {"audit_id": "a0000000-0000-0000-0000-000000000001", "actor_user_id": ADMIN, "action": "staff_suspended",
         "record_data": {"status": "suspended"}, "performed_at": "2026-11-22T10:00:00Z"},
        {"audit_id": "a0000000-0000-0000-0000-000000000002", "actor_user_id": None, "action": "custom.thing_done",
         "record_data": None, "performed_at": "2026-11-21T10:00:00Z"},
    ]
    client = users_client([{"id": ADMIN, "email": "o@example.com", "first_name": "Olive", "last_name": "Owner"}])
    with patch.object(service, "get_admin_client", return_value=client), \
            patch.object(service.membership_repo, "list_user_grants", return_value=grants(role)), \
            patch.object(service.admin_audit, "list_member_history", return_value=rows) as read:
        result = service.history(INST_A, USER)
    read.assert_called_once_with(client, INST_A, USER)
    first, second = result.entries
    assert (first.label, first.actor_name, first.details) == ("Suspended", "Olive Owner", {"status": "suspended"})
    assert (second.label, second.actor_name, second.details) == ("custom thing done", "System", {})


@pytest.mark.parametrize("grant", [grants("staff", INST_B), grants("student"), []])
def test_history_of_someone_outside_the_institution_is_not_found(grant) -> None:
    with patch.object(service, "get_admin_client", return_value=MagicMock()), \
            patch.object(service.membership_repo, "list_user_grants", return_value=grant), \
            patch.object(service.admin_audit, "list_member_history") as read:
        with pytest.raises(AppError) as caught:
            service.history(INST_A, USER)
    assert caught.value.status_code == 404
    read.assert_not_called()


def test_history_query_is_pinned_to_the_institution_and_a_valid_id() -> None:
    client = MagicMock()
    query = client.table.return_value.select.return_value
    query.eq.return_value.or_.return_value.order.return_value.limit.return_value.execute.return_value.data = []
    admin_audit.list_member_history(client, INST_A, USER)
    query.eq.assert_called_once_with("institution_id", str(INST_A))
    query.eq.return_value.or_.assert_called_once_with(
        f"record_id.eq.{USER},record_data->>faculty_user_id.eq.{USER}")
    with pytest.raises(ValueError):
        admin_audit.list_member_history(client, INST_A, "x,record_id.neq.0")


def test_history_route_needs_user_and_audit_read() -> None:
    assert _ADMIN_ROUTE_PERMISSIONS[("GET", "/admin/memberships/{user_id}/history")] == ("users.read", "audit.read")


@pytest.mark.parametrize("end,expected", [
    (None, "active"), (str(date.today() + timedelta(days=5)), "active"),
    (str(date.today() - timedelta(days=1)), "contract_ended"),
])
def test_directory_shows_employment_status(end, expected) -> None:
    roster = MembershipRoster(total=1, members=[MembershipRosterEntry(
        user_id=USER, name="Ada", email="ada@example.com", role="faculty", status="active")])
    with patch.object(member_profiles, "get_admin_client", return_value=object()), \
            patch.object(member_profiles.repo, "list_common", return_value=[]), \
            patch.object(member_profiles.repo, "list_staff", return_value=[]), \
            patch.object(member_profiles.repo, "list_additional", return_value=[]), \
            patch.object(member_profiles.repo, "list_faculty", return_value=[
                {"user_id": str(USER), "employment_type": "contractual", "contract_end_date": end}]):
        member = member_profiles.with_profiles(INST_A, roster).members[0]
    assert (member.employment_type, member.employment_status) == ("contractual", expected)


def test_member_without_a_profile_has_no_employment_status() -> None:
    roster = MembershipRoster(total=1, members=[MembershipRosterEntry(
        user_id=USER, name="Ada", email="ada@example.com", role="staff", status="active")])
    with patch.object(member_profiles, "get_admin_client", return_value=object()), \
            patch.object(member_profiles.repo, "list_common", return_value=[]), \
            patch.object(member_profiles.repo, "list_staff", return_value=[]), \
            patch.object(member_profiles.repo, "list_faculty", return_value=[]), \
            patch.object(member_profiles.repo, "list_additional", return_value=[]):
        assert member_profiles.with_profiles(INST_A, roster).members[0].employment_status == "not_set"
