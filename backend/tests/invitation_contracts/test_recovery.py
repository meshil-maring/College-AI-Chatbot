from unittest.mock import call
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.repositories.invitations import platform_admin_invitations as repo
from app.services.invitations import platform_admin_invitations as institution

from .support import TOKEN, INV, AUTH
from .support import recovery as recovery


@pytest.mark.parametrize(
    "kind,path",
    [("institution", "admin-invitations"), ("platform", "super-admin-invitations")],
)
def test_confirmation_failure_reload_and_retry_require_no_sign_in(recovery, kind, path):
    client, invitation, operation, read, create, reserve, grant = recovery
    http = TestClient(app)
    client.auth.admin.update_user_by_id.side_effect = [
        TimeoutError("lost confirmation"),
        None,
    ]
    endpoint = f"/api/v1/{path}/{TOKEN}"
    assert http.post(endpoint + "/recover").status_code == 502
    assert operation["stage"] == "accepted" and invitation["status"] == "accepted"
    assert http.get(endpoint).json()["account_recovery_available"] is True
    assert http.post(endpoint + "/recover").status_code == 200
    assert operation["stage"] == "confirmed"
    # Lost final response/reload: another attempt returns without provider I/O.
    assert (
        http.post(
            endpoint + "/recover",
            json={
                "auth_user_id": "forged",
                "acceptance_id": "forged",
                "password": "ignored",
            },
        ).status_code
        == 200
    )
    assert client.auth.admin.update_user_by_id.call_args_list == [
        call(AUTH, {"email_confirm": True}),
        call(AUTH, {"email_confirm": True}),
    ]
    read.assert_called_with(client, INV, repo.hash_invitation_token(TOKEN), kind=kind)
    create.assert_not_called()
    reserve.assert_not_called()
    grant.assert_not_called()


@pytest.mark.parametrize(
    "result",
    [
        None,
        {"new_account": False, "stage": "accepted"},
        {"new_account": True, "stage": "provider_started"},
        {"new_account": True, "stage": "reserved"},
    ],
)
def test_recovery_cannot_create_accounts_or_confirm_unvalidated_operations(
    recovery, result
):
    client, _, _, read, create, reserve, grant = recovery
    read.side_effect = None
    read.return_value = result
    response = TestClient(app).post(f"/api/v1/admin-invitations/{TOKEN}/recover")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITATION_RECONCILIATION_REQUIRED"
    client.auth.admin.update_user_by_id.assert_not_called()
    create.assert_not_called()
    reserve.assert_not_called()
    grant.assert_not_called()


def test_concurrent_confirmation_completion_repairs_a_lost_cas_response(
    recovery, monkeypatch
):
    client, _, operation, _, create, _, grant = recovery

    def advance(*a, **k):
        operation["stage"] = "confirmed"
        return None

    monkeypatch.setattr(repo, "advance_operation", advance)
    assert institution.recover_account(TOKEN).role == "admin"
    client.auth.admin.update_user_by_id.assert_called_once_with(
        AUTH, {"email_confirm": True}
    )
    create.assert_not_called()
    grant.assert_not_called()


@pytest.mark.parametrize("path", ["admin-invitations", "super-admin-invitations"])
def test_lost_confirmation_record_response_returns_original_result_on_retry(
    recovery, monkeypatch, path
):
    client, _, operation, _, create, reserve, grant = recovery

    def advance(*a, **k):
        operation["stage"] = "confirmed"
        raise TimeoutError("state committed, response lost")

    monkeypatch.setattr(repo, "advance_operation", advance)
    http = TestClient(app, raise_server_exceptions=False)
    endpoint = f"/api/v1/{path}/{TOKEN}/recover"
    assert http.post(endpoint).status_code == 500
    assert http.post(endpoint).status_code == 200
    client.auth.admin.update_user_by_id.assert_called_once_with(
        AUTH, {"email_confirm": True}
    )
    create.assert_not_called()
    reserve.assert_not_called()
    grant.assert_not_called()
