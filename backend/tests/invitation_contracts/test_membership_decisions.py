from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from app.core.errors import AppError
from app.schemas.platform.tenancy import ApprovalDecisionRequest
from app.services.platform import tenancy

from .support import INV, USER, AUTH, INST, ACTOR


@pytest.mark.parametrize(
    "decision,status", [("approve", "approved"), ("reject", "rejected")]
)
def test_legacy_decision_retry_routes_status_and_actor_to_atomic_rpc(
    monkeypatch, decision, status
):
    client = MagicMock()
    monkeypatch.setattr(tenancy, "get_admin_client", lambda: client)
    monkeypatch.setattr(
        tenancy.tenancy_repo,
        "get_membership_request_by_id",
        lambda *_: {"request_id": INV, "institution_id": INST, "status": status},
    )
    monkeypatch.setattr(tenancy, "assert_can_manage_institution", lambda *_: None)
    monkeypatch.setattr(tenancy, "assert_active_tenant_context", lambda *_: None)
    client.rpc.return_value.execute.return_value.data = {
        "decided": True,
        "audit_persisted": True,
        "already_applied": True,
    }
    for _ in range(2):
        assert (
            tenancy.decide_membership_request(
                ACTOR, {}, INV, ApprovalDecisionRequest(decision=decision)
            ).status
            == decision
        )
    assert client.rpc.call_count == 2
    client.rpc.assert_called_with(
        "b05_decide_legacy_membership",
        {
            "p_request_id": INV,
            "p_status": status,
            "p_actor_user_id": USER,
            "p_actor_auth_user_id": AUTH,
            "p_reason": None,
        },
    )
    client.table.assert_not_called()


def test_legacy_decision_missing_audit_never_reports_success(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(tenancy, "get_admin_client", lambda: client)
    monkeypatch.setattr(
        tenancy.tenancy_repo,
        "get_membership_request_by_id",
        lambda *_: {"request_id": INV, "institution_id": INST, "status": "pending"},
    )
    monkeypatch.setattr(tenancy, "assert_can_manage_institution", lambda *_: None)
    monkeypatch.setattr(tenancy, "assert_active_tenant_context", lambda *_: None)
    client.rpc.return_value.execute.return_value.data = {
        "decided": True,
        "audit_persisted": False,
    }
    with pytest.raises(AppError) as caught:
        tenancy.decide_membership_request(
            ACTOR, {}, INV, ApprovalDecisionRequest(decision="approve")
        )
    assert caught.value.code == "MEMBERSHIP_DECISION_CONFLICT"
    client.table.assert_not_called()


@pytest.mark.parametrize("fault", ["grant", "audit", "lost_response"])
def test_legacy_decision_failure_and_retry_preserve_unrelated_grants(
    monkeypatch, fault
):
    client = MagicMock()
    existing = {"user_id": USER, "scope_id": "other-institution", "role": "faculty"}
    state = {
        "row": {"request_id": INV, "institution_id": INST, "status": "pending"},
        "grants": [existing.copy()],
        "audits": {},
        "decisions": 0,
        "fault": fault,
    }
    monkeypatch.setattr(tenancy, "get_admin_client", lambda: client)
    monkeypatch.setattr(
        tenancy.tenancy_repo,
        "get_membership_request_by_id",
        lambda *_: state["row"].copy(),
    )
    monkeypatch.setattr(tenancy, "assert_can_manage_institution", lambda *_: None)
    monkeypatch.setattr(tenancy, "assert_active_tenant_context", lambda *_: None)

    def rpc(name, params):
        assert name == "b05_decide_legacy_membership"

        def execute():
            candidate = deepcopy(state)
            repeated = candidate["row"]["status"] == "approved"
            if not repeated:
                candidate["row"]["status"] = "approved"
                candidate["decisions"] += 1
            if state["fault"] == "grant":
                state["fault"] = None
                raise RuntimeError("grant failed")
            grant = {"user_id": USER, "scope_id": INST, "role": "staff"}
            if grant not in candidate["grants"]:
                candidate["grants"].append(grant)
            if state["fault"] == "audit":
                state["fault"] = None
                raise RuntimeError("audit failed")
            candidate["audits"].setdefault(INV, USER)
            candidate["fault"] = None
            state.update(candidate)
            if fault == "lost_response" and not repeated:
                raise TimeoutError("response lost")
            return SimpleNamespace(
                data={
                    "decided": True,
                    "audit_persisted": True,
                    "already_applied": repeated,
                }
            )

        return SimpleNamespace(execute=execute)

    client.rpc.side_effect = rpc
    with pytest.raises((RuntimeError, TimeoutError)):
        tenancy.decide_membership_request(
            ACTOR, {}, INV, ApprovalDecisionRequest(decision="approve")
        )
    if fault != "lost_response":
        assert (
            state["row"]["status"] == "pending"
            and state["grants"] == [existing]
            and not state["audits"]
        )
    for _ in range(2):
        assert (
            tenancy.decide_membership_request(
                ACTOR, {}, INV, ApprovalDecisionRequest(decision="approve")
            ).status
            == "approve"
        )
    assert existing in state["grants"] and len(state["grants"]) == 2
    assert state["decisions"] == 1 and len(state["audits"]) == 1
    client.table.assert_not_called()
