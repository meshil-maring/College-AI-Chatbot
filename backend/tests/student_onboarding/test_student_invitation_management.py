from unittest.mock import Mock
from uuid import UUID
from datetime import datetime, timezone

import pytest
from postgrest.exceptions import APIError
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.invitations.student_onboarding import StudentInvitationView
from app.schemas.invitations.student_onboarding_management import StudentInvitationUpdateRequest
from app.services.invitations import student_onboarding_management as management
from app.services.invitations.student_onboarding_common import database

TENANT = UUID("10000000-0000-0000-0000-000000000001")
INVITATION = UUID("20000000-0000-0000-0000-000000000001")
ACTOR = {"user_id": "30000000-0000-0000-0000-000000000001"}


def invitation_view(email: str = "ada@example.test") -> StudentInvitationView:
    return StudentInvitationView(
        invitation_id=INVITATION,
        institution_id=TENANT,
        email=email,
        student_name="Ada Lovelace",
        register_number="REG-1",
        university_roll_number=None,
        academic_section_id=INVITATION,
        expires_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )


def test_update_requires_placement_grant_only_when_section_changes(monkeypatch):
    client = object()
    context = Mock(return_value=(client, TENANT, ACTOR["user_id"]))
    update = Mock(return_value={"invitation_id": str(INVITATION), "email_changed": False})
    project = Mock(return_value=invitation_view())
    monkeypatch.setattr(management, "admin_context", context)
    monkeypatch.setattr(management, "database", lambda operation: operation())
    monkeypatch.setattr(management.repository, "update", update)
    monkeypatch.setattr(management, "project_invitation", project)
    monkeypatch.setattr(management, "token", Mock(return_value=("raw", "a" * 64)))
    payload = {
        "email": "ada@example.test",
        "student_name": "Ada Lovelace",
        "register_number": "REG-1",
        "university_roll_number": None,
        "academic_section_id": None,
    }

    result = management.update(ACTOR, INVITATION, payload)
    assert result.invitation == invitation_view()
    assert result.email_changed is False
    context.assert_called_once_with(
        ACTOR,
        ("students.update",),
        denied_message="You do not have permission to edit this student invitation.",
    )
    update.assert_called_once_with(
        client,
        actor=ACTOR["user_id"],
        tenant=TENANT,
        invitation=INVITATION,
        payload=payload,
        token_hash="a" * 64,
        expires_at=update.call_args.kwargs["expires_at"],
    )


def test_update_requires_course_grant_for_section_change(monkeypatch):
    context = Mock(return_value=(object(), TENANT, ACTOR["user_id"]))
    monkeypatch.setattr(management, "admin_context", context)
    monkeypatch.setattr(management, "database", lambda operation: operation())
    monkeypatch.setattr(management.repository, "update", Mock(return_value={"email_changed": False}))
    monkeypatch.setattr(management, "project_invitation", lambda row: invitation_view())
    monkeypatch.setattr(management, "token", Mock(return_value=("raw", "a" * 64)))

    management.update(ACTOR, INVITATION, {
        "email": "ada@example.test",
        "student_name": "Ada Lovelace",
        "register_number": "REG-1",
        "university_roll_number": None,
        "academic_section_id": str(INVITATION),
    })

    context.assert_called_once_with(
        ACTOR,
        ("students.update", "courses.manage"),
        denied_message="You do not have permission to edit this student invitation.",
    )


def test_cancel_uses_delete_grant_and_repository(monkeypatch):
    client = object()
    context = Mock(return_value=(client, TENANT, ACTOR["user_id"]))
    cancel = Mock(return_value={"invitation_id": str(INVITATION), "cancelled": True})
    monkeypatch.setattr(management, "admin_context", context)
    monkeypatch.setattr(management, "database", lambda operation: operation())
    monkeypatch.setattr(management.repository, "cancel", cancel)

    result = management.cancel(ACTOR, INVITATION)

    assert result.invitation_id == INVITATION
    assert result.cancelled is True
    context.assert_called_once_with(
        ACTOR,
        ("students.delete",),
        denied_message="You do not have permission to cancel this student invitation.",
    )
    cancel.assert_called_once_with(
        client, actor=ACTOR["user_id"], tenant=TENANT, invitation=INVITATION
    )


def test_invitation_update_contract_normalizes_email_and_identity():
    request = StudentInvitationUpdateRequest.model_validate(
        {
            "email": " ADA@example.com ",
            "student_name": "  Ada   Lovelace ",
            "register_number": " REG-1 ",
            "university_roll_number": "  ",
        }
    )

    assert request.email == "ada@example.com"
    assert request.student_name == "Ada Lovelace"
    assert request.register_number == "REG-1"
    assert request.university_roll_number is None

    with pytest.raises(ValidationError):
        StudentInvitationUpdateRequest.model_validate(
            {
                "email": "not-an-email",
                "student_name": "Ada Lovelace",
                "register_number": "REG-1",
            }
        )


def test_email_update_rotates_token_and_delivers_to_corrected_address(monkeypatch):
    client = object()
    row = {"invitation_id": str(INVITATION), "email": "corrected@example.test", "email_changed": True}
    delivery = Mock(
        invitation=invitation_view("corrected@example.test"),
        delivery_status="sent",
        delivery_message="Setup link sent to corrected email.",
    )
    monkeypatch.setattr(management, "admin_context", Mock(return_value=(client, TENANT, ACTOR["user_id"])))
    monkeypatch.setattr(management, "database", lambda operation: operation())
    monkeypatch.setattr(management.repository, "update", Mock(return_value=row))
    monkeypatch.setattr(management, "token", Mock(return_value=("raw-token", "c" * 64)))
    monkeypatch.setattr(management, "deliver_setup_link", Mock(return_value=delivery))

    result = management.update(ACTOR, INVITATION, {
        "email": "corrected@example.test",
        "student_name": "Ada Lovelace",
        "register_number": "REG-1",
        "university_roll_number": None,
        "academic_section_id": None,
    })

    assert result.email_changed is True
    assert result.delivery_status == "sent"
    assert result.delivery_message == "Setup link sent to corrected email."
    management.deliver_setup_link.assert_called_once()


def test_cancel_refuses_invitations_with_provisioned_accounts():
    failure = APIError({"code": "P0003", "message": "private database detail"})

    with pytest.raises(AppError) as error:
        database(lambda: (_ for _ in ()).throw(failure))

    assert error.value.code == "INVITATION_SETUP_STARTED"
    assert "private database detail" not in error.value.message
