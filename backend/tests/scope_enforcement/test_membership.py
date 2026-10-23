"""Test membership."""

from __future__ import annotations

from app.core.errors import AppError

from app.services.auth import authorization as authz

from app.services.platform import tenancy as tenancy_svc

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .database import (
    _db,
)

from .fixtures import (
    _active_institution_authorization,
)

from .state import (
    _base_state,
)

from .support import (
    INST_A,
    INST_ADMIN,
    JR_A,
    MR_A,
    ORG_A,
    ORG_ADMIN,
    ORG_B,
    USER_ADMIN,
    _authz_patches,
    _decision,
    _inst_ctx,
    _login,
    _logout,
    _role_row,
    _user,
    client,
)


def test_01b_org_scoped_admin_decides_own_join_request_endpoint():
    """Org A admin (server-resolved scope) approves its own join request."""
    state = _base_state()  # ORG_A pending (allowed), join request pending
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 200, resp.text
    assert state["institution_join_requests"][JR_A]["status"] == "approved"
    assert state["institutions"][INST_A]["status"] == "active"
    assert state["institutions"][INST_A]["is_active"] is True


def test_02b_org_admin_cannot_decide_another_orgs_join_request_endpoint():
    """Org B admin cannot decide Org A's join request (ID substitution)."""
    state = _base_state()
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_B, ORG_B)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_MISMATCH"
    assert state["institution_join_requests"][JR_A]["status"] == "pending"


def test_20d_rejected_org_admin_denied_on_decision_endpoint():
    """A rejected organization's admin cannot act through the endpoint either."""
    state = _base_state(org_status="rejected")
    _login(_user(None, roles=("admin",), user_id=ORG_ADMIN))
    patches = _authz_patches(ORG_ADMIN, [_role_row(authz.ORGANIZATION, ORG_A, ORG_A)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/institutions/join-requests/{JR_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "ORGANIZATION_INACTIVE"
    assert state["institution_join_requests"][JR_A]["status"] == "pending"


def test_01c_platform_admin_approves_pending_organization():
    """Platform admin keeps the previous authority; the new guard is a no-op."""
    state = _base_state()  # ORG_A pending
    _login(_user(None, roles=("admin",), user_id=USER_ADMIN))
    patches = _authz_patches(USER_ADMIN, [_role_row(authz.PLATFORM, None, None)])
    with (
        patch.object(tenancy_svc, "get_admin_client", return_value=_db(state)),
        patches[0],
        patches[1],
        patches[2],
    ):
        resp = client.post(
            f"/api/v1/organizations/{ORG_A}/decision",
            json=_decision("approve"),
        )
    _logout()
    assert resp.status_code == 200, resp.text
    assert state["organizations"][ORG_A]["status"] == "active"


def test_03b_institution_admin_membership_decision_lifecycle():
    """Institution admin: ACTIVE institution allows, PENDING denies (service)."""
    from app.schemas.platform.tenancy import ApprovalDecisionRequest

    current_user = {
        "user_id": INST_ADMIN,
        "auth_user_id": INST_ADMIN,
        "institution_id": None,
    }
    ctx = _inst_ctx()

    # ACTIVE institution: membership approval succeeds and grants the role.
    state = _base_state(inst_status="active", inst_active=True)
    db = _db(state)
    db.rpc.return_value.execute.return_value.data = {
        "decided": True,
        "audit_persisted": True,
        "already_applied": False,
    }
    with patch.object(tenancy_svc, "get_admin_client", return_value=db):
        response = tenancy_svc.decide_membership_request(
            current_user,
            ctx,
            MR_A,
            ApprovalDecisionRequest(decision="approve"),
        )
    assert response.status == "approve"
    # A service test does not execute SQL; the row stays pending in this fake.
    assert state["institution_membership_requests"][MR_A]["status"] == "pending"
    db.rpc.assert_called_once_with(
        "b05_decide_legacy_membership",
        {
            "p_request_id": MR_A,
            "p_status": "approved",
            "p_reason": None,
            "p_actor_user_id": INST_ADMIN,
            "p_actor_auth_user_id": INST_ADMIN,
        },
    )

    # PENDING institution: fail closed BEFORE any write.
    state_pending = _base_state(inst_status="pending")
    with patch.object(tenancy_svc, "get_admin_client", return_value=_db(state_pending)):
        with pytest.raises(AppError) as excinfo:
            tenancy_svc.decide_membership_request(
                current_user,
                ctx,
                MR_A,
                ApprovalDecisionRequest(decision="approve"),
            )
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "TENANT_INACTIVE"
    assert state_pending["institution_membership_requests"][MR_A]["status"] == "pending"
    assert state_pending["user_roles"] == []
