"""Administrator profiles and Owner-only invitation resend.

Database behaviour is covered by sql/admin_profile_contracts.sql.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS
from app.core.errors import AppError
from app.schemas.admin.institution_admins import AdminInvitationCreate
from app.schemas.admin.member_profiles import CommonProfile
from app.services.admin import institution_admins as service

INST = UUID("40000000-0000-0000-0000-000000000001")
OWNER = "10000000-0000-0000-0000-000000000001"
OTHER = "10000000-0000-0000-0000-000000000002"
INVITATION = UUID("60000000-0000-0000-0000-000000000001")
PROFILE = {"employee_id": "ADM-7", "designation": "Registrar", "joining_date": "2026-01-05", "phone": None}


def invitation(**changes):
    return {"institution_id": str(INST), "role_name": "admin", "created_by": OWNER, **changes}


def test_profile_save_goes_to_the_database_command_with_validated_fields():
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.repo, "save_profile", return_value={}) as command:
        result = service.save_profile({"user_id": OTHER}, INST, UUID(OTHER), CommonProfile(**PROFILE))
    command.assert_called_once_with("db", OTHER, INST, UUID(OTHER), PROFILE)
    assert result.message == "Profile saved."


def test_profile_fields_are_checked_before_the_database():
    for bad in ({"employee_id": "ADM 7"}, {"designation": "  "}, {"phone": "call me"}, {"joining_date": "soon"}):
        with pytest.raises(ValidationError):
            CommonProfile(**(PROFILE | bad))


def test_a_used_employee_id_is_a_clear_conflict():
    failure = Exception("raw")
    failure.code = "P1204"
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.repo, "save_profile", side_effect=failure):
        with pytest.raises(AppError) as error:
            service.save_profile({"user_id": OWNER}, INST, UUID(OWNER), CommonProfile(**PROFILE))
    assert (error.value.status_code, error.value.code) == (409, "EMPLOYEE_ID_IN_USE")


def test_invitation_passes_the_optional_profile_fields():
    body = AdminInvitationCreate(email="n@example.com", profile=PROFILE)
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.invite_repo, "generate_invitation_token", return_value="raw"), \
            patch.object(service.email_outbox_crypto, "protect_invitation_token", return_value="sealed"), \
            patch.object(service.repo, "create_invitation", return_value={}) as create:
        service.invite({"user_id": OWNER}, INST, body)
    assert create.call_args.kwargs["profile"] == PROFILE | {"joining_date": "2026-01-05"}
    assert AdminInvitationCreate(email="n@example.com").profile is None


@pytest.mark.parametrize(("owner", "stored", "status", "code"), [
    (OTHER, invitation(), 403, "OWNER_REQUIRED"),
    (OWNER, None, 404, "INVITATION_NOT_FOUND"),
    (OWNER, invitation(role_name="staff"), 404, "INVITATION_NOT_FOUND"),
    (OWNER, invitation(institution_id="40000000-0000-0000-0000-000000000009"), 404, "INVITATION_NOT_FOUND"),
    (OWNER, invitation(created_by=OTHER), 409, "INVITATION_FROM_PREVIOUS_OWNER"),
])
def test_resend_is_owner_only_and_only_for_their_own_admin_invitations(owner, stored, status, code):
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.repo, "read", return_value={"owner_user_id": owner}), \
            patch.object(service.invite_repo, "get_invitation_by_id", return_value=stored), \
            patch.object(service.invitations, "resend_invitation") as resend:
        with pytest.raises(AppError) as error:
            service.resend_invitation({"user_id": OWNER}, INST, INVITATION, "peer")
    assert (error.value.status_code, error.value.code) == (status, code)
    resend.assert_not_called()


def test_resend_rotates_the_link_through_the_shared_invitation_service():
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.repo, "read", return_value={"owner_user_id": OWNER}), \
            patch.object(service.invite_repo, "get_invitation_by_id", return_value=invitation()), \
            patch.object(service.invitations, "resend_invitation", return_value=SimpleNamespace(
                message="Sent.", invitation_token="raw-token", invitation_url="/accept?t=raw-token")) as resend:
        result = service.resend_invitation({"user_id": OWNER}, INST, INVITATION, "peer")
    resend.assert_called_once_with({"user_id": OWNER}, INST, INVITATION, peer="peer")
    # The new link goes only by email, as for a new invitation.
    assert result.model_dump() == {"message": "Sent.", "already_applied": False}


def test_new_routes_have_policies():
    assert _ADMIN_ROUTE_PERMISSIONS[("PUT", "/admin/institution-admins/{user_id}/profile")] == ("profile.own.update",)
    assert _ADMIN_ROUTE_PERMISSIONS[("POST", "/admin/institution-admins/invitations/{invitation_id}/resend")] == (
        "users.create", "roles.manage")
    assert date(2026, 1, 5) == CommonProfile(**PROFILE).joining_date
