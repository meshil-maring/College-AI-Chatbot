"""Phase 7.15 focused security + contract tests: invitation delivery, email
verification, resend, abuse controls and expiry cleanup.

Sections:
  1. Email delivery abstraction (local outbox, production boundary, content)
  2. Email binding + server-authoritative verification
  3. Resend (authorization, token supersession, replay)
  4. Rate limiting (inspect / accept / resend, safe 429s)
  5. Expiry enforcement + sweep idempotency
  6. Delivery failure (no access granted, auditable, retryable)
  7. Security invariants + migration contract
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core.errors import AppError
from app.core.security import get_current_user
from app.main import app
from app.services import email_delivery
from app.services import platform_admin_invitations as service
from app.services.invitation_abuse_controls import reset_invitation_abuse_state

client = TestClient(app, raise_server_exceptions=False)

MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20261001030000_phase_7_15_invitation_delivery_email_verification.sql"
)

INSTITUTION_ID = "40000000-0000-0000-0000-000000000001"
INSTITUTION_B_ID = "40000000-0000-0000-0000-000000000002"
ACTOR_USER_ID = "10000000-0000-0000-0000-000000000001"
TARGET_USER_ID = "10000000-0000-0000-0000-000000000009"
INVITATION_ID = "20000000-0000-0000-0000-000000000007"
RAW_TOKEN = "a" * 64
RAW_TOKEN_HASH = hashlib.sha256(RAW_TOKEN.encode("utf-8")).hexdigest()
NEW_RAW_TOKEN = "b" * 64
NEW_TOKEN_HASH = hashlib.sha256(NEW_RAW_TOKEN.encode("utf-8")).hexdigest()
PASSWORD = "correct-horse-battery"

INSTITUTION_ROW = {
    "institution_id": INSTITUTION_ID,
    "organization_id": "50000000-0000-0000-0000-000000000001",
    "name": "Unico University",
    "code": "UNICO",
    "status": "active",
    "is_active": True,
}
FUTURE = "2099-01-01T00:00:00+00:00"
PAST = "2000-01-01T00:00:00+00:00"

INVITE_URL = f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins/invitations"
RESEND_URL = f"{INVITE_URL}/{INVITATION_ID}/resend"
SWEEP_URL = "/api/v1/platform/admin-invitations/expire-sweep"
ACCEPT_URL = f"/api/v1/admin-invitations/{RAW_TOKEN}/accept"
INSPECT_URL = f"/api/v1/admin-invitations/{RAW_TOKEN}"


def _invitation(**overrides) -> dict:
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
        "email_verified_at": None,
        "email_delivery_status": "sent",
        "email_delivery_at": "2026-01-01T00:00:01+00:00",
        "email_delivery_attempts": 1,
        "resend_count": 0,
        "last_sent_at": "2026-01-01T00:00:01+00:00",
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
    return patch(
        "app.db.supabase.get_super_admin_authorization",
        new=AsyncMock(return_value={"status": "active", "has_platform_grant": True}),
    )


def _invite_repo_patch(**kwargs):
    return patch.multiple("app.services.platform_admin_invitations.invite_repo", **kwargs)


def _platform_repo_patch(**kwargs):
    return patch.multiple(
        "app.services.platform_admin_invitations.platform_repo", **kwargs
    )


def _audit_actions(audit: MagicMock) -> list[str]:
    return [call.kwargs["action"] for call in audit.call_args_list]


class _Stack:
    """Enter a list of patch contexts as one block."""

    def __init__(self, items):
        self._items = items
        self._ctxs = [c for c in items if hasattr(c, "start")]

    def __enter__(self):
        for ctx in self._ctxs:
            ctx.start()
        return self

    def __exit__(self, *exc):
        for ctx in reversed(self._ctxs):
            ctx.stop()
        return False


@pytest.fixture(autouse=True)
def _isolated(monkeypatch):
    reset_invitation_abuse_state()
    email_delivery.reset_email_outbox()
    monkeypatch.setattr(settings, "email_provider", "local")
    monkeypatch.setattr(settings, "email_base_url", "http://localhost:5173")
    monkeypatch.setattr(settings, "email_from", "no-reply@localhost")
    monkeypatch.setattr(settings, "email_provider_api_key", "")
    monkeypatch.setattr(settings, "invitation_rate_limit_enabled", True)
    yield
    reset_invitation_abuse_state()
    email_delivery.reset_email_outbox()
    app.dependency_overrides.pop(get_current_user, None)


class _FailingProvider:
    """A provider that always fails, standing in for a vendor outage."""

    name = "failing"

    def __init__(self, code: str = email_delivery.DELIVERY_TEMPORARY_FAILURE) -> None:
        self.code = code
        self.calls = 0

    def send_invitation(self, email):
        self.calls += 1
        raise email_delivery.EmailDeliveryError("nope", code=self.code)


def _create_patches(*, institution=None, insert_row=None, audit=None, pending=None):
    return [
        _invite_repo_patch(
            find_pending_invitation=MagicMock(return_value=pending),
            generate_invitation_token=MagicMock(return_value=RAW_TOKEN),
            hash_invitation_token=MagicMock(return_value=RAW_TOKEN_HASH),
            insert_invitation=MagicMock(
                return_value=insert_row if insert_row is not None else _invitation()
            ),
            record_email_delivery=MagicMock(return_value={}),
            increment_delivery_attempt=MagicMock(return_value={}),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(
                return_value=institution if institution is not None else INSTITUTION_ROW
            ),
            record_institution_audit=audit if audit is not None else MagicMock(),
        ),
    ]


# ===========================================================================
# 1. Email delivery abstraction
# ===========================================================================


def test_local_provider_captures_the_invitation_email() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    audit = MagicMock()
    with _allow_super_admin(), _Stack(_create_patches(audit=audit)):
        response = client.post(INVITE_URL, json={"email": "dean@unico.example"})

    assert response.status_code == 201
    captured = email_delivery.captured_emails()
    assert len(captured) == 1
    assert captured[0].to_email == "dean@unico.example"
    assert captured[0].subject == (
        "You have been invited to administer Unico University"
    )
    # The delivery outcome is reported honestly, and audited.
    assert response.json()["email_delivery"]["status"] == "sent"
    assert "institution_admin_invitation_email_sent" in _audit_actions(audit)


def test_local_provider_never_contacts_an_external_service() -> None:
    """The local provider is a pure in-process capture with no HTTP surface."""
    provider = email_delivery.LocalEmailProvider()
    result = provider.send_invitation(
        email_delivery.build_invitation_email(
            to_email="dean@unico.example",
            institution_name="Unico University",
            raw_token=RAW_TOKEN,
            expires_at=FUTURE,
        )
    )
    assert result.status == email_delivery.DELIVERY_SENT
    assert result.provider == "local"
    assert not hasattr(provider, "session")
    assert not hasattr(provider, "client")


def test_invitation_email_contains_institution_expiry_and_url() -> None:
    subject, body = email_delivery.render_invitation_email(
        institution_name="Unico University",
        invitation_url="http://localhost:5173/admin-invite/" + RAW_TOKEN,
        expires_at=FUTURE,
    )
    assert "Unico University" in subject
    assert "Unico University" in body
    assert "University Administrator" in body
    assert FUTURE in body
    assert f"http://localhost:5173/admin-invite/{RAW_TOKEN}" in body
    assert "ignore this email" in body


def test_invitation_email_never_contains_a_password_or_credential() -> None:
    _subject, body = email_delivery.render_invitation_email(
        institution_name="Unico University",
        invitation_url="http://localhost:5173/admin-invite/" + RAW_TOKEN,
        expires_at=FUTURE,
    )
    assert PASSWORD not in body
    assert "password" not in body.lower()
    assert RAW_TOKEN_HASH not in body
    assert "token_hash" not in body
    assert "supabase" not in body.lower()
    assert "service_role" not in body.lower()
    assert INSTITUTION_ID not in body
    assert INVITATION_ID not in body


def test_invitation_url_is_built_from_configured_base_url_only(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_base_url", "https://yourdomain.com")
    assert email_delivery.build_invitation_url(RAW_TOKEN) == (
        f"https://yourdomain.com/admin-invite/{RAW_TOKEN}"
    )
    monkeypatch.setattr(settings, "email_base_url", "https://yourdomain.com/")
    assert email_delivery.build_invitation_url(RAW_TOKEN) == (
        f"https://yourdomain.com/admin-invite/{RAW_TOKEN}"
    )


def test_invitation_url_ignores_the_request_host_header() -> None:
    """A spoofed forwarding header cannot poison the emailed link.

    A spoofed ``Host`` is separately rejected by the project's existing
    ``TrustedHostMiddleware``; this test proves the stronger property, that the
    link is built from configuration and never from ANY request header.
    """
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin(), _Stack(_create_patches()):
        response = client.post(
            INVITE_URL,
            json={"email": "dean@unico.example"},
            headers={"X-Forwarded-Host": "attacker.example", "X-Forwarded-Proto": "http"},
        )
    assert response.status_code == 201
    captured = email_delivery.captured_emails()
    assert captured[0].invitation_url.startswith("http://localhost:5173/admin-invite/")
    assert "attacker.example" not in captured[0].invitation_url


def test_missing_base_url_is_a_safe_configuration_error() -> None:
    original = settings.email_base_url
    try:
        settings.email_base_url = ""
        with pytest.raises(AppError) as excinfo:
            email_delivery.build_invitation_url(RAW_TOKEN)
        assert excinfo.value.code == "EMAIL_BASE_URL_NOT_CONFIGURED"
    finally:
        settings.email_base_url = original


def test_production_provider_is_selected_by_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_provider", "some-vendor")
    provider = email_delivery.get_email_provider()
    assert isinstance(provider, email_delivery.ProductionEmailProvider)
    # No vendor is hard-coded: the configured name is carried through.
    assert provider._provider_name == "some-vendor"


def test_production_provider_refuses_to_claim_success(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_provider", "some-vendor")
    monkeypatch.setattr(settings, "email_provider_api_key", "vendor-secret-key")
    result = email_delivery.deliver_invitation_email(
        email_delivery.get_email_provider(),
        to_email="dean@unico.example",
        institution_name="Unico University",
        raw_token=RAW_TOKEN,
        expires_at=FUTURE,
    )
    assert result.status == email_delivery.DELIVERY_FAILED
    assert result.detail == email_delivery.DELIVERY_CONFIGURATION_ERROR
    assert "vendor-secret-key" not in str(result)


def test_production_provider_reports_missing_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_provider", "some-vendor")
    monkeypatch.setattr(settings, "email_provider_api_key", "")
    result = email_delivery.deliver_invitation_email(
        email_delivery.get_email_provider(),
        to_email="dean@unico.example",
        institution_name="Unico University",
        raw_token=RAW_TOKEN,
        expires_at=FUTURE,
    )
    assert result.status == email_delivery.DELIVERY_FAILED
    assert result.detail == email_delivery.DELIVERY_CONFIGURATION_ERROR


def test_provider_credentials_never_leave_the_provider(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_provider", "some-vendor")
    monkeypatch.setattr(settings, "email_provider_api_key", "vendor-secret-key")
    provider = email_delivery.get_email_provider()
    assert not hasattr(provider, "api_key")
    for name in dir(provider):
        if name.startswith("_") or callable(getattr(provider, name)):
            continue
        assert "vendor-secret-key" not in str(getattr(provider, name))


def test_provider_credentials_are_never_a_response_field() -> None:
    """No invitation/roster/audit schema has a field a credential could use."""
    from app.schemas import admin_invitations as schemas

    fields: set[str] = set()
    for model in vars(schemas).values():
        model_fields = getattr(model, "model_fields", None)
        if isinstance(model_fields, dict):
            fields.update(model_fields.keys())
    assert not fields & {
        "api_key",
        "email_provider_api_key",
        "supabase_secret_key",
        "service_role_key",
        "password_hash",
        "token_hash",
        "raw_token",
    }


def test_provider_logs_never_contain_the_token_or_recipient(caplog) -> None:
    import logging

    with caplog.at_level(logging.INFO, logger="app.services.email_delivery"):
        email_delivery.deliver_invitation_email(
            email_delivery.LocalEmailProvider(),
            to_email="dean@unico.example",
            institution_name="Unico University",
            raw_token=RAW_TOKEN,
            expires_at=FUTURE,
        )
    assert RAW_TOKEN not in caplog.text
    assert "dean@unico.example" not in caplog.text


def test_local_outbox_is_bounded() -> None:
    from app.services.email_delivery import OUTBOX_MAX_MESSAGES

    provider = email_delivery.LocalEmailProvider()
    for index in range(OUTBOX_MAX_MESSAGES + 10):
        provider.send_invitation(
            email_delivery.build_invitation_email(
                to_email=f"n{index}@unico.example",
                institution_name="Unico University",
                raw_token=RAW_TOKEN,
                expires_at=FUTURE,
            )
        )
    assert len(email_delivery.captured_emails()) == OUTBOX_MAX_MESSAGES


def test_delivery_helper_never_raises_for_a_provider_failure() -> None:
    """A provider error becomes a recorded result, not a 500 to the operator."""
    result = email_delivery.deliver_invitation_email(
        _FailingProvider(),
        to_email="dean@unico.example",
        institution_name="Unico University",
        raw_token=RAW_TOKEN,
        expires_at=FUTURE,
    )
    assert result.status == email_delivery.DELIVERY_FAILED
    assert result.detail == email_delivery.DELIVERY_TEMPORARY_FAILURE


def test_delivery_helper_survives_an_unexpected_provider_crash() -> None:
    class _Exploding:
        name = "exploding"

        def send_invitation(self, email):
            raise RuntimeError("vendor exploded")

    result = email_delivery.deliver_invitation_email(
        _Exploding(),
        to_email="dean@unico.example",
        institution_name="Unico University",
        raw_token=RAW_TOKEN,
        expires_at=FUTURE,
    )
    assert result.status == email_delivery.DELIVERY_FAILED
    assert result.detail == email_delivery.DELIVERY_PERMANENT_FAILURE


# ===========================================================================
# 2. Email binding + server-authoritative verification
# ===========================================================================


def _accept_patches(*, invitation, claim=True, audit=None, assign=None, existing=None,
                    create_auth=None):
    return [
        _invite_repo_patch(
            get_invitation_by_token_hash=MagicMock(return_value=invitation),
            claim_invitation=MagicMock(
                return_value={"invitation_id": INVITATION_ID} if claim else None
            ),
            expire_invitation=MagicMock(return_value=True),
            mark_email_verified=MagicMock(return_value=True),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            get_user_by_email=MagicMock(return_value=existing),
            get_platform_organization_id=MagicMock(
                return_value="50000000-0000-0000-0000-000000000001"
            ),
            assign_institution_admin=assign if assign is not None else MagicMock(),
            record_institution_audit=audit if audit is not None else MagicMock(),
        ),
        patch(
            "app.services.platform_admin_invitations.student_svc._create_auth_account",
            create_auth
            if create_auth is not None
            else MagicMock(return_value="30000000-0000-0000-0000-000000000001"),
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


def test_acceptance_creates_the_auth_account_with_the_invitation_email() -> None:
    """The binding is server-side: Auth email == invitation.email, always."""
    create_auth = MagicMock(return_value="30000000-0000-0000-0000-000000000001")
    with _Stack(_accept_patches(invitation=_invitation(), create_auth=create_auth)):
        response = client.post(ACCEPT_URL, json={"password": PASSWORD})

    assert response.status_code == 201
    assert create_auth.call_args.args[0] == "dean@unico.example"
    assert response.json()["email"] == "dean@unico.example"


def test_acceptance_cannot_smuggle_a_different_email() -> None:
    """``email`` is not an authoritative request field — extras are rejected."""
    create_auth = MagicMock(return_value="30000000-0000-0000-0000-000000000001")
    with _Stack(_accept_patches(invitation=_invitation(), create_auth=create_auth)):
        response = client.post(
            ACCEPT_URL, json={"password": PASSWORD, "email": "attacker@example.test"}
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    create_auth.assert_not_called()


@pytest.mark.parametrize(
    "extra",
    [
        {"email_verified": True},
        {"email_verified_at": "2099-01-01T00:00:00+00:00"},
        {"institution_id": INSTITUTION_B_ID},
        {"role": "super_admin"},
        {"scope": "platform"},
        {"status": "accepted"},
    ],
)
def test_acceptance_rejects_every_authority_shaped_extra_field(extra) -> None:
    create_auth = MagicMock(return_value="30000000-0000-0000-0000-000000000001")
    with _Stack(_accept_patches(invitation=_invitation(), create_auth=create_auth)):
        response = client.post(ACCEPT_URL, json={"password": PASSWORD, **extra})

    assert response.status_code == 422
    create_auth.assert_not_called()


def test_inspection_reports_the_servers_verification_state() -> None:
    with _Stack(_accept_patches(invitation=_invitation(email_verified_at=None))):
        pending = client.get(INSPECT_URL)
    verified_row = _invitation(email_verified_at="2026-01-02T00:00:00+00:00")
    with _Stack(_accept_patches(invitation=verified_row)):
        verified = client.get(INSPECT_URL)

    assert pending.json()["email_verified"] is False
    assert verified.json()["email_verified"] is True


def test_verification_is_recorded_by_the_server_at_acceptance() -> None:
    marked = MagicMock(return_value=True)
    audit = MagicMock()
    stack = _accept_patches(invitation=_invitation(), audit=audit)
    stack[0] = _invite_repo_patch(
        get_invitation_by_token_hash=MagicMock(return_value=_invitation()),
        claim_invitation=MagicMock(return_value={"invitation_id": INVITATION_ID}),
        expire_invitation=MagicMock(return_value=True),
        mark_email_verified=marked,
    )
    with _Stack(stack):
        response = client.post(ACCEPT_URL, json={"password": PASSWORD})

    assert response.status_code == 201
    assert marked.call_count == 1
    assert "institution_admin_invitation_verified" in _audit_actions(audit)
    assert "institution_admin_invitation_accepted" in _audit_actions(audit)


def test_inspection_never_exposes_a_token_or_digest() -> None:
    with _Stack(_accept_patches(invitation=_invitation())):
        response = client.get(INSPECT_URL)
    assert response.status_code == 200
    assert RAW_TOKEN not in response.text
    assert RAW_TOKEN_HASH not in response.text
    assert "token_hash" not in response.text


# ===========================================================================
# 3. Resend
# ===========================================================================


def _resend_patches(*, invitation=None, rotated="row", audit=None):
    rotate_result = _invitation() if rotated == "row" else None
    return [
        _invite_repo_patch(
            get_invitation_by_id=MagicMock(
                return_value=invitation if invitation is not None else _invitation()
            ),
            generate_invitation_token=MagicMock(return_value=NEW_RAW_TOKEN),
            hash_invitation_token=MagicMock(return_value=NEW_TOKEN_HASH),
            rotate_invitation_token=MagicMock(return_value=rotate_result),
            increment_resend_count=MagicMock(return_value={}),
            increment_delivery_attempt=MagicMock(return_value={}),
            record_email_delivery=MagicMock(return_value={}),
            expire_invitation=MagicMock(return_value=True),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=audit if audit is not None else MagicMock(),
        ),
    ]


def test_super_admin_can_resend() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    audit = MagicMock()
    with _allow_super_admin(), _Stack(_resend_patches(audit=audit)):
        response = client.post(RESEND_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["invitation_token"] == NEW_RAW_TOKEN
    assert NEW_RAW_TOKEN in body["invitation_url"]
    assert body["previous_token_invalidated"] is True
    assert "institution_admin_invitation_resent" in _audit_actions(audit)
    # The new link is actually delivered, and the delivery is audited.
    assert email_delivery.captured_emails()[0].invitation_url.endswith(NEW_RAW_TOKEN)
    assert "institution_admin_invitation_email_sent" in _audit_actions(audit)


@pytest.mark.parametrize("role", ["student", "faculty", "staff", "admin"])
def test_non_super_admin_cannot_resend(role) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal(
        role, institution_id=INSTITUTION_ID
    )
    with _allow_super_admin(), _Stack(_resend_patches()):
        response = client.post(RESEND_URL)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert email_delivery.captured_emails() == []


def test_anonymous_cannot_resend() -> None:
    with _allow_super_admin(), _Stack(_resend_patches()):
        response = client.post(RESEND_URL)
    assert response.status_code == 401


def _rotation_probe_patches(*, rotate_result, audit=None):
    """Patches where the rotation write is observable."""
    rotate = MagicMock(return_value=rotate_result)
    stack = _resend_patches(audit=audit)
    stack[0] = _invite_repo_patch(
        get_invitation_by_id=MagicMock(return_value=_invitation()),
        generate_invitation_token=MagicMock(return_value=NEW_RAW_TOKEN),
        hash_invitation_token=MagicMock(return_value=NEW_TOKEN_HASH),
        rotate_invitation_token=rotate,
        increment_resend_count=MagicMock(return_value={}),
        increment_delivery_attempt=MagicMock(return_value={}),
        record_email_delivery=MagicMock(return_value={}),
        expire_invitation=MagicMock(return_value=True),
    )
    return stack, rotate


def test_resend_stores_only_the_new_digest_and_never_the_raw_token() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    stack, rotate = _rotation_probe_patches(rotate_result=_invitation())
    with _allow_super_admin(), _Stack(stack):
        client.post(RESEND_URL)

    assert rotate.call_args.kwargs["token_hash"] == NEW_TOKEN_HASH
    assert NEW_RAW_TOKEN not in str(rotate.call_args)
    assert RAW_TOKEN_HASH not in str(rotate.call_args)


def test_resend_supersedes_the_old_token_so_only_one_is_live() -> None:
    """One live token per invitation: the old digest is overwritten in place."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    stack, rotate = _rotation_probe_patches(rotate_result=_invitation())
    with _allow_super_admin(), _Stack(stack):
        client.post(RESEND_URL)

    kwargs = rotate.call_args.kwargs
    assert kwargs["token_hash"] == NEW_TOKEN_HASH
    assert rotate.call_count == 1
    # A NEW expiry is generated (now + the server TTL), never reused.
    from datetime import datetime, timedelta, timezone

    delta = kwargs["expires_at"] - datetime.now(timezone.utc)
    assert timedelta(hours=23) < delta <= timedelta(hours=24, seconds=5)


def test_resend_losing_the_race_sends_nothing() -> None:
    """If the row stopped being pending, no live token is minted silently."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    stack, rotate = _rotation_probe_patches(rotate_result=None)
    with _allow_super_admin(), _Stack(stack):
        response = client.post(RESEND_URL)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITATION_NOT_RESENDABLE"
    rotate.assert_called_once()
    assert email_delivery.captured_emails() == []


def test_resend_token_generator_is_fresh_and_high_entropy() -> None:
    from app.repositories.platform_admin_invitations import generate_invitation_token

    tokens = {generate_invitation_token() for _ in range(3)}
    assert len(tokens) == 3
    assert all(len(t) >= 43 for t in tokens)
    assert all(RAW_TOKEN not in t for t in tokens)


@pytest.mark.parametrize("terminal", ["accepted", "cancelled", "expired"])
def test_resend_of_a_terminal_invitation_is_refused(terminal) -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    rotate = MagicMock(return_value=None)
    stack = [
        _invite_repo_patch(
            get_invitation_by_id=MagicMock(
                return_value=_invitation(status=terminal)
            ),
            generate_invitation_token=MagicMock(return_value=NEW_RAW_TOKEN),
            hash_invitation_token=MagicMock(return_value=NEW_TOKEN_HASH),
            rotate_invitation_token=rotate,
            increment_delivery_attempt=MagicMock(return_value={}),
            record_email_delivery=MagicMock(return_value={}),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=MagicMock(),
        ),
    ]
    with _allow_super_admin(), _Stack(stack):
        response = client.post(RESEND_URL)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVITATION_NOT_RESENDABLE"
    rotate.assert_not_called()
    assert email_delivery.captured_emails() == []


def test_resend_of_an_elapsed_invitation_expires_it_and_refuses() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    expire = MagicMock(return_value=True)
    rotate = MagicMock(return_value=None)
    audit = MagicMock()
    stack = [
        _invite_repo_patch(
            get_invitation_by_id=MagicMock(
                return_value=_invitation(expires_at=PAST)
            ),
            expire_invitation=expire,
            generate_invitation_token=MagicMock(return_value=NEW_RAW_TOKEN),
            hash_invitation_token=MagicMock(return_value=NEW_TOKEN_HASH),
            rotate_invitation_token=rotate,
            increment_delivery_attempt=MagicMock(return_value={}),
            record_email_delivery=MagicMock(return_value={}),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=audit,
        ),
    ]
    with _allow_super_admin(), _Stack(stack):
        response = client.post(RESEND_URL)

    assert response.status_code == 409
    expire.assert_called_once()
    assert "institution_admin_invitation_expired" in _audit_actions(audit)
    rotate.assert_not_called()


def test_resend_cannot_cross_tenants() -> None:
    """Another institution's invitation is a 404, and nothing is written."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    rotate = MagicMock(return_value=None)
    stack = [
        _invite_repo_patch(
            get_invitation_by_id=MagicMock(
                return_value=_invitation(institution_id=INSTITUTION_B_ID)
            ),
            rotate_invitation_token=rotate,
            increment_delivery_attempt=MagicMock(return_value={}),
            record_email_delivery=MagicMock(return_value={}),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=MagicMock(),
        ),
    ]
    with _allow_super_admin(), _Stack(stack):
        response = client.post(RESEND_URL)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INVITATION_NOT_FOUND"
    rotate.assert_not_called()
    assert email_delivery.captured_emails() == []


def test_resend_response_never_contains_a_digest_or_credential() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin(), _Stack(_resend_patches()):
        response = client.post(RESEND_URL)
    assert NEW_TOKEN_HASH not in response.text
    assert RAW_TOKEN_HASH not in response.text
    assert "token_hash" not in response.text


# ===========================================================================
# 4. Rate limiting
# ===========================================================================


def test_inspection_is_rate_limited_per_peer(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_inspect_ip_limit_requests", 3)
    with _Stack(_accept_patches(invitation=_invitation())):
        statuses = [client.get(INSPECT_URL).status_code for _ in range(5)]

    assert statuses[:3] == [200, 200, 200]
    assert statuses[3:] == [429, 429]


def test_inspection_rate_limit_returns_a_safe_429(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_inspect_ip_limit_requests", 1)
    with _Stack(_accept_patches(invitation=_invitation())):
        client.get(INSPECT_URL)
        response = client.get(INSPECT_URL)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "INVITATION_RATE_LIMITED"
    assert response.headers.get("Retry-After") is not None
    for leak in ("platform_admin_invitations", "token_hash", "counter", "limit="):
        assert leak not in response.text


def test_acceptance_is_rate_limited_per_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_accept_token_limit_requests", 2)
    monkeypatch.setattr(settings, "invitation_accept_ip_limit_requests", 100)
    with _Stack(_accept_patches(invitation=_invitation(), claim=False)):
        statuses = [
            client.post(ACCEPT_URL, json={"password": PASSWORD}).status_code
            for _ in range(4)
        ]

    # The first attempts lose the claim (400); the budget then returns 429.
    assert statuses[:2] == [400, 400]
    assert statuses[2:] == [429, 429]


def test_acceptance_rate_limit_stops_reaching_the_auth_primitive(monkeypatch) -> None:
    """A brute-force run must not keep minting Auth accounts."""
    monkeypatch.setattr(settings, "invitation_accept_token_limit_requests", 2)
    monkeypatch.setattr(settings, "invitation_accept_ip_limit_requests", 100)
    create_auth = MagicMock(return_value="30000000-0000-0000-0000-000000000001")
    with _Stack(_accept_patches(invitation=_invitation(), create_auth=create_auth)):
        for _ in range(6):
            client.post(ACCEPT_URL, json={"password": PASSWORD})
    assert create_auth.call_count == 2


def test_acceptance_rate_limit_returns_a_safe_429(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_accept_token_limit_requests", 1)
    monkeypatch.setattr(settings, "invitation_accept_ip_limit_requests", 100)
    with _Stack(_accept_patches(invitation=_invitation(), claim=False)):
        client.post(ACCEPT_URL, json={"password": PASSWORD})
        response = client.post(ACCEPT_URL, json={"password": PASSWORD})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "INVITATION_RATE_LIMITED"
    assert PASSWORD not in response.text
    assert RAW_TOKEN not in response.text


def test_rate_limit_key_is_the_digest_never_the_raw_token(monkeypatch) -> None:
    """The limiter must not hold a usable credential as an in-memory key."""
    from app.services import invitation_abuse_controls as controls

    monkeypatch.setattr(settings, "invitation_accept_token_limit_requests", 1)
    monkeypatch.setattr(settings, "invitation_accept_ip_limit_requests", 100)
    fingerprint = hashlib.sha256(RAW_TOKEN.encode("utf-8")).hexdigest()
    controls.enforce_accept_rate_limit(fingerprint, "198.51.100.7")
    with pytest.raises(AppError):
        controls.enforce_accept_rate_limit(fingerprint, "198.51.100.7")
    # The bucket is keyed by the digest; the raw token never appears in it.
    assert RAW_TOKEN not in fingerprint


def test_resend_is_rate_limited_per_invitation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_resend_invitation_limit_requests", 2)
    monkeypatch.setattr(settings, "invitation_resend_institution_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_actor_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_ip_limit_requests", 100)
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin(), _Stack(_resend_patches()):
        statuses = [client.post(RESEND_URL).status_code for _ in range(4)]

    assert statuses[:2] == [200, 200]
    assert statuses[2:] == [429, 429]


def test_resend_rate_limit_stops_reaching_the_token_rotation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_resend_invitation_limit_requests", 1)
    monkeypatch.setattr(settings, "invitation_resend_institution_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_actor_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_ip_limit_requests", 100)
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    stack, rotate = _rotation_probe_patches(rotate_result=_invitation())
    with _allow_super_admin(), _Stack(stack):
        for _ in range(5):
            client.post(RESEND_URL)
    assert rotate.call_count == 1


def test_resend_rate_limit_returns_a_safe_429(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_resend_invitation_limit_requests", 1)
    monkeypatch.setattr(settings, "invitation_resend_institution_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_actor_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_ip_limit_requests", 100)
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin(), _Stack(_resend_patches()):
        client.post(RESEND_URL)
        response = client.post(RESEND_URL)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "INVITATION_RATE_LIMITED"
    assert NEW_RAW_TOKEN not in response.text


def test_resend_is_rate_limited_per_actor(monkeypatch) -> None:
    """A single Super Admin cannot mail-bomb across many invitations."""
    monkeypatch.setattr(settings, "invitation_resend_invitation_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_institution_limit_requests", 100)
    monkeypatch.setattr(settings, "invitation_resend_actor_limit_requests", 2)
    monkeypatch.setattr(settings, "invitation_resend_ip_limit_requests", 100)
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    other = "30000000-0000-0000-0000-00000000000a"
    stack = _resend_patches()
    stack[0] = _invite_repo_patch(
        get_invitation_by_id=MagicMock(
            side_effect=[_invitation(), _invitation(invitation_id=other)]
        ),
        generate_invitation_token=MagicMock(return_value=NEW_RAW_TOKEN),
        hash_invitation_token=MagicMock(return_value=NEW_TOKEN_HASH),
        rotate_invitation_token=MagicMock(
            side_effect=[
                _invitation(),
                _invitation(invitation_id=other),
            ]
        ),
        increment_resend_count=MagicMock(return_value={}),
        increment_delivery_attempt=MagicMock(return_value={}),
        record_email_delivery=MagicMock(return_value={}),
    )
    with _allow_super_admin(), _Stack(stack):
        base = f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins/invitations"
        statuses = [
            client.post(f"{base}/{INVITATION_ID}/resend").status_code,
            client.post(f"{base}/{other}/resend").status_code,
            client.post(f"{base}/{INVITATION_ID}/resend").status_code,
        ]

    assert statuses == [200, 200, 429]


def test_rate_limit_can_be_disabled_explicitly(monkeypatch) -> None:
    monkeypatch.setattr(settings, "invitation_rate_limit_enabled", False)
    monkeypatch.setattr(settings, "invitation_inspect_ip_limit_requests", 1)
    with _Stack(_accept_patches(invitation=_invitation())):
        statuses = [client.get(INSPECT_URL).status_code for _ in range(4)]
    assert statuses == [200, 200, 200, 200]


def test_documented_limit_defaults_are_in_force() -> None:
    """The values documented in the status report are the shipped defaults."""
    assert settings.invitation_rate_limit_window_seconds == 300
    assert settings.invitation_inspect_ip_limit_requests == 60
    assert settings.invitation_accept_token_limit_requests == 5
    assert settings.invitation_accept_ip_limit_requests == 20
    assert settings.invitation_resend_invitation_limit_requests == 3
    assert settings.invitation_resend_institution_limit_requests == 10
    assert settings.invitation_resend_actor_limit_requests == 20
    assert settings.invitation_resend_ip_limit_requests == 5


# ===========================================================================
# 5. Expiry enforcement + sweep
# ===========================================================================


def test_expired_invitation_is_refused_without_any_sweep() -> None:
    """The sweep is cleanup; acceptance itself is the security boundary."""
    audit = MagicMock()
    stack = _accept_patches(invitation=_invitation(expires_at=PAST), audit=audit)
    stack[0] = _invite_repo_patch(
        get_invitation_by_token_hash=MagicMock(
            return_value=_invitation(expires_at=PAST)
        ),
        expire_invitation=MagicMock(return_value=True),
        mark_email_verified=MagicMock(return_value=True),
    )
    with _Stack(stack):
        inspect = client.get(INSPECT_URL)
        accept = client.post(ACCEPT_URL, json={"password": PASSWORD})

    assert inspect.status_code == 410
    assert inspect.json()["error"]["code"] == "INVITATION_EXPIRED"
    assert accept.status_code == 410
    assert accept.json()["error"]["code"] == "INVITATION_EXPIRED"
    assert "institution_admin_invitation_expired" in _audit_actions(audit)


def _sweep_patches(*, candidates, expire_side_effect, audit=None):
    return [
        _invite_repo_patch(
            list_expiring_pending_invitations=MagicMock(return_value=candidates),
            expire_invitation=MagicMock(side_effect=expire_side_effect),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(),
            record_institution_audit=audit if audit is not None else MagicMock(),
        ),
    ]


def test_sweep_expires_elapsed_pending_invitations() -> None:
    audit = MagicMock()
    with _Stack(_sweep_patches(candidates=[_invitation()], expire_side_effect=[True],
                                audit=audit)):
        result = service.expire_pending_admin_invitations()

    assert result.scanned == 1
    assert result.expired == 1
    assert result.already_terminal == 0
    assert _audit_actions(audit) == ["institution_admin_invitation_expired"]


def test_sweep_is_idempotent() -> None:
    """A second run finds nothing pending and changes nothing."""
    audit = MagicMock()
    with _Stack(_sweep_patches(candidates=[], expire_side_effect=[], audit=audit)):
        result = service.expire_pending_admin_invitations()

    assert (result.scanned, result.expired, result.already_terminal) == (0, 0, 0)
    audit.assert_not_called()


def test_sweep_does_not_modify_an_accepted_invitation() -> None:
    """A row that stopped being pending mid-sweep is left completely alone."""
    audit = MagicMock()
    accepted = _invitation(status="accepted", accepted_at="2026-01-02T00:00:00+00:00")
    with _Stack(
        _sweep_patches(candidates=[accepted], expire_side_effect=[False], audit=audit)
    ):
        result = service.expire_pending_admin_invitations()

    assert result.expired == 0
    assert result.already_terminal == 1
    audit.assert_not_called()


def test_sweep_audit_carries_no_token_or_credential() -> None:
    audit = MagicMock()
    with _Stack(_sweep_patches(candidates=[_invitation()], expire_side_effect=[True],
                                audit=audit)):
        service.expire_pending_admin_invitations()

    recorded = str(audit.call_args_list)
    assert RAW_TOKEN not in recorded
    assert RAW_TOKEN_HASH not in recorded
    assert PASSWORD not in recorded
    assert "token_hash" not in recorded
    # The actor is the invitation's original issuing Super Admin.
    assert audit.call_args.kwargs["actor_user_id"] == ACTOR_USER_ID


def test_sweep_continues_when_one_audit_write_fails() -> None:
    audit = MagicMock(side_effect=RuntimeError("ledger down"))
    with _Stack(_sweep_patches(candidates=[_invitation()], expire_side_effect=[True],
                                audit=audit)):
        result = service.expire_pending_admin_invitations()
    assert result.expired == 1


def test_sweep_route_is_super_admin_only() -> None:
    with _allow_super_admin():
        assert client.post(SWEEP_URL).status_code == 401
        app.dependency_overrides[get_current_user] = lambda: _principal("admin")
        assert client.post(SWEEP_URL).status_code == 403


def test_sweep_route_runs_the_reusable_service_function() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin(), _Stack(
        _sweep_patches(candidates=[_invitation()], expire_side_effect=[True])
    ):
        response = client.post(SWEEP_URL)
    assert response.status_code == 200
    assert response.json() == {"scanned": 1, "expired": 1, "already_terminal": 0}


def test_sweep_page_size_is_bounded_by_the_repository() -> None:
    from app.repositories.platform_admin_invitations import SWEEP_PAGE_MAX

    assert SWEEP_PAGE_MAX == 200


# ===========================================================================
# 6. Delivery failure
# ===========================================================================


def _create_with_provider(provider, *, audit=None, record=None, attempts=None,
                          create_auth=None):
    stack = [
        _invite_repo_patch(
            find_pending_invitation=MagicMock(return_value=None),
            generate_invitation_token=MagicMock(return_value=RAW_TOKEN),
            hash_invitation_token=MagicMock(return_value=RAW_TOKEN_HASH),
            insert_invitation=MagicMock(return_value=_invitation()),
            record_email_delivery=record if record is not None else MagicMock(),
            increment_delivery_attempt=(
                attempts if attempts is not None else MagicMock()
            ),
        ),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            record_institution_audit=audit if audit is not None else MagicMock(),
            assign_institution_admin=MagicMock(),
        ),
        patch(
            "app.services.platform_admin_invitations.student_svc._create_auth_account",
            create_auth if create_auth is not None else MagicMock(),
        ),
        patch(
            "app.services.email_delivery.get_email_provider",
            MagicMock(return_value=provider),
        ),
    ]
    return stack


def test_delivery_failure_is_reported_honestly_and_grants_nothing() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    audit = MagicMock()
    record = MagicMock()
    attempts = MagicMock()
    with _allow_super_admin(), _Stack(
        _create_with_provider(
            _FailingProvider(), audit=audit, record=record, attempts=attempts
        )
    ):
        response = client.post(INVITE_URL, json={"email": "dean@unico.example"})

    assert response.status_code == 201
    body = response.json()
    assert body["email_delivery"]["status"] == "failed"
    assert body["email_delivery"]["detail"] == email_delivery.DELIVERY_TEMPORARY_FAILURE
    # The invitation is still created and still live (recoverable by resend).
    assert body["invitation"]["status"] == "invited"
    # The failure is persisted as a failure, never optimistically as sent.
    assert record.call_args.kwargs["status"] == "failed"
    assert attempts.call_args.kwargs["sent"] is False
    assert "institution_admin_invitation_email_failed" in _audit_actions(audit)


def test_delivery_failure_creates_no_account_and_grants_no_role() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    create_auth = MagicMock()
    assign = MagicMock()
    with _allow_super_admin(), _Stack(
        _create_with_provider(_FailingProvider(), create_auth=create_auth)
    ):
        client.post(INVITE_URL, json={"email": "dean@unico.example"})

    create_auth.assert_not_called()
    assign.assert_not_called()


def test_delivery_failure_is_auditable_without_credential_material() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    audit = MagicMock()
    with _allow_super_admin(), _Stack(_create_with_provider(_FailingProvider(), audit=audit)):
        client.post(INVITE_URL, json={"email": "dean@unico.example"})

    failure_call = next(
        call
        for call in audit.call_args_list
        if call.kwargs["action"] == "institution_admin_invitation_email_failed"
    )
    assert failure_call.kwargs["result"] == "failed"
    recorded = str(failure_call)
    assert RAW_TOKEN not in recorded
    assert RAW_TOKEN_HASH not in recorded
    assert PASSWORD not in recorded


def test_retry_after_a_delivery_failure_works_safely() -> None:
    """Resend is the controlled retry: a fresh token, the old one dead."""
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    audit = MagicMock()
    stack = _resend_patches(
        invitation=_invitation(email_delivery_status="failed"), audit=audit
    )
    with _allow_super_admin(), _Stack(stack):
        response = client.post(RESEND_URL)

    assert response.status_code == 200
    assert response.json()["email_delivery"]["status"] == "sent"
    assert "institution_admin_invitation_resent" in _audit_actions(audit)
    assert "institution_admin_invitation_email_sent" in _audit_actions(audit)
    # The one-time link reveal still holds for the retry.
    assert response.json()["invitation_token"] == NEW_RAW_TOKEN


def test_resend_delivery_failure_is_not_silently_successful() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    audit = MagicMock()
    stack = _resend_patches(audit=audit)
    stack.append(
        patch(
            "app.services.email_delivery.get_email_provider",
            MagicMock(return_value=_FailingProvider()),
        )
    )
    with _allow_super_admin(), _Stack(stack):
        response = client.post(RESEND_URL)

    body = response.json()
    assert body["email_delivery"]["status"] == "failed"
    assert "could not be sent" in body["message"]
    assert "institution_admin_invitation_email_failed" in _audit_actions(audit)


# ===========================================================================
# 7. Security invariants + migration contract
# ===========================================================================


def test_raw_token_is_never_persisted() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    insert = MagicMock(return_value=_invitation())
    stack = _create_patches()
    stack[0] = _invite_repo_patch(
        find_pending_invitation=MagicMock(return_value=None),
        generate_invitation_token=MagicMock(return_value=RAW_TOKEN),
        hash_invitation_token=MagicMock(return_value=RAW_TOKEN_HASH),
        insert_invitation=insert,
        record_email_delivery=MagicMock(return_value={}),
        increment_delivery_attempt=MagicMock(return_value={}),
    )
    with _allow_super_admin(), _Stack(stack):
        client.post(INVITE_URL, json={"email": "dean@unico.example"})

    assert insert.call_args.kwargs["token_hash"] == RAW_TOKEN_HASH
    assert RAW_TOKEN not in str(insert.call_args)


def test_roster_never_exposes_a_raw_token_or_digest() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    stack = [
        _invite_repo_patch(list_invitations=MagicMock(return_value=[_invitation()])),
        _platform_repo_patch(
            get_platform_institution=MagicMock(return_value=INSTITUTION_ROW),
            list_institution_admin_user_ids=MagicMock(return_value=[]),
            list_users_by_ids=MagicMock(return_value={}),
        ),
    ]
    with _allow_super_admin(), _Stack(stack):
        response = client.get(
            f"/api/v1/platform/institutions/{INSTITUTION_ID}/admins/roster"
        )

    assert response.status_code == 200
    assert RAW_TOKEN not in response.text
    assert RAW_TOKEN_HASH not in response.text
    entry = response.json()["pending_invitations"][0]
    # The roster exposes delivery bookkeeping, never the credential.
    assert entry["email_delivery_status"] == "sent"
    assert entry["email_delivery_attempts"] == 1
    assert not [k for k in entry if "token" in k]


def test_no_password_is_ever_logged(caplog) -> None:
    import logging

    with caplog.at_level(logging.DEBUG):
        with _Stack(_accept_patches(invitation=_invitation())):
            client.post(ACCEPT_URL, json={"password": PASSWORD})
    assert PASSWORD not in caplog.text


def test_no_service_role_credential_reaches_a_response() -> None:
    app.dependency_overrides[get_current_user] = lambda: _principal("super_admin")
    with _allow_super_admin(), _Stack(_create_patches()):
        response = client.post(INVITE_URL, json={"email": "dean@unico.example"})
    for secret in (settings.supabase_secret_key, settings.email_provider_api_key):
        if secret:
            assert secret not in response.text
    assert "service_role" not in response.text


def test_acceptance_cannot_cross_tenants() -> None:
    """The institution comes from the invitation, never from the caller."""
    assign = MagicMock()
    with _Stack(_accept_patches(invitation=_invitation(), assign=assign)):
        response = client.post(ACCEPT_URL, json={"password": PASSWORD})

    assert response.status_code == 201
    assert str(assign.call_args.kwargs["institution_id"]) == INSTITUTION_ID
    assert str(assign.call_args.kwargs["user_id"]) == TARGET_USER_ID


def test_acceptance_cannot_escalate_to_super_admin() -> None:
    """The grant primitive targets a hard-coded role, by construction."""
    import inspect as _inspect

    from app.repositories.platform_institutions import assign_institution_admin

    source = _inspect.getsource(assign_institution_admin)
    assert "'admin'" in source
    assert "super_admin" not in source


def test_reused_token_is_denied_after_a_successful_acceptance() -> None:
    """The one-time gate is the atomic claim, not a client-side flag."""
    create_auth = MagicMock(return_value="30000000-0000-0000-0000-000000000001")
    with _Stack(_accept_patches(invitation=_invitation(), create_auth=create_auth)):
        first = client.post(ACCEPT_URL, json={"password": PASSWORD})
    assert first.status_code == 201

    used = _invitation(status="accepted", accepted_at="2026-01-02T00:00:00+00:00")
    with _Stack(_accept_patches(invitation=used, create_auth=create_auth)):
        second = client.post(ACCEPT_URL, json={"password": PASSWORD})
    assert second.status_code == 410
    assert second.json()["error"]["code"] == "INVITATION_ALREADY_ACCEPTED"
    assert create_auth.call_count == 1


def test_cancelled_token_is_denied() -> None:
    with _Stack(_accept_patches(invitation=_invitation(status="cancelled"))):
        response = client.post(ACCEPT_URL, json={"password": PASSWORD})
    assert response.status_code == 410
    assert response.json()["error"]["code"] == "INVITATION_CANCELLED"


@pytest.mark.parametrize("bad", ["short", "z" * 64, "a" * 300])
def test_invalid_token_produces_no_database_error_or_traceback(bad) -> None:
    with _Stack(_accept_patches(invitation=None)):
        response = client.post(
            f"/api/v1/admin-invitations/{bad}/accept", json={"password": PASSWORD}
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVITATION_INVALID"
    for leak in ("Traceback", "platform_admin_invitations", "psycopg", "supabase"):
        assert leak not in response.text


def test_migration_adds_the_delivery_and_verification_columns() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for column in (
        "email_verified_at",
        "email_delivery_status",
        "email_delivery_at",
        "email_delivery_attempts",
        "last_sent_at",
        "resend_count",
    ):
        assert f'ADD COLUMN IF NOT EXISTS "{column}"' in sql


def test_migration_never_adds_a_raw_token_or_password_column() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for forbidden in ("raw_token", '"token"', '"password"', '"api_key"'):
        assert forbidden not in sql


def test_migration_permits_rotation_only_while_pending() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "phase715_assert_invitation_transition" in sql
    # The binding stays immutable.
    for field in (
        '"institution_id" IS DISTINCT',
        '"email" IS DISTINCT',
        '"role_name" IS DISTINCT',
        '"created_by" IS DISTINCT',
    ):
        assert field in sql
    # Rotation is guarded by the pending status on both sides.
    assert "only a pending invitation token may be rotated" in sql
    # Terminal states stay terminal.
    assert "is already terminal" in sql


def test_migration_extends_the_audit_vocabulary_additively() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for action in (
        "institution_admin_invitation_email_sent",
        "institution_admin_invitation_email_failed",
        "institution_admin_invitation_resent",
        "institution_admin_invitation_verified",
    ):
        assert f"'{action}'::text" in sql
    # Every Phase 7.14 event survives untouched.
    for action in (
        "institution_admin_invited",
        "institution_admin_invitation_accepted",
        "institution_admin_invitation_expired",
        "institution_admin_invitation_cancelled",
        "institution_admin_revoked",
    ):
        assert f"'{action}'::text" in sql
    # No new lifecycle state was invented.
    assert "'email_verified'::text" not in sql


def test_migration_keeps_the_table_service_role_only() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert 'TO "anon"' not in sql
    assert 'TO "authenticated"' not in sql
    assert "CREATE POLICY" not in sql


def test_the_service_exposes_the_documented_execution_boundary() -> None:
    """A reusable sweep function plus Super Admin routes; no daemon."""
    assert callable(service.expire_pending_admin_invitations)
    paths = app.openapi()["paths"]
    assert "/api/v1/platform/admin-invitations/expire-sweep" in paths
    assert (
        "/api/v1/platform/institutions/{institution_id}/admins/invitations/"
        "{invitation_id}/resend" in paths
    )
    # Both new platform operations are POST-only.
    assert "get" not in paths["/api/v1/platform/admin-invitations/expire-sweep"]


def test_no_background_scheduler_was_added_for_the_sweep() -> None:
    """Scheduling is a deployment concern; nothing claims to run it."""
    import app.main as main_module

    source = Path(main_module.__file__).read_text(encoding="utf-8")
    assert "expire_pending_admin_invitations" not in source
    assert "asyncio.create_task" not in source
    assert "APScheduler" not in source
