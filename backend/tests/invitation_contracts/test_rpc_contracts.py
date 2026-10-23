"""Caller contracts only: no hosted schema assertions or database execution."""

from unittest.mock import MagicMock

import pytest
from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.repositories.admin import admin_memberships
from app.repositories.platform import platform_institutions
from app.services.admin import admin_memberships as memberships_service

ACTOR = "10000000-0000-0000-0000-000000000001"
AUTH = "10000000-0000-0000-0000-000000000002"
TARGET = "10000000-0000-0000-0000-000000000003"
INST = "30000000-0000-0000-0000-000000000001"


def _assign(client):
    return platform_institutions.assign_institution_admin(
        client,
        actor_user_id=ACTOR,
        actor_auth_user_id=AUTH,
        user_id=TARGET,
        institution_id=INST,
    )


def _reject(client, status="rejected"):
    return admin_memberships.decide_pending_request(
        client,
        request_id=TARGET,
        institution_id=INST,
        status=status,
        decided_by_user_id=ACTOR,
        reason="Reviewed",
    )


def test_assignment_retains_verified_actor_and_exact_five_argument_contract():
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = True
    assert _assign(client) == {"changed": True}
    client.rpc.assert_called_once_with(
        "phase81_assign_institution_role_audited",
        {
            "p_actor_user_id": ACTOR,
            "p_actor_auth_user_id": AUTH,
            "p_target_user_id": TARGET,
            "p_institution_id": INST,
            "p_role_name": "admin",
        },
    )
    client.table.assert_not_called()


def test_assignment_missing_contract_never_downgrades_to_legacy_signature():
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = APIError(
        {
            "code": "PGRST202",
            "message": "RPC unavailable",
            "details": None,
            "hint": None,
        }
    )
    with pytest.raises(APIError):
        _assign(client)
    assert client.rpc.call_count == 1
    client.table.assert_not_called()


@pytest.mark.parametrize(
    "data", [None, {"audit_persisted": True, "status": "rejected"}]
)
def test_membership_rejection_exact_contract_and_nullable_result(data):
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = data
    assert _reject(client) == data
    client.rpc.assert_called_once_with(
        "b05_reject_membership",
        {
            "p_request_id": TARGET,
            "p_institution_id": INST,
            "p_decided_by": ACTOR,
            "p_reason": "Reviewed",
        },
    )
    client.table.assert_not_called()


@pytest.mark.parametrize("code", ["PGRST202", "42883", "42703"])
def test_missing_membership_contract_is_unavailable_without_table_fallback(code):
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = APIError(
        {
            "code": code,
            "message": "private schema detail",
            "details": None,
            "hint": None,
        }
    )
    with pytest.raises(AppError) as caught:
        _reject(client)
    assert caught.value.status_code == 503
    assert caught.value.code == "MEMBERSHIP_REJECTION_UNAVAILABLE"
    assert "private" not in caught.value.message
    assert client.rpc.call_count == 1
    client.table.assert_not_called()


def test_membership_rejection_preserves_authorization_errors():
    client = MagicMock()
    error = APIError(
        {"code": "42501", "message": "denied", "details": None, "hint": None}
    )
    client.rpc.return_value.execute.side_effect = error
    with pytest.raises(APIError) as caught:
        _reject(client)
    assert caught.value is error
    client.table.assert_not_called()


@pytest.mark.parametrize("status", ["pending", "approved", "reject"])
def test_rejection_caller_cannot_silently_change_another_decision_to_reject(status):
    client = MagicMock()
    with pytest.raises(ValueError):
        _reject(client, status)
    client.rpc.assert_not_called()
    client.table.assert_not_called()


@pytest.mark.parametrize("result", [None, {"audit_persisted": False}])
def test_membership_service_never_reports_unaudited_rejection(monkeypatch, result):
    client = MagicMock()
    monkeypatch.setattr(memberships_service, "get_admin_client", lambda: client)
    monkeypatch.setattr(
        admin_memberships,
        "get_request_for_institution",
        lambda *_: {
            "requested_role": "staff",
            "status": "pending",
        },
    )
    client.rpc.return_value.execute.return_value.data = result
    with pytest.raises(AppError) as caught:
        memberships_service.decide_request(
            {"user_id": ACTOR},
            INST,
            TARGET,
            approve=False,
            reason=None,
        )
    assert caught.value.status_code == 409
    assert caught.value.code == (
        "MEMBERSHIP_REQUEST_CONFLICT"
        if result is None
        else "MEMBERSHIP_AUDIT_UNCERTAIN"
    )
    client.table.assert_not_called()


def test_membership_approval_preserves_local_argument_and_result_contract():
    client = MagicMock()
    result = {"role_granted": True, "audit_persisted": True, "already_applied": False}
    client.rpc.return_value.execute.return_value.data = result
    assert (
        admin_memberships.approve_and_grant_role(
            client,
            request_id=TARGET,
            institution_id=INST,
            decided_by_user_id=ACTOR,
            reason=None,
        )
        == result
    )
    client.rpc.assert_called_once_with(
        "phase723_approve_membership_and_grant_role",
        {
            "p_request_id": TARGET,
            "p_institution_id": INST,
            "p_decided_by": ACTOR,
            "p_reason": None,
        },
    )
    client.table.assert_not_called()
