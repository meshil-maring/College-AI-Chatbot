from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from app.repositories.invitations import platform_admin_invitations as repo

from .support import INV, USER


@pytest.mark.parametrize("kind", ["institution", "platform"])
@pytest.mark.parametrize("status", ["cancelled", "expired"])
@pytest.mark.parametrize("failure", ["before_audit", "after_commit"])
def test_lifecycle_audit_failure_and_retry_use_one_durable_command(
    kind, status, failure
):
    # This fake models the command's transaction boundary; it cannot prove SQL
    # rollback. It does exercise the real repository adapter and retry result.
    state = {"status": "invited", "events": {}, "decisions": 0, "fault": failure}
    client = MagicMock()

    def rpc(name, params):
        assert name == "b05_transition_invitation"
        assert params == {
            "p_kind": kind,
            "p_id": INV,
            "p_status": status,
            "p_actor": USER,
        }

        def execute():
            candidate = deepcopy(state)
            repeated = candidate["status"] == status
            if not repeated:
                candidate["status"] = status
                candidate["decisions"] += 1
            if state["fault"] == "before_audit":
                state["fault"] = None
                raise RuntimeError("audit insertion failed")
            candidate["events"].setdefault((kind, INV, status), USER)
            candidate["fault"] = None
            state.update(candidate)
            if failure == "after_commit" and not repeated:
                raise TimeoutError("response lost after commit")
            return SimpleNamespace(
                data={
                    "closed": True,
                    "audit_persisted": True,
                    "already_applied": repeated,
                }
            )

        return SimpleNamespace(execute=execute)

    client.rpc.side_effect = rpc
    with pytest.raises((RuntimeError, TimeoutError)):
        repo.transition_invitation(
            client, INV, kind=kind, status=status, actor_user_id=USER
        )
    if failure == "before_audit":
        assert state["status"] == "invited" and not state["events"]
    result = repo.transition_invitation(
        client, INV, kind=kind, status=status, actor_user_id=USER
    )
    assert result["audit_persisted"] is True
    assert (
        state["status"] == status
        and state["decisions"] == 1
        and len(state["events"]) == 1
    )
    # Repair a preexisting terminal state with missing audit, without deciding again.
    state["events"].clear()
    assert repo.transition_invitation(
        client, INV, kind=kind, status=status, actor_user_id=USER
    )["already_applied"]
    assert state["decisions"] == 1 and len(state["events"]) == 1
    client.table.assert_not_called()
