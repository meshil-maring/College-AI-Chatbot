"""Focused Phase 7.23 security, tenant, lifecycle, and concurrency tests."""

from unittest.mock import ANY, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services import admin_memberships as service
from app.services import platform_admin_invitations as invitation_service
from app.schemas.admin_invitations import AdminInvitationAcceptRequest
from supabase_auth.errors import AuthApiError

INST_A = UUID("40000000-0000-0000-0000-000000000001")
INST_B = UUID("40000000-0000-0000-0000-000000000002")
ADMIN_A = "10000000-0000-0000-0000-000000000001"
USER_A = UUID("20000000-0000-0000-0000-000000000001")
REQUEST_A = UUID("30000000-0000-0000-0000-000000000001")
client = TestClient(app, raise_server_exceptions=False)


def _actor() -> dict:
    return {"user_id": ADMIN_A, "institution_id": str(INST_A), "roles": ["admin"]}


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _request(**changes) -> dict:
    row = {
        "request_id": str(REQUEST_A),
        "institution_id": str(INST_A),
        "organization_id": "50000000-0000-0000-0000-000000000001",
        "user_id": str(USER_A),
        "requested_role": "staff",
        "official_email": "staff@a.example",
        "full_name": "Staff A",
        "status": "pending",
        "created_at": "2026-10-04T00:00:00Z",
    }
    row.update(changes)
    return row


def test_request_listing_is_pinned_to_server_institution() -> None:
    listing = MagicMock(return_value=[_request()])
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "list_requests", listing
    ):
        result = service.list_requests(INST_A, role="staff", status="pending")
    assert result.total == 1
    assert result.requests[0].email == "staff@a.example"
    listing.assert_called_once_with(
        ANY, INST_A, role="staff", status="pending"
    )


@pytest.mark.parametrize("role", ["staff", "faculty", "student"])
def test_non_admin_roles_cannot_approve_membership_requests(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": ADMIN_A,
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "roles": [role],
        "status": "active",
        "role_assignments": [],
    }
    response = client.post(
        f"/api/v1/admin/memberships/requests/{REQUEST_A}/approve", json={}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("role", ["staff", "faculty"])
def test_non_admin_roles_cannot_modify_roster(role: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": ADMIN_A,
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "roles": [role],
        "status": "active",
        "role_assignments": [],
    }
    response = client.post(f"/api/v1/admin/memberships/{USER_A}/deactivate")
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["admin", "super_admin", "student"])
def test_request_role_escalation_is_rejected(role: str) -> None:
    with pytest.raises(AppError) as caught:
        service.list_requests(INST_A, role=role)
    assert caught.value.code == "INVALID_MEMBERSHIP_ROLE"


def test_foreign_request_id_fails_without_granting_access() -> None:
    approve = MagicMock()
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "get_request_for_institution", return_value=None
    ), patch.object(service.repo, "approve_and_grant_role", approve):
        with pytest.raises(AppError) as caught:
            service.decide_request(
                _actor(), INST_A, REQUEST_A, approve=True, reason=None
            )
    assert caught.value.code == "MEMBERSHIP_REQUEST_NOT_FOUND"
    approve.assert_not_called()


def test_approval_grants_requested_server_owned_role_immediately() -> None:
    row = _request(requested_role="faculty")
    approve = MagicMock(return_value={"already_applied": False, "role_granted": True})
    client = MagicMock()
    with patch.object(service, "get_admin_client", return_value=client), patch.object(
        service.repo, "get_request_for_institution", return_value=row
    ), patch.object(service.repo, "get_user", return_value={
        "id": str(USER_A),
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "email": "staff@a.example",
        "status": "active",
    }), patch.object(service.repo, "approve_and_grant_role", approve), patch.object(
        service, "_audit"
    ) as audit:
        result = service.decide_request(
            _actor(), INST_A, REQUEST_A, approve=True, reason=None
        )
    assert result.status == "approved"
    assert "can now sign in" in result.message
    approve.assert_called_once()
    assert approve.call_args.kwargs["institution_id"] == INST_A
    assert audit.call_args.args[4] == {
        "role": "faculty",
        "status": "approved",
        "access_granted": True,
    }
    client.auth.admin.update_user_by_id.assert_called_once_with(
        "70000000-0000-0000-0000-000000000001",
        {"email_confirm": True},
    )


def test_repeat_approval_confirms_email_for_already_approved_applicant() -> None:
    client = MagicMock()
    row = _request(status="approved", requested_role="faculty")
    with patch.object(service, "get_admin_client", return_value=client), patch.object(
        service.repo, "get_request_for_institution", return_value=row
    ), patch.object(service.repo, "get_user", return_value={
        "id": str(USER_A),
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "email": "staff@a.example",
        "status": "active",
    }), patch.object(service.repo, "approve_and_grant_role") as grant:
        result = service.decide_request(
            _actor(), INST_A, REQUEST_A, approve=True, reason=None
        )
    assert result.already_applied is True
    client.auth.admin.update_user_by_id.assert_called_once_with(
        "70000000-0000-0000-0000-000000000001",
        {"email_confirm": True},
    )
    grant.assert_not_called()


def test_email_confirmation_failure_does_not_grant_membership_role() -> None:
    client = MagicMock()
    client.auth.admin.update_user_by_id.side_effect = AuthApiError(
        "Auth Admin API unavailable", 503, "server_error"
    )
    grant = MagicMock()
    with patch.object(service, "get_admin_client", return_value=client), patch.object(
        service.repo, "get_request_for_institution", return_value=_request()
    ), patch.object(service.repo, "get_user", return_value={
        "id": str(USER_A),
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "email": "staff@a.example",
        "status": "active",
    }), patch.object(service.repo, "approve_and_grant_role", grant):
        with pytest.raises(AppError) as caught:
            service.decide_request(
                _actor(), INST_A, REQUEST_A, approve=True, reason=None
            )
    assert caught.value.code == "MEMBERSHIP_EMAIL_CONFIRMATION_FAILED"
    grant.assert_not_called()


def test_rejection_assigns_no_role_and_sends_no_invitation() -> None:
    grant = MagicMock()
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "get_request_for_institution", return_value=_request()
    ), patch.object(
        service.repo, "decide_pending_request", return_value=_request(status="rejected")
    ), patch.object(service.repo, "approve_and_grant_role", grant), patch.object(
        service, "_audit"
    ):
        result = service.decide_request(
            _actor(), INST_A, REQUEST_A, approve=False, reason="not eligible"
        )
    assert result.status == "rejected"
    grant.assert_not_called()


def test_approval_rejects_an_invalid_applicant_before_transition() -> None:
    decide = MagicMock()
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "get_request_for_institution", return_value=_request()
    ), patch.object(
        service.repo, "get_user", return_value={
            "id": str(USER_A), "email": "staff@a.example", "status": "deactivated"
        }
    ), patch.object(service.repo, "decide_pending_request", decide):
        with pytest.raises(AppError) as caught:
            service.decide_request(_actor(), INST_A, REQUEST_A, approve=True, reason=None)
    assert caught.value.code == "APPLICANT_STATE_INVALID"
    decide.assert_not_called()


def test_repeat_same_decision_is_idempotent() -> None:
    with patch.object(service, "get_admin_client", return_value=MagicMock()), patch.object(
        service.repo,
        "get_request_for_institution",
        return_value=_request(status="approved"),
    ), patch.object(service.repo, "get_user", return_value={
        "id": str(USER_A),
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "email": "staff@a.example",
        "status": "active",
    }), patch.object(service.repo, "decide_pending_request") as decide:
        result = service.decide_request(
            _actor(), INST_A, REQUEST_A, approve=True, reason=None
        )
    assert result.already_applied is True
    decide.assert_not_called()


def test_approve_reject_race_loser_gets_conflict() -> None:
    with patch.object(service, "get_admin_client", return_value=MagicMock()), patch.object(
        service.repo, "get_request_for_institution", return_value=_request()
    ), patch.object(service.repo, "get_user", return_value={
        "id": str(USER_A),
        "auth_user_id": "70000000-0000-0000-0000-000000000001",
        "email": "staff@a.example",
        "status": "active",
    }), patch.object(
        service.repo, "approve_and_grant_role", return_value={"conflict": True}
    ):
        with pytest.raises(AppError) as caught:
            service.decide_request(
                _actor(), INST_A, REQUEST_A, approve=True, reason=None
            )
    assert caught.value.code == "MEMBERSHIP_REQUEST_CONFLICT"


def test_roster_lists_only_staff_faculty_with_granted_roles() -> None:
    grants = [
        {
            "user_id": str(USER_A),
            "assigned_at": "2026-10-04T00:00:00Z",
            "roles": {"name": "staff"},
            "users": {
                "id": str(USER_A),
                "email": "staff@a.example",
                "first_name": "Staff",
                "last_name": "A",
                "status": "active",
            },
        }
    ]
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "list_scoped_role_grants", return_value=grants
    ), patch.object(service.invitation_repo, "list_invitations") as list_invitations:
        result = service.list_roster(INST_A)
    assert result.total == 1
    assert {entry.role for entry in result.members} == {"staff"}
    assert result.members[0].created_at is not None
    list_invitations.assert_not_called()


def test_cross_tenant_deactivation_fails_safely() -> None:
    grants = [{"scope_type": "institution", "scope_id": str(INST_B), "roles": {"name": "staff"}}]
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "get_user", return_value={"id": str(USER_A), "status": "active"}
    ), patch.object(service.repo, "list_user_grants", return_value=grants), patch.object(
        service.repo, "set_user_status"
    ) as update:
        with pytest.raises(AppError) as caught:
            service.set_active(_actor(), INST_A, USER_A, active=False)
    assert caught.value.code == "MEMBERSHIP_NOT_FOUND"
    update.assert_not_called()


def test_admin_or_platform_role_cannot_be_modified_through_roster() -> None:
    grants = [
        {"scope_type": "institution", "scope_id": str(INST_A), "roles": {"name": "staff"}},
        {"scope_type": "platform", "scope_id": None, "roles": {"name": "super_admin"}},
    ]
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "get_user", return_value={"id": str(USER_A), "status": "active"}
    ), patch.object(service.repo, "list_user_grants", return_value=grants):
        with pytest.raises(AppError) as caught:
            service.set_active(_actor(), INST_A, USER_A, active=False)
    assert caught.value.code == "PROTECTED_ROLE"


@pytest.mark.parametrize(
    ("active", "current", "desired"),
    [(False, "active", "deactivated"), (True, "deactivated", "active")],
)
def test_lifecycle_uses_existing_user_status(active: bool, current: str, desired: str) -> None:
    grants = [{"scope_type": "institution", "scope_id": str(INST_A), "roles": {"name": "staff"}}]
    update = MagicMock(return_value=True)
    with patch.object(service, "get_admin_client", return_value=object()), patch.object(
        service.repo, "get_user", return_value={"id": str(USER_A), "status": current}
    ), patch.object(service.repo, "list_user_grants", return_value=grants), patch.object(
        service.repo, "set_user_status", update
    ), patch.object(service, "_audit"):
        result = service.set_active(_actor(), INST_A, USER_A, active=active)
    assert result.status == desired
    assert update.call_args.kwargs["status"] == desired


def test_migration_allows_only_three_institution_roles() -> None:
    migration = (
        __import__("pathlib").Path(__file__).parents[2]
        / "supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql"
    ).read_text(encoding="utf-8")
    assert "'admin'::text, 'staff'::text, 'faculty'::text" in migration
    assert "'super_admin'::text" not in migration
    assert "email_outbox" in migration


def test_approval_migration_grants_role_in_same_transaction() -> None:
    migration = (
        __import__("pathlib").Path(__file__).parents[2]
        / "supabase/migrations/20261009000000_phase_7_24_immediate_staff_faculty_approval.sql"
    ).read_text(encoding="utf-8")
    assert "phase723_approve_membership_and_grant_role" in migration
    assert "phase81_assert_institution_admin" in migration
    assert "phase81_assign_institution_role_audited" not in migration
    assert "INSERT INTO \"public\".\"user_roles\"" in migration
    assert "'role_granted', true" in migration
    assert "'email_outbox'" not in migration


def test_staff_invitation_acceptance_links_existing_identity_and_grants_stored_scope() -> None:
    invitation = {
        "invitation_id": "60000000-0000-0000-0000-000000000001",
        "institution_id": str(INST_A),
        "email": "staff@a.example",
        "role_name": "staff",
        "status": "invited",
        "expires_at": "2099-01-01T00:00:00Z",
        "created_by": ADMIN_A,
    }
    client = MagicMock()
    assign = MagicMock()
    with patch.object(invitation_service.abuse, "enforce_accept_rate_limit"), patch.object(
        invitation_service, "get_admin_client", return_value=client
    ), patch.object(
        invitation_service, "_resolve_live_invitation", return_value=invitation
    ), patch.object(
        invitation_service,
        "_require_active_institution",
        return_value={
            "institution_id": str(INST_A),
            "organization_id": "50000000-0000-0000-0000-000000000001",
            "name": "Institution A",
        },
    ), patch.object(
        invitation_service.tenancy_repo,
        "get_user_by_email",
        return_value={
            "user_id": str(USER_A),
            "auth_user_id": "70000000-0000-0000-0000-000000000001",
            "email": "staff@a.example",
        },
    ), patch.object(
        invitation_service.invite_repo,
        "claim_invitation",
        return_value={**invitation, "status": "accepted"},
    ), patch.object(
        invitation_service.invite_repo, "mark_email_verified"
    ), patch.object(
        invitation_service.tenancy_repo, "assign_membership_role", assign
    ):
        result = invitation_service.accept_invitation(
            "a" * 64,
            AdminInvitationAcceptRequest(password="safe-password"),
            peer="test",
        )
    assert result.role == "staff"
    client.auth.admin.update_user_by_id.assert_called_once()
    assign.assert_called_once_with(
        client,
        actor_user_id=str(USER_A),
        user_id=str(USER_A),
        role_name="staff",
        institution_id=INST_A,
        organization_id="50000000-0000-0000-0000-000000000001",
    )
