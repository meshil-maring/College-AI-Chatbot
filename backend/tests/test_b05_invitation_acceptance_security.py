"""Offline service/RPC and SQL source contracts; no database execution.

The threaded test exercises orchestration against a locked RPC fake. It does
not establish PostgreSQL locking, rollback, ACL or deployed-schema behavior.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.repositories.invitations import platform_admin_invitations as repo
from app.repositories.platform import tenancy
from app.schemas.invitations.admin_invitations import AdminInvitationAcceptRequest
from app.services.admin import admin_memberships as memberships
from app.services.invitations import platform_admin_invitations as svc
from app.services.auth import student_registration


@pytest.mark.parametrize("role", ["staff", "faculty", "admin"])
def test_self_or_cross_tenant_role_assignment_cannot_use_platform_route(monkeypatch, role):
    from app.services.platform import platform_institutions

    assign = MagicMock()
    monkeypatch.setattr(platform_institutions.platform_repo, "assign_institution_admin", assign)
    app.dependency_overrides[get_current_user] = lambda: {
        **ACTOR, "roles": [role], "institution_id": INST_ID,
    }
    try:
        http = TestClient(app)
        for institution in (INST_ID, INVITATION_ID):
            response = http.post(f"/api/v1/platform/institutions/{institution}/admins", json={
                "email": ACTOR["email"],
            })
            assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assign.assert_not_called()


def test_assignment_body_cannot_forge_actor_identity(monkeypatch):
    from app.db import supabase
    from app.services.platform import platform_institutions

    assign = MagicMock()
    monkeypatch.setattr(platform_institutions.platform_repo, "assign_institution_admin", assign)
    monkeypatch.setattr(supabase, "get_super_admin_authorization", AsyncMock(return_value={
        "status": "active", "has_platform_grant": True,
    }))
    app.dependency_overrides[get_current_user] = lambda: {**ACTOR, "roles": ["super_admin"]}
    try:
        response = TestClient(app).post(f"/api/v1/platform/institutions/{INST_ID}/admins", json={
            "email": ACTOR["email"], "actor_user_id": INVITATION_ID,
            "actor_auth_user_id": INVITATION_ID,
        })
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 422
    assign.assert_not_called()


@pytest.mark.parametrize("role", ["student", "admin", "super_admin", "", None])
def test_membership_assignment_rejects_invalid_role_before_rpc(role):
    client = MagicMock()
    with pytest.raises(ValueError):
        tenancy.assign_membership_role_audited(
            client, actor_user_id=USER_ID, actor_auth_user_id=AUTH_ID,
            user_id=USER_ID, institution_id=INST_ID, role_name=role,
        )
    client.rpc.assert_not_called()
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

ROOT = Path(__file__).parents[2]
SQL = ROOT / "supabase/migrations/20261017000000_b05_invitation_acceptance_security.sql"
TOKEN = "a" * 64
DIGEST = repo.hash_invitation_token(TOKEN)
INVITATION_ID = "20000000-0000-0000-0000-000000000001"
USER_ID = "30000000-0000-0000-0000-000000000001"
AUTH_ID = "50000000-0000-0000-0000-000000000001"
INST_ID = "40000000-0000-0000-0000-000000000001"
BODY = AdminInvitationAcceptRequest(password="correct-horse-battery")
ACTOR = {"user_id": USER_ID, "auth_user_id": AUTH_ID, "email": "invitee@example.test"}


@pytest.fixture
def deps(monkeypatch):
    client = MagicMock()
    invitation = {
        "invitation_id": INVITATION_ID, "institution_id": INST_ID,
        "email": ACTOR["email"], "role_name": "staff", "status": "invited",
        "expires_at": "2099-01-01T00:00:00Z", "created_by": USER_ID,
    }
    existing = {**ACTOR, "status": "active"}
    monkeypatch.setattr(svc, "get_admin_client", lambda: client)
    monkeypatch.setattr(svc, "_resolve_live_invitation", lambda *_: invitation.copy())
    monkeypatch.setattr(svc, "_require_active_institution", lambda *_: {"name": "Test"})
    monkeypatch.setattr(svc.abuse, "enforce_accept_rate_limit", lambda *_: None)
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: existing)
    def reservation(*a, **k):
        return {"reserved": True, "acceptance_id": str(k["acceptance_id"]),
                "stage": "user_created" if k.get("existing_user_id") else "reserved",
                "user_id": k.get("existing_user_id"), "auth_user_id": k.get("existing_auth_user_id"),
                "new_account": not bool(k.get("existing_user_id"))}
    reserve = MagicMock(side_effect=reservation)
    def advance(*a, **k):
        return {"stage": k["stage"], "auth_user_id": AUTH_ID, "user_id": USER_ID}
    monkeypatch.setattr(repo, "advance_operation", MagicMock(side_effect=advance))
    finalize = MagicMock(return_value={"accepted": True})
    create = MagicMock(return_value=AUTH_ID)
    public = MagicMock(return_value=USER_ID)
    delete = MagicMock()
    monkeypatch.setattr(repo, "reserve_invitation", reserve)
    monkeypatch.setattr(repo, "claim_invitation", finalize)
    monkeypatch.setattr(student_registration, "_create_auth_account", create)
    monkeypatch.setattr(student_registration, "_create_public_user", public)
    monkeypatch.setattr(student_registration, "_try_delete_auth_user", delete)
    monkeypatch.setattr(student_registration, "_try_delete_user_row", delete)
    return client, invitation, reserve, finalize, create, public, delete


@pytest.mark.parametrize("role", ["admin", "staff", "faculty"])
def test_anonymous_existing_account_cannot_change_credentials(deps, role):
    client, invitation, reserve, finalize, create, public, delete = deps
    invitation["role_name"] = role
    with pytest.raises(AppError, match="Sign in") as caught:
        svc.accept_invitation(TOKEN, BODY)
    assert caught.value.code == "ACCOUNT_ALREADY_EXISTS"
    for mock in (reserve, finalize, create, public, delete):
        mock.assert_not_called()
    client.auth.admin.update_user_by_id.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("user_id", INVITATION_ID), ("auth_user_id", INVITATION_ID),
    ("email", "someone@example.test"),
])
def test_authenticated_identity_must_match_canonical_invitee(deps, field, value):
    client, _, reserve, finalize, create, public, delete = deps
    with pytest.raises(AppError) as caught:
        svc.accept_invitation(TOKEN, actor={**ACTOR, field: value})
    assert caught.value.code == "FORBIDDEN"
    for mock in (reserve, finalize, create, public, delete):
        mock.assert_not_called()
    client.auth.admin.update_user_by_id.assert_not_called()


def test_rejected_reservation_does_not_mutate_existing_identity(deps):
    client, _, reserve, finalize, create, public, delete = deps
    # These database decisions have the same fail-closed service contract.
    reserve.side_effect = None
    reserve.return_value = None
    with pytest.raises(AppError) as caught:
        svc.accept_invitation(TOKEN, actor=ACTOR)
    assert caught.value.code == "INVITATION_INVALID"
    assert reserve.call_args.kwargs["token_hash"] == DIGEST
    assert reserve.call_args.kwargs["existing_auth_user_id"] == AUTH_ID
    for mock in (finalize, create, public, delete):
        mock.assert_not_called()
    client.auth.admin.update_user_by_id.assert_not_called()


def test_existing_account_finalization_failure_preserves_identity(deps):
    client, _, reserve, finalize, create, public, delete = deps
    finalize.side_effect = TimeoutError("uncertain database response")
    with pytest.raises(AppError) as caught:
        svc.accept_invitation(TOKEN, actor=ACTOR)
    assert caught.value.code == "INVITATION_RECONCILIATION_REQUIRED"
    assert finalize.call_args.kwargs["acceptance_id"] == str(reserve.call_args.kwargs["acceptance_id"])
    assert finalize.call_args.kwargs["token_hash"] == DIGEST
    for mock in (create, public, delete):
        mock.assert_not_called()
    client.auth.admin.update_user_by_id.assert_not_called()


def test_existing_account_acceptance_uses_no_provider_calls(deps):
    client, _, _reserve, finalize, create, public, delete = deps
    result = svc.accept_invitation(TOKEN, actor=ACTOR)
    assert result.role == "staff" and result.institution_id == UUID(INST_ID)
    assert finalize.call_args.kwargs["accepted_user_id"] == USER_ID
    for mock in (create, public, delete):
        mock.assert_not_called()
    client.auth.assert_not_called()
    assert not client.auth.mock_calls


def test_membership_route_requires_authentication_and_preserves_credentials(deps):
    client, _, _, finalize, _, _, _ = deps
    http = TestClient(app)
    path = f"/api/v1/admin-invitations/{TOKEN}/accept-membership"
    assert http.post(path).status_code == 401
    finalize.assert_not_called()
    app.dependency_overrides[get_current_user] = lambda: ACTOR
    try:
        response = http.post(path)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 201
    assert not client.auth.mock_calls


def test_new_account_reserves_before_provider_and_retains_uncertain_attempt(deps, monkeypatch):
    _client, invitation, reserve, finalize, create, public, delete = deps
    invitation["role_name"] = "admin"
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: None)
    monkeypatch.setattr(svc.platform_repo, "get_user_by_email", lambda *_: None)
    order = []
    reserve.side_effect = lambda *a, **k: order.append("reserve") or {"reserved": True, "acceptance_id": str(k["acceptance_id"]), "stage": "reserved", "new_account": True}
    def uncertain(*a, **k):
        order.append("provider")
        raise TimeoutError("uncertain provider response")
    create.side_effect = uncertain
    with pytest.raises(AppError) as caught:
        svc.accept_invitation(TOKEN, BODY)
    assert caught.value.code == "INVITATION_RECONCILIATION_REQUIRED"
    assert order == ["reserve", "provider"]
    reserve.side_effect = None
    reserve.side_effect = None
    reserve.return_value = None
    with pytest.raises(AppError):
        svc.accept_invitation(TOKEN, BODY)
    assert create.call_count == 1  # No second provider attempt.
    assert create.call_args.kwargs == {"invitation_only": True}
    for mock in (finalize, public, delete):
        mock.assert_not_called()


def test_new_account_confirms_email_only_after_finalization(deps, monkeypatch):
    client, invitation, reserve, finalize, create, public, delete = deps
    invitation["role_name"] = "admin"
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: None)
    monkeypatch.setattr(svc.platform_repo, "get_user_by_email", lambda *_: None)
    order = []
    reserve.side_effect = lambda *a, **k: order.append("reserve") or {"reserved": True, "acceptance_id": str(k["acceptance_id"]), "stage": "reserved", "new_account": True}
    create.side_effect = lambda *a, **k: order.append("create") or AUTH_ID
    def advance(*a, **k):
        if k["stage"] == "user_created": order.append("public")
        return {"stage": k["stage"], "user_id": USER_ID, "auth_user_id": AUTH_ID}
    repo.advance_operation.side_effect = advance
    finalize.side_effect = lambda *a, **k: order.append("finalize") or {"accepted": True}
    client.auth.admin.update_user_by_id.side_effect = lambda *a, **k: order.append("confirm")
    assert svc.accept_invitation(TOKEN, BODY).role == "admin"
    assert order == ["reserve", "create", "public", "finalize", "confirm"]
    client.auth.admin.update_user_by_id.assert_called_once_with(AUTH_ID, {"email_confirm": True})
    delete.assert_not_called()


def test_failed_claim_cannot_confirm_or_delete_a_created_identity(deps, monkeypatch):
    client, invitation, _, finalize, _, _, delete = deps
    invitation["role_name"] = "admin"
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: None)
    monkeypatch.setattr(svc.platform_repo, "get_user_by_email", lambda *_: None)
    finalize.return_value = None
    with pytest.raises(AppError) as caught:
        svc.accept_invitation(TOKEN, BODY)
    assert caught.value.code == "INVITATION_RECONCILIATION_REQUIRED"
    assert not client.auth.mock_calls
    delete.assert_not_called()


def test_post_claim_provider_uncertainty_preserves_durable_acceptance(deps, monkeypatch):
    client, invitation, _, finalize, _, _, delete = deps
    invitation["role_name"] = "admin"
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: None)
    monkeypatch.setattr(svc.platform_repo, "get_user_by_email", lambda *_: None)
    client.auth.admin.update_user_by_id.side_effect = TimeoutError("uncertain confirmation")
    with pytest.raises(AppError) as caught:
        svc.accept_invitation(TOKEN, BODY)
    assert caught.value.code == "INVITATION_EMAIL_CONFIRMATION_UNCERTAIN"
    finalize.assert_called_once()
    delete.assert_not_called()


def test_token_rotated_between_lookup_and_reservation_cannot_create_account(deps, monkeypatch):
    _, invitation, reserve, finalize, create, public, delete = deps
    invitation["role_name"] = "admin"
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: None)
    monkeypatch.setattr(svc.platform_repo, "get_user_by_email", lambda *_: None)
    current_hash = repo.hash_invitation_token("b" * 64)
    def rotated_rpc_fake(*args, token_hash, **kwargs):
        return {"reserved": True} if token_hash == current_hash else None
    reserve.side_effect = rotated_rpc_fake
    with pytest.raises(AppError) as caught:
        svc.accept_invitation(TOKEN, BODY)
    assert caught.value.code == "INVITATION_INVALID"
    for mock in (finalize, create, public, delete):
        mock.assert_not_called()


def test_durable_approval_failure_cannot_confirm_email_even_on_repeat(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(memberships, "get_admin_client", lambda: client)
    monkeypatch.setattr(memberships.repo, "get_request_for_institution", lambda *_: {
        "user_id": USER_ID, "official_email": ACTOR["email"],
        "requested_role": "faculty", "status": "approved",
    })
    monkeypatch.setattr(memberships, "_approved_applicant", lambda *_: ACTOR)
    def denied(*args, **kwargs):
        raise AppError("Unauthorized approval", 403, "FORBIDDEN")
    monkeypatch.setattr(memberships.repo, "approve_and_grant_role", denied)
    with pytest.raises(AppError) as caught:
        memberships.decide_request(ACTOR, UUID(INST_ID), UUID(INVITATION_ID), approve=True, reason=None)
    assert caught.value.code == "FORBIDDEN"
    assert not client.auth.mock_calls


def test_concurrent_acceptances_only_winner_calls_provider(deps, monkeypatch):
    _, invitation, reserve, finalize, create, public, delete = deps
    invitation["role_name"] = "admin"
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: None)
    monkeypatch.setattr(svc.platform_repo, "get_user_by_email", lambda *_: None)
    gate, lock = Barrier(2), Lock()
    reserved_id = None
    def atomic_rpc_fake(*a, **k):
        nonlocal reserved_id
        gate.wait(timeout=5)
        with lock:
            if reserved_id is not None:
                return None
            reserved_id = k["acceptance_id"]
            return {"reserved": True, "acceptance_id": str(k["acceptance_id"]), "stage": "reserved", "new_account": True}
    reserve.side_effect = atomic_rpc_fake
    def accept():
        try:
            return svc.accept_invitation(TOKEN, BODY).role
        except AppError as exc:
            return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: accept(), range(2)))
    assert sorted(outcomes) == ["INVITATION_INVALID", "admin"]
    create.assert_called_once()
    finalize.assert_called_once()
    assert any(call.kwargs["stage"] == "user_created" for call in repo.advance_operation.call_args_list)
    assert finalize.call_args.kwargs["acceptance_id"] == str(reserved_id)
    delete.assert_not_called()


def test_invited_auth_creation_rejects_duplicates_without_mutation(monkeypatch):
    client = MagicMock()
    client.auth.admin.create_user.side_effect = AuthApiError("User already exists", 422, "email_exists")
    monkeypatch.setattr(student_registration, "get_admin_client", lambda: client)
    with pytest.raises(AppError) as caught:
        student_registration._create_auth_account(ACTOR["email"], BODY.password, invitation_only=True)
    assert caught.value.code == "EMAIL_ALREADY_REGISTERED"
    client.auth.admin.create_user.assert_called_once_with({
        "email": ACTOR["email"], "password": BODY.password, "email_confirm": False,
    })
    client.auth.admin.update_user_by_id.assert_not_called()
    client.auth.admin.delete_user.assert_not_called()


def test_reservation_rpc_binds_digest_and_verified_account_without_raw_token():
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = {"reserved": True}
    result = repo.reserve_invitation(
        client, INVITATION_ID, token_hash=DIGEST, acceptance_id=INST_ID,
        existing_user_id=USER_ID, existing_auth_user_id=AUTH_ID,
    )
    assert result == {"reserved": True}
    name, parameters = client.rpc.call_args.args
    assert name == "b05_reserve_invitation"
    assert parameters["p_token_hash"] == DIGEST
    assert parameters["p_existing_user_id"] == USER_ID
    assert parameters["p_existing_auth_user_id"] == AUTH_ID
    assert TOKEN not in str(parameters)
    client.table.assert_not_called()


@pytest.mark.parametrize("result", [
    {"conflict": True}, {"invalid_state": True}, {"not_found": True},
    {"role_granted": False}, {"already_applied": True, "role_granted": False},
])
def test_failed_durable_approval_cannot_confirm_email(monkeypatch, result):
    client = MagicMock()
    monkeypatch.setattr(memberships, "get_admin_client", lambda: client)
    monkeypatch.setattr(memberships.repo, "get_request_for_institution", lambda *_: {
        "user_id": USER_ID, "official_email": ACTOR["email"],
        "requested_role": "staff", "status": "pending",
    })
    monkeypatch.setattr(memberships, "_approved_applicant", lambda *_: ACTOR)
    monkeypatch.setattr(memberships.repo, "approve_and_grant_role", lambda *a, **k: result)
    with pytest.raises(AppError):
        memberships.decide_request(ACTOR, UUID(INST_ID), UUID(INVITATION_ID), approve=True, reason=None)
    client.auth.admin.update_user_by_id.assert_not_called()


def test_sql_contract_pins_generation_after_lock_and_preserves_tenants():
    source = SQL.read_text(encoding="utf-8")
    reserve = source.split("CREATE FUNCTION public.b05_reserve_invitation(", 1)[1].split("$$;", 1)[0]
    finalize = source.split("CREATE FUNCTION public.b05_finalize_invitation(", 1)[1].split("$$;", 1)[0]
    for body in (reserve, finalize):
        assert body.index("FOR UPDATE") < body.index("clock_timestamp()")
        assert "v_invitation.token_hash IS DISTINCT FROM p_token_hash" in body
    assert "v_invitation.acceptance_id IS NOT NULL" in reserve
    assert "v_invitation.acceptance_id IS DISTINCT FROM p_acceptance_id" in finalize
    assert "v_decision_time := clock_timestamp()" in finalize
    assert "RAISE EXCEPTION 'Invitation expired during finalization'" in finalize
    assert "email_verified_at = v_decision_time" in finalize
    assert "institution_admin_invitation_accepted" in finalize
    assert "institution_admin_invitation_verified" in finalize
    assert "ON CONFLICT (user_id, role_id) DO NOTHING" in source
    assert "Existing role belongs to another scope" in source
    assert "acceptance_id\" IS NOT NULL" in source  # Resend guard.
    for table in ("platform_admin_invitations", "platform_super_admin_invitations"):
        assert f"BEFORE UPDATE ON public.{table}" in source
    assert "Finalization RPC required" in source
    assert "Invitation acceptance requires reconciliation" in source


def test_sql_contract_rejects_self_assignment_forgery_and_invalid_roles():
    source = SQL.read_text(encoding="utf-8")
    role_functions = source.split("FUNCTION public.phase81_assign_institution_role_audited(")
    verified = role_functions[1].split("$$;",1)[0]
    assert "CREATE OR REPLACE FUNCTION public.phase81_assign_institution_role_audited(" not in source
    assert "auth_user_id = p_actor_auth_user_id" in verified
    assert "b05_assert_platform_actor(p_actor_user_id)" in verified
    assert "phase81_assert_institution_admin(p_actor_user_id, p_institution_id)" in verified
    assert "mr.status = 'approved'" in verified
    assert "mr.institution_id = p_institution_id" in verified
    assert "Unsupported institution role" in verified
    assert "p_actor_user_id = p_target_user_id" not in verified
    assert "p_actor_user_id <> p_target_user_id" not in verified
    assert "FROM PUBLIC, anon, authenticated, service_role" in source
    assert "DISABLE ROW LEVEL SECURITY" not in source
    assert 'CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_with_invitation"' not in source
    approval = source.split('CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_and_grant_role"', 1)[1]
    assert approval.index('phase81_assert_institution_admin') < approval.index('already_applied')


@pytest.fixture
def durable_attempt(deps, monkeypatch):
    """Orchestration fake only; not evidence of PostgreSQL transactions."""
    client, invitation, reserve, finalize, create, public, delete = deps
    invitation["role_name"] = "admin"
    state = {"op": None, "fault": None, "expired": False}
    monkeypatch.setattr(svc.tenancy_repo, "get_user_by_email", lambda *_: (
        {**ACTOR, "status": "active"} if state["op"] and state["op"].get("user_id") else None
    ))
    monkeypatch.setattr(svc.platform_repo, "get_user_by_email", lambda *_: None)
    monkeypatch.setattr(repo, "get_operation", lambda *_: state["op"].copy())
    def fail(boundary):
        if state["fault"] == boundary:
            state["fault"] = None
            raise TimeoutError(boundary)
    def reserve_op(*a, **k):
        fail("before_reserve")
        if state["op"] is None:
            state["op"] = {"acceptance_id": str(k["acceptance_id"]), "stage": "reserved",
                           "new_account": True, "user_id": None, "auth_user_id": None}
            invitation["acceptance_id"] = state["op"]["acceptance_id"]
        fail("after_reserve")
        return {**state["op"], "reconciliation_required": state["expired"]}
    reserve.side_effect = reserve_op
    def advance(*a, **k):
        fail("before_" + k["stage"])
        if state["op"]["stage"] != k["expected_stage"]:
            return None
        state["op"]["stage"] = k["stage"]
        if k["stage"] == "provider_created": state["op"]["auth_user_id"] = k["auth_user_id"]
        if k["stage"] == "user_created": state["op"]["user_id"] = USER_ID
        fail("after_" + k["stage"])
        return state["op"].copy()
    monkeypatch.setattr(repo, "advance_operation", MagicMock(side_effect=advance))
    def claim(*a, **k):
        fail("before_finalize")
        state["op"]["stage"] = "accepted"
        invitation["status"] = "accepted"
        fail("after_finalize")
        return {"accepted": True}
    finalize.side_effect = claim
    client.auth.admin.update_user_by_id.side_effect = lambda *a: fail("confirmation")
    return state, deps


@pytest.mark.parametrize("boundary,recoverable,provider_calls", [
    ("before_reserve", True, 1), ("after_reserve", True, 1),
    ("before_provider_started", True, 1), ("after_provider_started", False, 0),
    ("before_provider_created", False, 1), ("after_provider_created", True, 1),
    ("before_user_created", True, 1), ("after_user_created", True, 1),
    ("before_finalize", True, 1), ("after_finalize", True, 1),
    ("confirmation", True, 1), ("before_confirmed", True, 1), ("after_confirmed", True, 1),
])
def test_each_interruption_boundary_recovers_or_freezes(durable_attempt, boundary, recoverable, provider_calls):
    state, (_, _, reserve, finalize, create, public, delete) = durable_attempt
    state["fault"] = boundary
    with pytest.raises(AppError):
        svc.accept_invitation(TOKEN, BODY)
    operation_id = state["op"]["acceptance_id"] if state["op"] else None
    if recoverable:
        assert svc.accept_invitation(TOKEN, BODY).role == "admin"
        assert state["op"]["stage"] == "confirmed"
    else:
        with pytest.raises(AppError) as caught:
            svc.accept_invitation(TOKEN, BODY)
        assert caught.value.code == "INVITATION_RECONCILIATION_REQUIRED"
    if operation_id:
        assert str(reserve.call_args.kwargs["acceptance_id"]) == operation_id
    assert create.call_count == provider_calls
    public.assert_not_called()  # Public user provisioning is now a correlated RPC.
    delete.assert_not_called()


def test_expired_reserved_operation_remains_frozen(durable_attempt):
    state, (_, _, _, finalize, create, _, delete) = durable_attempt
    state["fault"] = "after_provider_created"
    with pytest.raises(AppError): svc.accept_invitation(TOKEN, BODY)
    state["expired"] = True
    with pytest.raises(AppError) as caught: svc.accept_invitation(TOKEN, BODY)
    assert caught.value.code == "INVITATION_RECONCILIATION_REQUIRED"
    assert create.call_count == 1
    finalize.assert_not_called()
    delete.assert_not_called()


def test_already_accepted_invitation_is_reachable_via_real_http_retry(durable_attempt, monkeypatch):
    state, (client, invitation, _, finalize, create, _, _) = durable_attempt
    state["fault"] = "after_finalize"
    # Use the actual token resolver, not the shortcut in the shared fixture.
    monkeypatch.setattr(svc, "_resolve_live_invitation", ORIGINAL_TOKEN_RESOLVER)
    monkeypatch.setattr(repo, "get_invitation_by_token_hash", lambda *_: invitation.copy())
    http = TestClient(app)
    path = f"/api/v1/admin-invitations/{TOKEN}/accept"
    assert http.post(path, json=BODY.model_dump()).status_code == 409
    assert http.post(path, json=BODY.model_dump()).status_code == 201
    assert create.call_count == 1 and finalize.call_count == 1
    client.auth.admin.update_user_by_id.assert_called_once_with(AUTH_ID, {"email_confirm": True})


@pytest.mark.parametrize("status,reserved,cancelled,expected", [
    ("invited",False,True,200), ("invited",True,False,409),
    ("invited",True,True,200),  # Only the SQL recovery protocol can affirm this.
    ("accepted",False,False,409), ("expired",False,False,409), ("cancelled",False,True,200),
    ("cancelled",False,False,409),  # Terminal state alone does not prove an audit.
])
def test_cancellation_states(deps, monkeypatch, status, reserved, cancelled, expected):
    _, invitation, *_ = deps
    invitation["status"] = status
    if reserved: invitation["acceptance_id"] = INST_ID
    monkeypatch.setattr(svc, "_require_institution", lambda *_: {})
    monkeypatch.setattr(repo, "get_invitation_by_id", lambda *_: invitation.copy())
    cancel = MagicMock(return_value=cancelled)
    monkeypatch.setattr(repo, "cancel_invitation", cancel)
    monkeypatch.setattr(svc.platform_repo, "record_institution_audit", MagicMock())
    if expected == 409:
        with pytest.raises(AppError) as caught: svc.cancel_invitation(ACTOR, UUID(INST_ID), UUID(INVITATION_ID))
        assert caught.value.code == "INVITATION_CANCELLATION_CONFLICT"
    else:
        result = svc.cancel_invitation(ACTOR, UUID(INST_ID), UUID(INVITATION_ID))
        assert result.already_applied == (status == "cancelled")


@pytest.mark.parametrize("missing", ["audit_persisted", "role_granted"])
def test_repeated_membership_approval_requires_durable_audit_and_grant(deps, monkeypatch, missing):
    client, *_ = deps
    monkeypatch.setattr(memberships, "get_admin_client", lambda: client)
    monkeypatch.setattr(memberships.repo, "get_request_for_institution", lambda *_: {
        "user_id": USER_ID, "official_email": ACTOR["email"], "requested_role": "staff", "status": "approved"})
    monkeypatch.setattr(memberships, "_approved_applicant", lambda *_: ACTOR)
    decision = MagicMock(return_value={"already_applied": True,"role_granted":True,"audit_persisted":True,missing:False})
    monkeypatch.setattr(memberships.repo,"approve_and_grant_role",decision)
    with pytest.raises(AppError):
        memberships.decide_request(ACTOR,UUID(INST_ID),UUID(INVITATION_ID),approve=True,reason=None)
    decision.assert_called_once()
    assert not client.auth.mock_calls


def test_membership_confirmation_failure_retries_the_durable_decision(deps, monkeypatch):
    client, *_ = deps
    monkeypatch.setattr(memberships,"get_admin_client",lambda:client)
    monkeypatch.setattr(memberships.repo,"get_request_for_institution",lambda *_:{
        "user_id":USER_ID,"official_email":ACTOR["email"],"requested_role":"faculty","status":"approved"})
    monkeypatch.setattr(memberships,"_approved_applicant",lambda *_:ACTOR)
    decision = MagicMock(return_value={"already_applied":True,"role_granted":True,"audit_persisted":True})
    monkeypatch.setattr(memberships.repo,"approve_and_grant_role",decision)
    client.auth.admin.update_user_by_id.side_effect = [TimeoutError(), None]
    with pytest.raises(AppError): memberships.decide_request(ACTOR,UUID(INST_ID),UUID(INVITATION_ID),approve=True,reason=None)
    assert memberships.decide_request(ACTOR,UUID(INST_ID),UUID(INVITATION_ID),approve=True,reason=None).already_applied
    assert decision.call_count == 2 and client.auth.admin.update_user_by_id.call_count == 2


ORIGINAL_TOKEN_RESOLVER = svc._resolve_live_invitation


def test_sql_decision_audit_and_recovery_contracts_are_present_not_runtime_proof():
    source = SQL.read_text(encoding="utf-8")
    assert "CREATE UNIQUE INDEX b05_decision_audit_key" in source
    approval = source.split('CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_and_grant_role"',1)[1].split('$$;',1)[0]
    repeated = approval.split('IF "v_request"."status" = \'approved\'',1)[1].split('END IF;',2)[2]
    assert "INSERT INTO public.admin_audit_log" in repeated
    assert "'membership:' || p_request_id::text" in approval
    assert "'audit_persisted', true" in approval
    recovery = source.split("CREATE FUNCTION public.b05_transition_invitation",1)[1].split('$$;',1)[0]
    assert recovery.index("FOR UPDATE") < recovery.index("v_op.stage <> 'reserved'")
    assert "RETURN NULL" in recovery and "b05.recovery_id" in recovery
    wrapper = source.split("CREATE FUNCTION public.b05_close_unstarted_invitation",1)[1].split('$$;',1)[0]
    assert "b05_transition_invitation('institution',p_invitation_id,p_status,NULL)" in wrapper
    # Retained source conventions: explicit file transaction; not an assertion
    # about the actual migration runner or PostgreSQL transaction behavior.
    assert "\nBEGIN;\n" in source and source.rstrip().endswith("COMMIT;")


def test_lost_cancellation_response_reports_reconciliation(deps,monkeypatch):
    _, invitation, *_ = deps
    monkeypatch.setattr(svc,"_require_institution",lambda *_:{})
    monkeypatch.setattr(repo,"get_invitation_by_id",lambda *_:invitation.copy())
    monkeypatch.setattr(repo,"cancel_invitation",MagicMock(side_effect=TimeoutError()))
    with pytest.raises(AppError) as caught:
        svc.cancel_invitation(ACTOR,UUID(INST_ID),UUID(INVITATION_ID))
    assert caught.value.status_code == 409
    assert caught.value.code == "INVITATION_CANCELLATION_UNCERTAIN"
