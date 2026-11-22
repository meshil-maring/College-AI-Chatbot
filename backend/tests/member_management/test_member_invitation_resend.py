"""Staff/Faculty invitation resend: tenant-pinned, and the new link goes only by email."""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.schemas.admin.member_invitations import MemberInvitationResent
from app.services.admin import member_invitations as service

INST = UUID("40000000-0000-0000-0000-000000000001")
INVITATION = UUID("60000000-0000-0000-0000-000000000001")
ACTOR = {"user_id": "10000000-0000-0000-0000-000000000001"}
DELIVERY = {"status": "sent", "provider": "test", "code": None}


def stored(**changes):
    return {"institution_id": str(INST), "role_name": "staff", "email": "s@example.com", **changes}


def test_resend_returns_the_outcome_but_never_the_new_token_or_link():
    shared = SimpleNamespace(
        invitation_token="raw-token", invitation_url="/admin-invite/raw-token",
        email_delivery=DELIVERY, expires_in_hours=72, message="A new invitation email was sent.",
    )
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.invite_repo, "get_invitation_by_id", return_value=stored()), \
            patch.object(service.invitations, "resend_invitation", return_value=shared) as resend, \
            patch.object(service, "_audit") as audit:
        result = service.resend(ACTOR, INST, INVITATION, "peer")
    resend.assert_called_once_with(ACTOR, INST, INVITATION, peer="peer")
    audit.assert_called_once()
    assert isinstance(result, MemberInvitationResent)
    body = result.model_dump(mode="json")
    assert "raw-token" not in str(body)
    assert body["message"] == "A new invitation email was sent." and body["expires_in_hours"] == 72


@pytest.mark.parametrize("invitation", [
    None, stored(role_name="admin"), stored(institution_id="40000000-0000-0000-0000-000000000009"),
])
def test_resend_refuses_other_roles_and_institutions(invitation):
    with patch.object(service, "get_admin_client", return_value="db"), \
            patch.object(service.invite_repo, "get_invitation_by_id", return_value=invitation), \
            patch.object(service.invitations, "resend_invitation") as resend:
        with pytest.raises(AppError) as error:
            service.resend(ACTOR, INST, INVITATION, "peer")
    assert error.value.status_code == 404
    resend.assert_not_called()


def test_resend_response_model_has_no_token_fields():
    assert not {"invitation_token", "invitation_url"} & set(MemberInvitationResent.model_fields)
