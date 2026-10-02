"""Focused security + contract tests for the Phase 7.14 University Admin lifecycle.

Covers the acceptance matrix directly:

* Invitation creation: Super Admin allowed; anonymous 401; student / faculty /
  staff / institution admin 403 — on the invite route specifically.
* Invitation lifecycle: valid token accepted; invalid / expired / cancelled /
  reused / suspended-institution tokens all denied, each with a safe error.
* Admin authorization: the accepted admin resolves to institution-scoped
  ``admin``, never ``super_admin``; an Institution A admin cannot reach
  Institution B; a revoked admin is denied.
* Token security: raw token is never persisted, never logged, never audited,
  never replayable, and expiry is enforced server-side.
* Audit: each lifecycle action writes its event; the audit API is Super Admin
  only; there is no audit mutation endpoint anywhere.
* Migration contract: one-time, expiry-bound, service-role-only, no duplicates.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
import inspect
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services.invitation_abuse_controls import reset_invitation_abuse_state

client = TestClient(app, raise_server_exceptions=False)

MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql"
)

INSTITUTION_ID = "40000000-0000-0000-0000-000000000001"
INSTITUTION_B_ID = "40000000-0000-0000-0000-000000000002"
ACTOR_USER_ID = "10000000-0000-0000-0000-000000000001"
TARGET_USER_ID = "10000000-0000-0000-0000-000000000009"
INVITATION_ID = "20000000-0000-0000-0000-000000000007"
ADMIN_ROLE_ID = "71200000-0000-0000-0000-000000000002"
SUPER_ADMIN_ROLE_ID = "71200000-0000-0000-0000-000000000001"

RAW_TOKEN = "a" * 64
RAW_TOKEN_HASH = hashlib.sha256(RAW_TOKEN.encode("utf-8")).hexdigest()

INSTITUTION_ROW = {
    "institution_id": INSTITUTION_ID,
    "organization_id": "50000000-0000-0000-0000-000000000001",
    "name": "Unico University",
    "code": "UNICO",
    "status": "active",
    "is_active": True,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}

FUTURE = "2099-01-01T00:00:00+00:00"
PAST = "2000-01-01T00:00:00+00:00"


def _invitation(**overrides) -> dict:
    """A pending invitation row as the repository would return it."""
    row = {
        "invitation_id": INVITATION_ID,
        "institution_id": INSTITUTION_ID,
        "email": "dean@unico.example",
        "role_name": "admin",
        "status": "invited",
        "expires_at": FUTURE,
        "accepted_at": None,
        "cancelled_at": None,
        "accepted_user_id": None,
        "created_by": ACTOR_USER_ID,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def _principal(role: str, *, institution_id: str | None = None) -> dict:
    return {
        "user_id": ACTOR_USER_ID,
        "auth_user_id": "20000000-0000-0000-0000-000000000001",
        "email": "user@example.test",
        "roles": [role],
        "institution_id": institution_id,
    }


def _allow_super_admin():
    """Mock an active, platform-granted super_admin."""
    return patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
    )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def _isolated_invitation_controls():
    """Keep Phase 7.14 lifecycle assertions independent of rate limiting.

    Phase 7.15 added per-token/per-peer acceptance budgets. They are real
    enforcement, so this suite (which deliberately drives several acceptance
    requests with the SAME token) must reset the process-local limiter around
    each test — exactly the Phase 7.8 convention — rather than have its
    lifecycle assertions become order-dependent. The Phase 7.15 suite tests the
    limits themselves.
    """
    reset_invitation_abuse_state()
    yield
    reset_invitation_abuse_state()


def _invitation_repo_patch(**kwargs):
    """Patch the invitation repository used by the service module."""
    return patch.multiple(
        "app.services.platform_admin_invitations.invite_repo", **kwargs
    )


def _platform_repo_patch(**kwargs):
    """Patch the institution repository used by the service module."""
    return patch.multiple(
        "app.services.platform_admin_invitations.platform_repo", **kwargs
    )


def _audit_actions(audit: MagicMock) -> list[str]:
    """Every audit action this request recorded, in order.

    Phase 7.15 adds additional delivery / verification events alongside the
    Phase 7.14 lifecycle events, so a single ``call_args`` can no longer stand
    for "the audit record of this request". These assertions check the whole
    recorded set instead, which keeps — and in the token-safety cases
    strengthens — the original intent.
    """
    return [call.kwargs["action"] for call in audit.call_args_list]


# ===========================================================================
# 1. Invitation creation authorization
# ===========================================================================

INVITE_URL = f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins/invitations"


def test_anonymous_cannot_create_an_invitation() -> None:
    response = client.post(INVITE_URL, json={"email": "dean@unico.example"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("role", ["student", "faculty", "staff", "admin"])
def test_every_tenant_role_is_forbidden_from_creating_an_invitation(role) -> None:
    """Even the admin of THIS institution cannot invite — platform only."""
    app.dependency_overrides[get_current_user] = lambda: _principal(
        role, institution_id=INSTITUTION_ID
    )
    response = client.post(INVITE_URL, json={"email": "dean@unico.example"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_super_admin_can_create_an_invitation() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    insert = MagicMock(return_value=_invitation())
    audit = MagicMock()
    with (
        _allow_super_admin(),
        _invitation_repo_patch(
            find_pending_invitation=MagicMock(return_value=None),
            generate_invitation_token=MagicMock(return_value=RAW_TOKEN),
            hash_invitation_token=MagicMock(return_value=RAW_TOKEN_HASH),
            insert_invitation=insert,
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=audit,
        ),
    ):
        response = client.post(INVITE_URL, json={"email": "Dean@Unico.Example"})

    assert response.status_code == 201
    body = response.json()
    # Email normalized server-side; bound to exactly ONE institution.
    assert body["invitation"]["email"] == "dean@unico.example"
    assert body["invitation"]["institution_id"] == INSTITUTION_ID
    assert body["invitation"]["status"] == "invited"
    assert body["expires_in_hours"] == 24
    # The raw token is delivered exactly once, in this response only.
    assert body["invitation_token"] == RAW_TOKEN
    assert RAW_TOKEN in body["invitation_url"]
    # No token hash may ever appear in a response.
    assert RAW_TOKEN_HASH not in response.text
    assert "token_hash" not in response.text
    # Only the digest is persisted — never the raw token.
    assert insert.call_args.kwargs["token_hash"] == RAW_TOKEN_HASH
    assert RAW_TOKEN not in str(insert.call_args)
    # Audited, with no token material in the details.
    assert "institution_admin_invited" in _audit_actions(audit)
    assert RAW_TOKEN not in str(audit.call_args_list)
    assert RAW_TOKEN_HASH not in str(audit.call_args_list)


def test_invitation_request_cannot_smuggle_role_or_scope_fields() -> None:
    """role / scope / institution_id / expiry are all unrepresentable."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    for payload in (
        {"email": "a@b.example", "role": "super_admin"},
        {"email": "a@b.example", "role": "staff"},
        {"email": "a@b.example", "institution_id": INSTITUTION_B_ID},
        {"email": "a@b.example", "scope_type": "platform"},
        {"email": "a@b.example", "scope_id": INSTITUTION_B_ID},
        {"email": "a@b.example", "expires_at": FUTURE},
        {"email": "a@b.example", "status": "accepted"},
        {"email": "a@b.example", "password": "Password123!"},
        {"email": "a@b.example", "unexpected": "boom"},
    ):
        with _allow_super_admin():
            response = client.post(INVITE_URL, json=payload)
        assert response.status_code == 422, payload


def test_invitation_role_is_always_the_server_constant() -> None:
    """The repository writes 'admin'; no caller can influence role_name."""
    from app.repositories import platform_admin_invitations as repo

    assert repo.INVITED_ROLE == "admin"
    assert "INVITED_ROLE" in inspect.getsource(repo.insert_invitation)
    assert "role_name" not in inspect.signature(repo.insert_invitation).parameters


def test_invitation_into_an_inactive_institution_is_refused() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    suspended = {**INSTITUTION_ROW, "status": "suspended", "is_active": False}
    insert = MagicMock()
    with (
        _allow_super_admin(),
        _invitation_repo_patch(insert_invitation=insert),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=suspended)
        ),
    ):
        response = client.post(INVITE_URL, json={"email": "dean@unico.example"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSTITUTION_INACTIVE"
    insert.assert_not_called()


def test_duplicate_pending_invitation_is_refused() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    insert = MagicMock()
    with (
        _allow_super_admin(),
        _invitation_repo_patch(
            find_pending_invitation=MagicMock(return_value=_invitation()),
            insert_invitation=insert,
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW)
        ),
    ):
        response = client.post(INVITE_URL, json={"email": "dean@unico.example"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITATION_ALREADY_PENDING"
    # No second live token may be minted.
    insert.assert_not_called()


# ===========================================================================
# 2. Invitation acceptance lifecycle
# ===========================================================================

ACCEPT_URL = f"/api/v1/admin-invitations/{RAW_TOKEN}/accept"
INSPECT_URL = f"/api/v1/admin-invitations/{RAW_TOKEN}"
ACCEPT_BODY = {"password": "correct-horse-battery"}

ACCEPT_PATCHES = [
    "student_svc._create_auth_account",
    "student_svc._create_public_user",
    "student_svc._try_delete_user_row",
    "student_svc._try_delete_auth_user",
]


def _accept_patches(
    *,
    invitation: dict | None,
    institution: dict | None = None,
    claim: bool = True,
    existing_user: dict | None = None,
    assign: MagicMock | None = None,
    audit: MagicMock | None = None,
):
    """Patch every external dependency of the acceptance path.

    ``claim`` controls the atomic single-use gate: True means this request wins
    the claim, False means it loses the race (or the token just expired).
    """
    stack = [
        _invitation_repo_patch(
            get_invitation_by_token_hash=MagicMock(return_value=invitation),
            claim_invitation=MagicMock(
                return_value={"invitation_id": INVITATION_ID} if claim else None
            ),
            expire_invitation=MagicMock(return_value=True),
            mark_email_verified=MagicMock(return_value=True),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(
                return_value=INSTITUTION_ROW if institution is None else institution
            ),
            get_user_by_email=MagicMock(return_value=existing_user),
            get_platform_organization_id=MagicMock(
                return_value="50000000-0000-0000-0000-000000000001"
            ),
            assign_institution_admin=assign if assign is not None else MagicMock(),
            record_institution_audit=audit if audit is not None else MagicMock(),
        ),
        patch(
            "app.services.platform_admin_invitations.student_svc._create_auth_account",
            MagicMock(return_value="30000000-0000-0000-0000-000000000001"),
        ),
        patch(
            "app.services.platform_admin_invitations.student_svc._create_public_user",
            MagicMock(return_value=TARGET_USER_ID),
        ),
        patch(
            "app.services.platform_admin_invitations.student_svc._try_delete_user_row",
            MagicMock(),
        ),
        patch(
            "app.services.platform_admin_invitations.student_svc._try_delete_auth_user",
            MagicMock(),
        ),
    ]
    return stack


def _start_all(stack):
    for ctx in stack:
        ctx.start()


def _stop_all(stack):
    for ctx in reversed(stack):
        ctx.stop()


def test_valid_token_is_accepted_and_grants_institution_scoped_admin() -> None:
    assign = MagicMock()
    audit = MagicMock()
    stack = _accept_patches(invitation=_invitation(), assign=assign, audit=audit)
    _start_all(stack)
    try:
        response = client.post(ACCEPT_URL, json=ACCEPT_BODY)
    finally:
        _stop_all(stack)

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "admin"
    assert body["scope"] == "institution"
    # Institution resolved SERVER-SIDE from the invitation, not from the request.
    assert body["institution_id"] == INSTITUTION_ID
    assert body["email"] == "dean@unico.example"
    # The grant is the fixed institution-scoped admin, via the existing primitive.
    assert str(assign.call_args.kwargs["institution_id"]) == INSTITUTION_ID
    assert str(assign.call_args.kwargs["user_id"]) == TARGET_USER_ID
    assert "organization_id" in assign.call_args.kwargs
    # Audited.
    assert "institution_admin_invitation_accepted" in _audit_actions(audit)
    # No token, hash or password is echoed anywhere.
    assert RAW_TOKEN not in response.text
    assert RAW_TOKEN_HASH not in response.text
    assert ACCEPT_BODY["password"] not in response.text
    assert "super_admin" not in response.text


@pytest.mark.parametrize("token", ["", "short", "x" * 300])
def test_malformed_token_is_denied(token: str) -> None:
    with _invitation_repo_patch(get_invitation_by_token_hash=MagicMock(return_value=None)):
        response = client.post(
            f"/api/v1/admin-invitations/{token}/accept", json=ACCEPT_BODY
        )
    # A malformed token never reaches the hash/lookup step.
    assert response.status_code in (400, 404, 422)


def test_unknown_token_and_expired_token_give_distinct_safe_errors() -> None:
    with _invitation_repo_patch(
        get_invitation_by_token_hash=MagicMock(return_value=None)
    ):
        unknown = client.post(ACCEPT_URL, json=ACCEPT_BODY)

    audit = MagicMock()
    with (
        _invitation_repo_patch(
            get_invitation_by_token_hash=MagicMock(
                return_value=_invitation(expires_at=PAST)
            ),
            expire_invitation=MagicMock(return_value=True),
        ),
        _platform_repo_patch(record_institution_audit=audit),
    ):
        expired = client.post(ACCEPT_URL, json=ACCEPT_BODY)

    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "INVITATION_INVALID"
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "INVITATION_EXPIRED"
    # Expiry is persisted and audited as its own lifecycle event.
    assert "institution_admin_invitation_expired" in _audit_actions(audit)
    # Neither error leaks internal naming.
    for response in (unknown, expired):
        assert "platform_admin_invitations" not in response.text
        assert "SELECT" not in response.text


def test_cancelled_token_cannot_be_accepted() -> None:
    with _invitation_repo_patch(
        get_invitation_by_token_hash=MagicMock(return_value=_invitation(status="cancelled"))
    ):
        response = client.post(ACCEPT_URL, json=ACCEPT_BODY)
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "INVITATION_CANCELLED"


def test_already_accepted_token_cannot_be_replayed() -> None:
    with _invitation_repo_patch(
        get_invitation_by_token_hash=MagicMock(
            return_value=_invitation(status="accepted", accepted_at=FUTURE)
        )
    ):
        response = client.post(ACCEPT_URL, json=ACCEPT_BODY)
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "INVITATION_ALREADY_ACCEPTED"


def test_reused_token_losing_the_atomic_claim_is_denied_and_grants_nothing() -> None:
    """The single-use gate: losing the claim means no account and no role."""
    assign = MagicMock()
    stack = _accept_patches(invitation=_invitation(), claim=False, assign=assign)
    _start_all(stack)
    try:
        response = client.post(ACCEPT_URL, json=ACCEPT_BODY)
    finally:
        _stop_all(stack)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVITATION_INVALID"
    assign.assert_not_called()


def test_acceptance_into_a_suspended_institution_is_denied() -> None:
    suspended = {**INSTITUTION_ROW, "status": "suspended", "is_active": False}
    assign = MagicMock()
    stack = _accept_patches(
        invitation=_invitation(), institution=suspended, assign=assign
    )
    _start_all(stack)
    try:
        response = client.post(ACCEPT_URL, json=ACCEPT_BODY)
    finally:
        _stop_all(stack)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSTITUTION_INACTIVE"
    assign.assert_not_called()


def test_acceptance_cannot_smuggle_role_scope_or_institution() -> None:
    """The acceptance body carries credentials only, never authorization."""
    for payload in (
        {**ACCEPT_BODY, "role": "super_admin"},
        {**ACCEPT_BODY, "institution_id": INSTITUTION_B_ID},
        {**ACCEPT_BODY, "scope_type": "platform"},
        {**ACCEPT_BODY, "user_id": TARGET_USER_ID},
        {**ACCEPT_BODY, "unexpected": "boom"},
    ):
        with _invitation_repo_patch(
            get_invitation_by_token_hash=MagicMock(return_value=None)
        ):
            response = client.post(ACCEPT_URL, json=payload)
        assert response.status_code == 422, payload


def test_acceptance_refuses_an_existing_account() -> None:
    """Re-provisioning is refused; the Phase 7.13 assignment path is signposted."""
    stack = _accept_patches(
        invitation=_invitation(),
        existing_user={"id": TARGET_USER_ID, "email": "dean@unico.example"},
    )
    _start_all(stack)
    try:
        response = client.post(ACCEPT_URL, json=ACCEPT_BODY)
    finally:
        _stop_all(stack)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ACCOUNT_ALREADY_EXISTS"


def test_acceptance_password_never_reaches_a_database_write_or_the_audit() -> None:
    """The password goes only to GoTrue — never into a write or a response."""
    password = "correct-horse-battery"
    audit = MagicMock()
    stack = _accept_patches(invitation=_invitation(), audit=audit)
    _start_all(stack)
    try:
        response = client.post(ACCEPT_URL, json={"password": password})
    finally:
        _stop_all(stack)

    assert response.status_code == 201
    assert password not in str(audit.call_args_list)
    assert password not in response.text


# ===========================================================================
# 3. Invitation inspection (unauthenticated, safe projection)
# ===========================================================================


def test_inspection_returns_only_the_bounded_public_view() -> None:
    with (
        _invitation_repo_patch(
            get_invitation_by_token_hash=MagicMock(return_value=_invitation())
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW)
        ),
    ):
        response = client.get(INSPECT_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["institution_name"] == "Unico University"
    assert body["institution_code"] == "UNICO"
    assert body["status"] == "invited"
    assert body["email"] == "dean@unico.example"
    # Never: token hash, invitation id, user records, audit data or other tenants.
    assert "token_hash" not in body
    assert RAW_TOKEN_HASH not in response.text
    assert "invitation_id" not in body
    assert "user_id" not in body


def test_inspection_of_an_unknown_token_is_a_generic_400() -> None:
    with _invitation_repo_patch(
        get_invitation_by_token_hash=MagicMock(return_value=None)
    ):
        response = client.get(INSPECT_URL)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVITATION_INVALID"
    assert "platform_admin_invitations" not in response.text


# ===========================================================================
# 4. Roster, cancellation and revocation
# ===========================================================================

ROSTER_URL = f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins/roster"
CANCEL_URL = (
    f"/api/v1/platform/institutions/{INSTITUTION_ID}"
    f"/admins/invitations/{INVITATION_ID}/cancel"
)
REVOKE_URL = (
    f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins/{TARGET_USER_ID}/revoke"
)


def test_roster_merges_accepted_admins_and_pending_invitations() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        _invitation_repo_patch(
            list_invitations=MagicMock(
                return_value=[
                    _invitation(),
                    _invitation(invitation_id=uuid.uuid4(), status="expired"),
                    _invitation(invitation_id=uuid.uuid4(), status="accepted"),
                ]
            )
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            list_institution_admin_user_ids=MagicMock(return_value=[TARGET_USER_ID]),
            list_users_by_ids=MagicMock(
                return_value={
                    TARGET_USER_ID: {
                        "id": TARGET_USER_ID,
                        "email": "dean@unico.example",
                        "status": "active",
                    }
                }
            ),
        ),
    ):
        response = client.get(ROSTER_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["admin_count"] == 1
    assert body["admins"][0]["email"] == "dean@unico.example"
    assert body["admins"][0]["user_id"] == TARGET_USER_ID
    # Accepted invitations are represented by their admin row, not duplicated.
    assert len(body["pending_invitations"]) == 2
    assert {row["status"] for row in body["pending_invitations"]} == {
        "invited",
        "expired",
    }
    assert "password" not in response.text and "token_hash" not in response.text


@pytest.mark.parametrize("role", ["student", "faculty", "staff", "admin"])
def test_tenant_roles_are_forbidden_from_roster_cancel_and_revoke(role) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal(
        role, institution_id=INSTITUTION_ID
    )
    for method, url in (
        ("GET", ROSTER_URL),
        ("POST", CANCEL_URL),
        ("POST", REVOKE_URL),
    ):
        response = client.request(method, url)
        assert response.status_code == 403, (method, url)
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_cross_institution_admin_cannot_reach_institution_b() -> None:
    """Institution A's admin can reach neither B's roster, invites nor admins."""
    app.dependency_overrides[get_current_user] = lambda: _principal(
        "admin", institution_id=INSTITUTION_ID
    )
    base = f"/api/v1/platform/institutions/{INSTITUTION_B_ID}"
    cases = [
        ("GET", f"{base}/admins/roster"),
        ("POST", f"{base}/admins/invitations/{INVITATION_ID}/cancel"),
        ("POST", f"{base}/admins/{TARGET_USER_ID}/revoke"),
    ]
    for method, url in cases:
        response = client.request(method, url)
        assert response.status_code == 403, url
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_cancelling_makes_the_token_unusable_and_keeps_the_record() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    cancel = MagicMock(return_value=True)
    audit = MagicMock()
    with (
        _allow_super_admin(),
        _invitation_repo_patch(
            get_invitation_by_id=MagicMock(return_value=_invitation()),
            cancel_invitation=cancel,
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=audit,
        ),
    ):
        response = client.post(CANCEL_URL)

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["already_applied"] is False
    assert audit.call_args.kwargs["action"] == "institution_admin_invitation_cancelled"
    # The invitation row is transitioned, never deleted.
    assert cancel.call_count == 1


def test_cancelling_another_tenants_invitation_is_a_clean_404() -> None:
    """The institution binding is verified before any mutation."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    cancel = MagicMock(return_value=True)
    with (
        _allow_super_admin(),
        _invitation_repo_patch(
            get_invitation_by_id=MagicMock(
                return_value=_invitation(institution_id=INSTITUTION_B_ID)
            ),
            cancel_invitation=cancel,
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW)
        ),
    ):
        response = client.post(CANCEL_URL)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVITATION_NOT_FOUND"
    cancel.assert_not_called()


def test_cancelling_a_consumed_invitation_reports_already_applied() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    audit = MagicMock()
    with (
        _allow_super_admin(),
        _invitation_repo_patch(
            get_invitation_by_id=MagicMock(return_value=_invitation()),
            cancel_invitation=MagicMock(return_value=False),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=audit,
        ),
    ):
        response = client.post(CANCEL_URL)

    assert response.status_code == 200
    assert response.json()["already_applied"] is True
    # A lost race is not re-audited as a fresh cancellation.
    audit.assert_not_called()


def test_revocation_removes_only_the_scoped_admin_grant() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    revoke = MagicMock(return_value=True)
    audit = MagicMock()
    with (
        _allow_super_admin(),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            find_institution_admin_grant=MagicMock(
                return_value={"user_id": TARGET_USER_ID, "scope_id": INSTITUTION_ID}
            ),
            has_platform_super_admin_grant=MagicMock(return_value=False),
            revoke_institution_admin_grant=revoke,
            get_user_by_id=MagicMock(
                return_value={"id": TARGET_USER_ID, "email": "dean@unico.example"}
            ),
            record_institution_audit=audit,
        ),
    ):
        response = client.post(REVOKE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["revoked"] is True
    assert body["already_revoked"] is False
    # Exactly the scoped tuple is targeted.
    assert str(revoke.call_args.kwargs["institution_id"]) == INSTITUTION_ID
    assert str(revoke.call_args.kwargs["user_id"]) == TARGET_USER_ID
    assert audit.call_args.kwargs["action"] == "institution_admin_revoked"


def test_revocation_refuses_to_strip_a_super_admin_grant() -> None:
    """A platform-scoped operator is never downgraded by a tenant action."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    revoke = MagicMock(return_value=True)
    with (
        _allow_super_admin(),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            find_institution_admin_grant=MagicMock(
                return_value={"user_id": TARGET_USER_ID, "scope_id": INSTITUTION_ID}
            ),
            has_platform_super_admin_grant=MagicMock(return_value=True),
            revoke_institution_admin_grant=revoke,
        ),
    ):
        response = client.post(REVOKE_URL)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PLATFORM_ROLE_PRESERVED"
    revoke.assert_not_called()


def test_revoking_a_non_admin_account_here_changes_nothing() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    revoke = MagicMock(return_value=True)
    audit = MagicMock()
    with (
        _allow_super_admin(),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            find_institution_admin_grant=MagicMock(return_value=None),
            revoke_institution_admin_grant=revoke,
            get_user_by_id=MagicMock(
                return_value={"id": TARGET_USER_ID, "email": "someone@unico.example"}
            ),
            record_institution_audit=audit,
        ),
    ):
        response = client.post(REVOKE_URL)

    assert response.status_code == 200
    assert response.json()["revoked"] is False
    assert response.json()["already_revoked"] is True
    revoke.assert_not_called()
    assert audit.call_args.kwargs["result"] == "already_applied"


def test_revocation_of_an_unknown_account_is_a_clean_404() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            find_institution_admin_grant=MagicMock(return_value=None),
            get_user_by_id=MagicMock(return_value=None),
        ),
    ):
        response = client.post(REVOKE_URL)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


def test_revocation_delete_re_asserts_user_role_and_scope() -> None:
    """The DELETE re-checks every component, so it cannot widen by accident."""
    from app.repositories import platform_institutions as repo

    db = MagicMock()
    table = db.table.return_value
    delete = table.delete.return_value
    delete.eq.return_value = delete
    delete.execute.return_value = MagicMock(data=[{"user_id": TARGET_USER_ID}])
    roles = MagicMock()
    roles.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "id": ADMIN_ROLE_ID,
        "name": "admin",
        "is_active": True,
    }
    db.table.side_effect = lambda name: roles if name == "roles" else table

    assert repo.revoke_institution_admin_grant(
        db, user_id=TARGET_USER_ID, institution_id=INSTITUTION_ID
    )
    delete.eq.assert_any_call("user_id", TARGET_USER_ID)
    delete.eq.assert_any_call("role_id", ADMIN_ROLE_ID)
    delete.eq.assert_any_call("scope_type", "institution")
    delete.eq.assert_any_call("scope_id", INSTITUTION_ID)
    # The role lookup pins the TENANT admin role, never super_admin.
    roles.select.return_value.eq.assert_called_with("name", "admin")


# ===========================================================================
# 5. Read-only platform audit
# ===========================================================================

AUDIT_URL = "/api/v1/platform/audit"

AUDIT_ROW = {
    "audit_id": "60000000-0000-0000-0000-000000000001",
    "actor_user_id": ACTOR_USER_ID,
    "action": "institution_admin_invited",
    "institution_id": INSTITUTION_ID,
    "target_user_id": None,
    "result": "success",
    "details": {"email": "dean@unico.example"},
    "performed_at": "2026-10-01T00:00:00+00:00",
}


def _audit_patches(listed: MagicMock | None = None):
    return _platform_repo_patch(
        list_audit_entries=(
            listed if listed is not None else MagicMock(return_value=[])
        ),
        count_audit_entries=MagicMock(return_value=0),
        list_users_by_ids=MagicMock(return_value={}),
    )


def test_audit_endpoint_is_super_admin_only() -> None:
    """anonymous -> 401, every tenant role -> 403, super_admin -> 200."""
    assert client.get(AUDIT_URL).status_code == 401
    for role in ("student", "faculty", "staff", "admin"):
        app.dependency_overrides[get_current_user] = lambda: _principal(
            role, institution_id=INSTITUTION_ID
        )
        response = client.get(AUDIT_URL)
        assert response.status_code == 403, role
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_super_admin_can_read_the_audit_ledger() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with (
        _allow_super_admin(),
        _platform_repo_patch(
            list_audit_entries=MagicMock(return_value=[AUDIT_ROW]),
            count_audit_entries=MagicMock(return_value=1),
            list_users_by_ids=MagicMock(
                return_value={ACTOR_USER_ID: {"email": "root@platform.test"}}
            ),
        ),
        patch(
            "app.services.platform_admin_invitations._institution_name_index",
            MagicMock(
                return_value=[
                    {"institution_id": INSTITUTION_ID, "name": "Unico University"}
                ]
            ),
        ),
    ):
        response = client.get(AUDIT_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    entry = body["entries"][0]
    # The actor is identified, so several Super Admins stay distinguishable.
    assert entry["actor_email"] == "root@platform.test"
    assert entry["institution_name"] == "Unico University"
    assert entry["action"] == "institution_admin_invited"
    assert entry["result"] == "success"


def test_audit_page_size_is_bounded_server_side() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    listed = MagicMock(return_value=[])
    with _allow_super_admin(), _audit_patches(listed):
        response = client.get(f"{AUDIT_URL}?limit=100000&offset=-5")

    assert response.status_code == 200
    assert response.json()["limit"] == 200
    assert response.json()["offset"] == 0
    assert listed.call_args.kwargs["limit"] == 200


def test_audit_endpoint_supports_optional_filters() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    listed = MagicMock(return_value=[])
    with _allow_super_admin(), _audit_patches(listed):
        response = client.get(
            f"{AUDIT_URL}?institution_id={INSTITUTION_ID}"
            "&action=institution_admin_revoked"
            "&date_from=2026-01-01T00:00:00%2B00:00"
            "&date_to=2026-12-31T00:00:00%2B00:00"
        )

    assert response.status_code == 200
    kwargs = listed.call_args.kwargs
    assert str(kwargs["institution_id"]) == INSTITUTION_ID
    assert kwargs["action"] == "institution_admin_revoked"
    assert kwargs["date_from"] is not None and kwargs["date_to"] is not None


def test_no_audit_mutation_endpoint_exists_anywhere() -> None:
    """Every audit route is read-only: no POST/PATCH/PUT/DELETE anywhere.

    The pre-existing tenant-scoped ``/admin/audit-logs`` routes are Phase 7.x
    institution admin audit views and are also GET-only; Phase 7.14 adds exactly
    one new audit route and it is a GET.
    """
    paths = app.openapi()["paths"]
    audit_routes = {
        (method.upper(), path)
        for path, methods in paths.items()
        for method in methods
        if "audit" in path
    }
    mutating = {"POST", "PATCH", "PUT", "DELETE"}
    # Nothing anywhere in the API can mutate an audit record.
    assert audit_routes, "expected at least one audit route"
    for method, _ in audit_routes:
        assert method not in mutating, (method, _)
    # The platform ledger has exactly one route, and it reads.
    platform_audit = {
        (m, p) for m, p in audit_routes if p.startswith("/api/v1/platform/audit")
    }
    assert platform_audit == {("GET", "/api/v1/platform/audit")}


# ===========================================================================
# 6. Token security invariants
# ===========================================================================


def test_tokens_are_cryptographically_random_and_long_enough() -> None:
    from app.repositories import platform_admin_invitations as repo

    tokens = {repo.generate_invitation_token() for _ in range(200)}
    # No collisions across a large sample.
    assert len(tokens) == 200
    for token in tokens:
        # 48 bytes of entropy -> 64 URL-safe characters, no padding/unsafe chars.
        assert len(token) == 64
        assert all(c.isalnum() or c in "-_" for c in token)
    assert "secrets" in inspect.getsource(repo.generate_invitation_token)


def test_only_the_sha256_digest_is_ever_persisted_or_looked_up() -> None:
    from app.repositories import platform_admin_invitations as repo

    digest = repo.hash_invitation_token(RAW_TOKEN)
    assert digest == RAW_TOKEN_HASH
    # Deterministic, and different for any other token.
    assert repo.hash_invitation_token(RAW_TOKEN) == digest
    assert repo.hash_invitation_token(RAW_TOKEN + "x") != digest
    # The repository surface never accepts or returns a raw token.
    for name in ("insert_invitation", "get_invitation_by_token_hash", "claim_invitation"):
        params = set(inspect.signature(getattr(repo, name)).parameters)
        assert "raw_token" not in params
        assert "token" not in params
    # The readable projection deliberately omits the digest column.
    assert "token_hash" not in repo.INVITATION_VIEW_COLUMNS


def test_the_claim_statement_rechecks_status_and_expiry_atomically() -> None:
    """Single-use is enforced by the write itself, not only by a prior read."""
    from app.repositories import platform_admin_invitations as repo

    db = MagicMock()
    table = db.table.return_value
    update = table.update.return_value
    # Chain exactly as the repository does: update -> eq -> eq -> gt -> execute.
    # Both .eq() calls land on the SAME `update` object, and .gt() follows the
    # second one, so the mock must let the second .eq() be observed as such.
    after_first_eq = MagicMock()
    gt_stage = MagicMock()
    after_first_eq.eq.return_value = gt_stage
    update.eq.side_effect = [after_first_eq, gt_stage]
    gt_stage.gt.return_value.execute.return_value = MagicMock(
        data=[{"invitation_id": INVITATION_ID}]
    )

    claimed = repo.claim_invitation(db, INVITATION_ID, accepted_user_id=TARGET_USER_ID)
    assert claimed is not None
    # The single UPDATE is filtered by invitation_id AND status='invited' AND
    # expires_at > now() — one atomic statement, not a read-then-write.
    assert [c.args for c in update.eq.call_args_list] == [
        ("invitation_id", INVITATION_ID),
    ]
    after_first_eq.eq.assert_called_once_with("status", "invited")
    gt = gt_stage.gt
    gt.assert_called_once()
    assert gt.call_args.args[0] == "expires_at"


def test_cancel_and_expire_are_also_conditional_on_pending_status() -> None:
    from app.repositories import platform_admin_invitations as repo

    db = MagicMock()
    table = db.table.return_value
    update = table.update.return_value
    update.eq.return_value = update
    update.execute.return_value = MagicMock(data=[{"invitation_id": INVITATION_ID}])

    assert repo.cancel_invitation(db, INVITATION_ID) is True
    update.eq.assert_any_call("status", "invited")

    assert repo.expire_invitation(db, INVITATION_ID) is True
    update.eq.assert_any_call("status", "invited")


def test_no_frontend_module_can_read_a_service_role_key() -> None:
    """The browser only ever talks to authenticated application APIs."""
    from pathlib import Path

    frontend = Path(__file__).parents[2] / "frontend" / "src"
    forbidden = ("service_role", "supabase_secret", "SUPABASE_SECRET", "eyJ")
    offenders: list[str] = []
    for path in frontend.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in forbidden:
            if needle in text:
                offenders.append(f"{path.name}: {needle}")
    assert offenders == []


def test_the_existing_phase_7_13_assignment_endpoint_is_preserved() -> None:
    """Phase 7.14 supplements the Phase 7.13 assignment capability."""
    paths = app.openapi()["paths"]
    assert "post" in paths["/api/v1/platform/institutions/{institution_id}/admins"]


# ===========================================================================
# 7. Migration contract
# ===========================================================================


def test_migration_adds_only_a_dedicated_invitation_table() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert 'CREATE TABLE IF NOT EXISTS "public"."platform_admin_invitations"' in sql
    # No duplicate user / role / institution / tenant / auth entity.
    for entity in ("users", "roles", "institutions", "organizations", "tenants", "auth"):
        assert f'CREATE TABLE IF NOT EXISTS "public"."{entity}"' not in sql
    # No password or plaintext-token column.
    assert '"password"' not in sql
    assert '"raw_token"' not in sql
    assert '"token"' not in sql


def test_migration_enforces_the_lifecycle_in_the_database() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for constraint in (
        "platform_admin_invitations_status_check",
        "platform_admin_invitations_role_name_check",
        "platform_admin_invitations_token_hash_key",
        "platform_admin_invitations_expiry_check",
        "platform_admin_invitations_terminal_state_check",
        "platform_admin_invitations_token_hash_check",
    ):
        assert constraint in sql
    # The invited role is pinned to 'admin' in a CHECK, not just in Python.
    assert 'CHECK ("role_name" = \'admin\'::text)' in sql
    # Token digests are constrained to lowercase 64-char SHA-256 hex.
    assert "'^[0-9a-f]{64}$'" in sql
    # Foreign keys to the canonical tables.
    assert 'REFERENCES "public"."institutions" ("institution_id")' in sql
    assert 'REFERENCES "public"."users" ("id")' in sql
    # A terminal invitation can never be revived.
    assert "trg_phase714_invitation_transition" in sql
    assert "already terminal" in sql
    assert "invitation identity is immutable" in sql


def test_migration_indexes_are_bounded_and_justified() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    # The token lookup path is served by the UNIQUE constraint's own index, so a
    # second index on the same column would be pure write amplification. Only the
    # three genuinely composite/filtering access paths are indexed separately.
    assert 'CONSTRAINT "platform_admin_invitations_token_hash_key" UNIQUE ("token_hash")' in sql
    assert "platform_admin_invitations_token_hash_idx" not in sql
    for index in (
        "platform_admin_invitations_institution_status_idx",
        "platform_admin_invitations_status_expiry_idx",
        "platform_admin_invitations_email_idx",
        "idx_platform_institution_audit_time",
        "idx_platform_institution_audit_action_time",
    ):
        assert index in sql


def test_migration_is_service_role_only_and_never_mutable() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert 'REVOKE ALL ON TABLE "public"."platform_admin_invitations"' in sql
    assert 'FROM PUBLIC, "anon", "authenticated"' in sql
    assert (
        'GRANT SELECT, INSERT, UPDATE ON TABLE "public"."platform_admin_invitations" '
        'TO "service_role"' in sql
    )
    # The audit ledger is append-only: UPDATE/DELETE are revoked from everyone.
    assert 'REVOKE UPDATE, DELETE ON TABLE "public"."platform_institution_audit_log"' in sql
    # No destructive or Auth-touching operation.
    for destructive in ("DROP TABLE", "DELETE FROM", "TRUNCATE", "auth.users"):
        assert destructive not in sql


def test_migration_extends_the_audit_vocabulary_without_losing_it() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    # The Phase 7.13 vocabulary is preserved...
    for action in (
        "institution_created",
        "institution_updated",
        "institution_suspended",
        "institution_activated",
        "admin_assigned",
    ):
        assert f"'{action}'" in sql
    # ...and the five Phase 7.14 events are added.
    for action in (
        "institution_admin_invited",
        "institution_admin_invitation_accepted",
        "institution_admin_invitation_expired",
        "institution_admin_invitation_cancelled",
        "institution_admin_revoked",
    ):
        assert f"'{action}'" in sql


def test_no_public_or_rag_surface_is_touched_by_this_phase() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "public_chat" not in sql.lower()
    assert "CREATE POLICY" not in sql.upper()
    assert "ENABLE ROW LEVEL SECURITY" not in sql.upper()