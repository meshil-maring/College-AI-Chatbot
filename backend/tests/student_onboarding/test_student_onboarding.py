from unittest.mock import Mock
from uuid import UUID

import pytest
from supabase_auth.errors import AuthRetryableError

from app.core.errors import AppError
from app.schemas.invitations.student_onboarding import (
    StudentIdentityInput,
    StudentIdentityReviewRequest,
    StudentIdentityReviewResponse,
    StudentInvitationBulkRequest,
    StudentInvitationCompleteRequest,
)
from app.services.invitations import student_onboarding_acceptance as acceptance

TOKEN = "a" * 43
TOKEN_HASH = "b" * 64
INVITATION_ID = "20000000-0000-0000-0000-000000000001"
AUTH_USER_ID = "30000000-0000-0000-0000-000000000001"
INVITATION = {
    "invitation_id": INVITATION_ID,
    "status": "pending",
    "section_active": True,
    "email": "student@example.test",
}


def test_student_identity_normalizes_email_and_optional_roll_number():
    student = StudentIdentityInput(
        student_name="  Ada   Lovelace ",
        register_number=" REG 100 ",
        university_roll_number="  ",
        email="ADA@example.com",
    )

    assert student.student_name == "Ada Lovelace"
    assert student.register_number == "REG 100"
    assert student.email == "ada@example.com"
    assert student.university_roll_number is None


def test_bulk_contract_rejects_more_than_500_students():
    row = {
        "source_row": 2,
        "student_name": "Ada",
        "register_number": "REG 100",
        "email": "ada@example.test",
    }

    with pytest.raises(ValueError):
        StudentInvitationBulkRequest(
            academic_section_id="10000000-0000-0000-0000-000000000001",
            students=[row] * 501,
        )


def test_identity_review_requires_and_normalizes_identifiers():
    with pytest.raises(ValueError, match="enter at least one student identifier"):
        StudentIdentityReviewRequest()

    identity = StudentIdentityReviewRequest(
        email="ADA@example.com",
        register_number=" REG 100 ",
        university_roll_number="  ",
    )

    assert identity.email == "ada@example.com"
    assert identity.register_number == "REG 100"
    assert identity.university_roll_number is None


def test_identity_review_response_preserves_sign_in_and_delivery_state():
    response = StudentIdentityReviewResponse.model_validate({
        "students": [{
            "student_name": "Ada Lovelace",
            "email": "ada@example.com",
            "register_number": "REG-1",
            "university_roll_number": None,
            "approval_status": "approved",
            "account_status": "active",
            "student_status": "active",
            "is_active": True,
            "has_signed_in": True,
            "last_sign_in_at": "2026-10-28T10:00:00Z",
            "matches_email": True,
            "matches_register_number": False,
            "matches_university_roll_number": False,
        }],
        "invitations": [],
        "email_conflict_exists": True,
    })

    assert response.students[0].has_signed_in is True
    assert response.students[0].last_sign_in_at is not None
    assert response.email_conflict_exists is True


def test_setup_password_rejects_blank_values():
    with pytest.raises(ValueError):
        StudentInvitationCompleteRequest(token=TOKEN, password="        ")


def test_completion_records_auth_user_before_atomic_activation(monkeypatch):
    client = object()
    record_auth_user = Mock(return_value=True)
    complete_invitation = Mock(return_value={"accepted": True})
    monkeypatch.setattr(acceptance, "_resolve", lambda _: (TOKEN_HASH, INVITATION))
    monkeypatch.setattr(acceptance, "_create_or_update_auth_user", lambda *_: AUTH_USER_ID)
    monkeypatch.setattr(acceptance, "get_admin_client", lambda: client)
    monkeypatch.setattr(acceptance.repository, "claim_setup", Mock(return_value=True))
    monkeypatch.setattr(acceptance.repository, "record_auth_user", record_auth_user)
    monkeypatch.setattr(acceptance.repository, "complete", complete_invitation)

    result = acceptance.complete(TOKEN, "valid-password")

    assert result.completed is True
    record_auth_user.assert_called_once_with(
        client,
        invitation=UUID(INVITATION_ID),
        token_hash=TOKEN_HASH,
        auth_user=AUTH_USER_ID,
    )
    complete_invitation.assert_called_once()


def test_completion_stops_when_auth_user_cannot_be_recorded(monkeypatch):
    client = object()
    complete_invitation = Mock()
    monkeypatch.setattr(acceptance, "_resolve", lambda _: (TOKEN_HASH, INVITATION))
    monkeypatch.setattr(acceptance, "_create_or_update_auth_user", lambda *_: AUTH_USER_ID)
    monkeypatch.setattr(acceptance, "get_admin_client", lambda: client)
    monkeypatch.setattr(acceptance.repository, "claim_setup", Mock(return_value=True))
    monkeypatch.setattr(acceptance.repository, "record_auth_user", Mock(return_value=False))
    monkeypatch.setattr(acceptance.repository, "complete", complete_invitation)

    with pytest.raises(AppError):
        acceptance.complete(TOKEN, "valid-password")
    complete_invitation.assert_not_called()


def test_failed_password_setup_releases_claim_when_no_account_was_created(monkeypatch):
    client = object()
    release_setup = Mock(return_value=True)
    monkeypatch.setattr(acceptance, "_resolve", lambda _: (TOKEN_HASH, INVITATION))
    monkeypatch.setattr(
        acceptance, "_create_or_update_auth_user",
        Mock(side_effect=AppError("Email delivery failed.", 503, "AUTH_ACCOUNT_UNAVAILABLE")),
    )
    monkeypatch.setattr(acceptance, "get_admin_client", lambda: client)
    monkeypatch.setattr(acceptance.repository, "claim_setup", Mock(return_value=True))
    monkeypatch.setattr(acceptance.repository, "release_setup", release_setup)

    with pytest.raises(AppError, match="Email delivery failed."):
        acceptance.complete(TOKEN, "valid-password")

    release_setup.assert_called_once_with(
        client, invitation=UUID(INVITATION_ID), token_hash=TOKEN_HASH,
    )


def test_retryable_auth_failure_releases_setup_claim(monkeypatch):
    client = Mock()
    client.auth.admin.create_user.side_effect = AuthRetryableError("network unavailable", 0)
    release_setup = Mock(return_value=True)
    monkeypatch.setattr(acceptance, "_resolve", lambda _: (TOKEN_HASH, INVITATION))
    monkeypatch.setattr(acceptance, "get_admin_client", lambda: client)
    monkeypatch.setattr(acceptance.repository, "claim_setup", Mock(return_value=True))
    monkeypatch.setattr(acceptance.repository, "release_setup", release_setup)

    with pytest.raises(AppError) as error:
        acceptance.complete(TOKEN, "valid-password")

    assert error.value.code == "AUTH_ACCOUNT_UNAVAILABLE"
    release_setup.assert_called_once_with(
        client, invitation=UUID(INVITATION_ID), token_hash=TOKEN_HASH,
    )


def test_completion_requires_active_section_before_creating_auth_user(monkeypatch):
    inactive = {**INVITATION, "section_active": False}
    create_auth_user = Mock()
    monkeypatch.setattr(acceptance, "_resolve", lambda _: (TOKEN_HASH, inactive))
    monkeypatch.setattr(acceptance, "_create_or_update_auth_user", create_auth_user)

    with pytest.raises(AppError):
        acceptance.complete(TOKEN, "valid-password")
    create_auth_user.assert_not_called()


def test_student_invitation_management_routes_have_explicit_permissions():
    from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS

    assert _ADMIN_ROUTE_PERMISSIONS[
        ("PATCH", "/admin/students/onboarding-invitations/{invitation_id}")
    ] == ("students.update",)
    assert _ADMIN_ROUTE_PERMISSIONS[
        ("DELETE", "/admin/students/onboarding-invitations/{invitation_id}")
    ] == ("students.delete",)
