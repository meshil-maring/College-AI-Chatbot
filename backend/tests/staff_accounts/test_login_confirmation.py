"""Approval and login stay recoverable when provider confirmation fails."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.main import app
from app.services.admin import admin_memberships

USER_ID = "20000000-0000-0000-0000-000000000001"
INST_ID = UUID("40000000-0000-0000-0000-000000000001")
REQUEST_ID = UUID("30000000-0000-0000-0000-000000000001")
EMAIL = "applicant@example.com"
PASSWORD = "registration-password"


@pytest.fixture
def journey():
    state = SimpleNamespace(status="pending", confirmed=False, grants=0)
    database, provider = MagicMock(), MagicMock()
    account = {
        "id": USER_ID, "auth_user_id": "auth-applicant", "email": EMAIL,
        "status": "active",
    }

    def request_row():
        return {
            "request_id": str(REQUEST_ID), "user_id": USER_ID,
            "official_email": EMAIL, "requested_role": state.role,
            "institution_id": str(INST_ID), "status": state.status,
        }

    def sign_in(credentials):
        if credentials != {"email": EMAIL, "password": PASSWORD}:
            raise AuthApiError("Invalid login credentials", 400, "invalid_credentials")
        if not state.confirmed:
            raise AuthApiError("Email not confirmed", 400, "email_not_confirmed")
        return SimpleNamespace(
            user=SimpleNamespace(id="auth-applicant", email=EMAIL),
            session=SimpleNamespace(
                access_token="test-access", refresh_token="test-refresh", expires_in=3600,
            ),
        )

    def grant(*_args, **_kwargs):
        already = state.status == "approved"
        if not already:
            state.status = "approved"
            state.grants += 1
        return {"already_applied": already, "role_granted": True, "audit_persisted": True}

    def confirm(*_args):
        state.confirmed = True

    provider.auth.sign_in_with_password.side_effect = sign_in
    database.auth.admin.update_user_by_id.side_effect = confirm
    with (
        patch("app.api.auth.common.create_supabase_client", return_value=provider),
        patch("app.api.auth.common.get_admin_client", return_value=database),
        patch("app.api.auth.common.get_sign_in_context", new=AsyncMock(return_value={
            "user_id": USER_ID, "status": "active", "institution_id": None,
        })),
        patch("app.api.auth.common.enforce_auth_rate_limit"),
        patch("app.api.auth.common.record_auth_security_event") as audit,
        patch("app.repositories.platform.tenancy.get_user_by_email", return_value={
            "user_id": USER_ID, "auth_user_id": "auth-applicant", "email": EMAIL,
        }) as lookup,
        patch("app.repositories.platform.tenancy.get_pending_membership_request_for_user",
              side_effect=lambda *_: request_row() if state.status == "pending" else None),
        patch.object(admin_memberships, "get_admin_client", return_value=database),
        patch.object(admin_memberships.repo, "get_request_for_institution",
                     side_effect=lambda *_: request_row()),
        patch.object(admin_memberships.repo, "get_user", return_value=account),
        patch.object(admin_memberships.repo, "approve_and_grant_role", side_effect=grant) as approval,
    ):
        yield SimpleNamespace(
            state=state, database=database, confirm=confirm, lookup=lookup,
            audit=audit, approval=approval, client=TestClient(app),
        )


def login(journey, password=PASSWORD):
    return journey.client.post("/api/v1/auth/login", json={"email": EMAIL, "password": password})


@pytest.mark.parametrize("role", ["staff", "faculty"])
def test_failed_confirmation_can_retry_approved_request_then_login(journey, role):
    journey.state.role = role
    assert login(journey).json()["error"]["code"] == "REGISTRATION_PENDING"
    journey.database.auth.admin.update_user_by_id.side_effect = AuthApiError(
        "Provider unavailable", 503, "server_error",
    )
    actor = {"user_id": "institution-admin"}
    with pytest.raises(AppError) as failure:
        admin_memberships.decide_request(actor, INST_ID, REQUEST_ID, approve=True, reason=None)
    assert failure.value.code == "MEMBERSHIP_EMAIL_CONFIRMATION_FAILED"
    assert journey.state.status == "approved"
    assert journey.state.grants == 1
    assert journey.state.confirmed is False

    blocked = login(journey)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "EMAIL_CONFIRMATION_REQUIRED"
    assert "retry sign-in setup" in blocked.json()["error"]["message"]
    assert "access_token" not in blocked.json()

    journey.database.auth.admin.update_user_by_id.side_effect = journey.confirm
    retried = admin_memberships.decide_request(
        actor, INST_ID, REQUEST_ID, approve=True, reason=None,
    )
    assert retried.already_applied is True
    assert journey.approval.call_count == 2
    assert journey.state.grants == 1
    assert journey.state.confirmed is True
    journey.database.auth.admin.update_user_by_id.assert_called_with(
        "auth-applicant", {"email_confirm": True},
    )
    response = login(journey)
    assert response.status_code == 200
    assert response.json()["access_token"] == "test-access"
    assert response.json()["user"]["email"] == EMAIL


@pytest.mark.parametrize("status", ["pending", "approved", "rejected"])
def test_wrong_password_never_discloses_registration_state(journey, status):
    journey.state.role = "staff"
    journey.state.status = status
    response = login(journey, password="incorrect-password")
    assert response.status_code == 400
    assert response.json() == {"error": {
        "code": "INVALID_CREDENTIALS", "message": "Invalid login credentials",
    }}
    journey.lookup.assert_not_called()
    journey.database.auth.admin.update_user_by_id.assert_not_called()


def test_unconfirmed_email_denial_records_failure_without_confirming(journey):
    journey.state.role = "staff"
    journey.state.status = "approved"
    response = login(journey)
    assert response.status_code == 403
    journey.audit.assert_called_once()
    assert journey.audit.call_args.kwargs["status"] == "failure"
    journey.database.auth.admin.update_user_by_id.assert_not_called()
