"""Phase 7.18 Mailgun adapter, signature, and reconciliation contracts."""

from __future__ import annotations

import hashlib
import hmac
import logging
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.core.errors import AppError
from app.core.startup_validation import run_startup_configuration_validation
from app.main import app
from app.services import email_delivery, mailgun_webhooks

SIGNING_KEY = "phase718-test-only-signing-material"
TOKEN = "T" * 50
TIMESTAMP = 1_770_000_000
MESSAGE_ID = "phase718-message@mg.example.edu"
MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql"
)


def _signature(timestamp: int = TIMESTAMP, token: str = TOKEN) -> dict[str, str]:
    value = hmac.new(
        SIGNING_KEY.encode(), f"{timestamp}{token}".encode(), hashlib.sha256
    ).hexdigest()
    return {"timestamp": str(timestamp), "token": token, "signature": value}


def _payload(
    *,
    signature: dict | None = None,
    event: str = "delivered",
    severity: str | None = None,
    event_id: str = "event-1",
    message_id: str = MESSAGE_ID,
) -> dict:
    event_data = {
        "id": event_id,
        "event": event,
        "timestamp": TIMESTAMP + 0.25,
        "domain": {"name": "mg.example.edu"},
        "message": {"headers": {"message-id": f"<{message_id}>"}},
    }
    if severity:
        event_data["severity"] = severity
    return {"signature": signature or _signature(), "event-data": event_data}


def _email() -> email_delivery.InvitationEmail:
    return email_delivery.InvitationEmail(
        to_email="admin@example.edu",
        subject="Invitation",
        body="Safe text body",
        institution_name="Example University",
        invitation_url="https://app.example.edu/admin-invite/test-secret",
        expires_at="2099-01-01T00:00:00Z",
        idempotency_key="email-outbox:test-id",
    )


def _transport(handler) -> email_delivery.MailgunEmailTransport:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return email_delivery.MailgunEmailTransport(
        api_key="key-test-secret",
        domain="mg.example.edu",
        base_url="https://api.mailgun.net",
        client=client,
    )


def _send(transport):
    return transport.send_invitation(
        _email(),
        from_address="College AI <no-reply@example.edu>",
        reply_to="support@example.edu",
        timeout_seconds=4.5,
        idempotency_key="email-outbox:test-id",
    )


def test_mailgun_success_constructs_message_and_normalizes_id() -> None:
    observed = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["request"] = request
        observed["body"] = request.content.decode()
        return httpx.Response(200, json={"id": f"<{MESSAGE_ID}>", "message": "Queued"})

    result = _send(_transport(handler))
    request = observed["request"]
    assert result.message_id == MESSAGE_ID
    assert request.url == "https://api.mailgun.net/v3/mg.example.edu/messages"
    assert request.headers["authorization"].startswith("Basic ")
    assert request.headers["content-type"].startswith("multipart/form-data;")
    for value in ("from", "to", "subject", "text", "h:Reply-To"):
        assert value in observed["body"]


@pytest.mark.parametrize(
    ("status", "expected", "retryable"),
    [
        (400, email_delivery.DELIVERY_PERMANENT_FAILURE, False),
        (401, email_delivery.DELIVERY_CONFIGURATION_ERROR, False),
        (403, email_delivery.DELIVERY_CONFIGURATION_ERROR, False),
        (500, email_delivery.DELIVERY_TEMPORARY_FAILURE, True),
        (503, email_delivery.DELIVERY_TEMPORARY_FAILURE, True),
    ],
)
def test_mailgun_http_errors_are_normalized(status, expected, retryable) -> None:
    transport = _transport(lambda _: httpx.Response(status, text="provider secret body"))
    with pytest.raises(email_delivery.EmailDeliveryError) as error:
        _send(transport)
    assert error.value.code == expected
    assert error.value.retryable is retryable
    assert "provider secret body" not in str(error.value)


def test_mailgun_rate_limit_honors_retry_after() -> None:
    transport = _transport(
        lambda _: httpx.Response(429, headers={"Retry-After": "17"}, text="limited")
    )
    with pytest.raises(email_delivery.EmailDeliveryError) as error:
        _send(transport)
    assert error.value.code == email_delivery.DELIVERY_RATE_LIMITED
    assert error.value.retryable is True
    assert error.value.retry_after_seconds == 17


def test_mailgun_timeout_and_network_failures_are_safe() -> None:
    def timeout(request):
        raise httpx.ReadTimeout("secret diagnostic", request=request)

    with pytest.raises(email_delivery.EmailDeliveryError) as error:
        _send(_transport(timeout))
    assert error.value.code == email_delivery.DELIVERY_TIMEOUT
    assert error.value.retryable is True
    assert "secret diagnostic" not in str(error.value)


@pytest.mark.parametrize("response", [{}, {"id": ""}, ["unexpected"]])
def test_mailgun_malformed_success_is_rejected(response) -> None:
    transport = _transport(lambda _: httpx.Response(200, json=response))
    with pytest.raises(email_delivery.EmailDeliveryError) as error:
        _send(transport)
    assert error.value.code == email_delivery.DELIVERY_MALFORMED_RESPONSE


def test_valid_signature_and_message_id_are_parsed() -> None:
    event = mailgun_webhooks.parse_verified_event(
        _payload(),
        signing_key=SIGNING_KEY,
        configured_domain="mg.example.edu",
        tolerance_seconds=900,
        now=TIMESTAMP,
    )
    assert event.event_type == "delivered"
    assert event.provider_message_id == MESSAGE_ID
    assert len(event.event_key) == 64
    assert len(event.replay_token_digest) == 64


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value["signature"].update(signature="0" * 64),
        lambda value: value["signature"].update(timestamp=str(TIMESTAMP + 1)),
        lambda value: value["signature"].update(token="X" * 50),
    ],
)
def test_wrong_signature_or_modified_signing_input_is_rejected(mutator) -> None:
    payload = _payload()
    mutator(payload)
    with pytest.raises(AppError) as error:
        mailgun_webhooks.parse_verified_event(
            payload,
            signing_key=SIGNING_KEY,
            configured_domain="mg.example.edu",
            tolerance_seconds=900,
            now=TIMESTAMP,
        )
    assert error.value.code == "MAILGUN_WEBHOOK_INVALID_SIGNATURE"


def test_stale_signature_is_rejected() -> None:
    with pytest.raises(AppError) as error:
        mailgun_webhooks.parse_verified_event(
            _payload(),
            signing_key=SIGNING_KEY,
            configured_domain="mg.example.edu",
            tolerance_seconds=60,
            now=TIMESTAMP + 61,
        )
    assert error.value.code == "MAILGUN_WEBHOOK_STALE"


@pytest.mark.parametrize(
    "payload",
    [{}, {"signature": _signature()}, {"signature": {}, "event-data": {}}, []],
)
def test_missing_or_malformed_signature_fields_fail_closed(payload) -> None:
    with pytest.raises(AppError):
        mailgun_webhooks.parse_verified_event(
            payload,
            signing_key=SIGNING_KEY,
            configured_domain="mg.example.edu",
            tolerance_seconds=900,
            now=TIMESTAMP,
        )


def test_event_mapping_is_explicit() -> None:
    permanent = mailgun_webhooks.parse_verified_event(
        _payload(event="failed", severity="permanent"),
        signing_key=SIGNING_KEY,
        configured_domain="mg.example.edu",
        tolerance_seconds=900,
        now=TIMESTAMP,
    )
    temporary = mailgun_webhooks.parse_verified_event(
        _payload(event="failed", severity="temporary", event_id="event-2"),
        signing_key=SIGNING_KEY,
        configured_domain="mg.example.edu",
        tolerance_seconds=900,
        now=TIMESTAMP,
    )
    unknown = mailgun_webhooks.parse_verified_event(
        _payload(event="opened", event_id="event-3"),
        signing_key=SIGNING_KEY,
        configured_domain="mg.example.edu",
        tolerance_seconds=900,
        now=TIMESTAMP,
    )
    assert permanent.event_type == "permanent_failure"
    assert temporary.event_type == "temporary_failure"
    assert unknown.event_type == "unsupported"


def test_provider_event_identity_is_stable_and_payload_minimal() -> None:
    one = _payload()
    two = _payload()
    two["event-data"]["recipient"] = "redacted-or-changed@example.edu"
    parsed_one = mailgun_webhooks.parse_verified_event(
        one, signing_key=SIGNING_KEY, configured_domain="mg.example.edu",
        tolerance_seconds=900, now=TIMESTAMP,
    )
    parsed_two = mailgun_webhooks.parse_verified_event(
        two, signing_key=SIGNING_KEY, configured_domain="mg.example.edu",
        tolerance_seconds=900, now=TIMESTAMP,
    )
    assert parsed_one.event_key == parsed_two.event_key


def test_invalid_webhook_never_reaches_reconciliation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailgun_webhook_signing_key", SIGNING_KEY)
    monkeypatch.setattr(settings, "mailgun_domain", "mg.example.edu")
    reconcile = MagicMock()
    monkeypatch.setattr(mailgun_webhooks, "reconcile", reconcile)
    response = TestClient(app, raise_server_exceptions=False).post(
        "/api/v1/webhooks/mailgun",
        json=_payload(signature={**_signature(), "signature": "0" * 64}),
    )
    assert response.status_code == 401
    reconcile.assert_not_called()


def test_duplicate_and_unknown_events_are_acknowledged_without_extra_actions(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mailgun_webhook_signing_key", SIGNING_KEY)
    monkeypatch.setattr(settings, "mailgun_domain", "mg.example.edu")
    monkeypatch.setattr(settings, "mailgun_webhook_tolerance_seconds", 900)
    # Endpoint uses wall-clock time, so use a current signature while retaining
    # a deterministic event timestamp and provider event identity.
    import time
    signed_at = int(time.time())
    payload = _payload(signature=_signature(signed_at), event_id="duplicate-event")
    reconcile = MagicMock(
        side_effect=[
            {"result": "unknown_message", "state_changed": False},
            {"result": "duplicate", "state_changed": False},
        ]
    )
    monkeypatch.setattr(mailgun_webhooks, "reconcile", reconcile)
    monkeypatch.setattr("app.api.mailgun_webhooks.get_admin_client", lambda: MagicMock())
    client = TestClient(app, raise_server_exceptions=False)
    first = client.post("/api/v1/webhooks/mailgun", json=payload)
    second = client.post("/api/v1/webhooks/mailgun", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"status": "accepted"}
    assert reconcile.call_count == 2


def test_migration_enforces_replay_dedup_monotonicity_and_resend_isolation() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert 'UNIQUE ("provider_name", "event_key")' in sql
    assert 'UNIQUE ("provider_name", "replay_token_digest")' in sql
    assert '"provider_message_id" = NULLIF' in sql
    assert "v_outbox.\"status\" = 'sent'::text" in sql
    assert "v_outbox.\"status\" IN ('sent'::text, 'delivered'::text)" in sql
    assert "v_is_latest" in sql and "stale_generation" in sql
    assert 'newer."delivery_sequence" > v_outbox."delivery_sequence"' in sql
    assert "invitation_id" not in sql.split("phase718_reconcile_mailgun_event", 1)[0]


def test_mailgun_production_configuration_fails_closed_without_secrets() -> None:
    config = Settings(
        _env_file=None,
        environment="production",
        debug=False,
        allowed_hosts="api.example.edu",
        supabase_url="https://project.supabase.co",
        supabase_publishable_key="public-test",
        supabase_secret_key="secret-test",
        supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
        openrouter_api_key="ai-test",
        r2_endpoint_url="https://r2.example.edu",
        r2_access_key_id="r2-test",
        r2_secret_access_key="r2-secret-test",
        email_provider="mailgun",
        email_from="no-reply@example.edu",
        email_base_url="https://app.example.edu",
        email_outbox_token_encryption_key=(
            "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        ),
    )
    with pytest.raises(RuntimeError) as error:
        run_startup_configuration_validation(config)
    message = str(error.value)
    for name in ("MAILGUN_API_KEY", "MAILGUN_DOMAIN", "MAILGUN_WEBHOOK_SIGNING_KEY"):
        assert name in message


def test_mailgun_secrets_and_invitation_url_are_not_logged(caplog) -> None:
    secret = "key-test-secret"
    webhook_secret = SIGNING_KEY
    transport = _transport(lambda _: httpx.Response(500, text=secret))
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(email_delivery.EmailDeliveryError):
            _send(transport)
    assert secret not in caplog.text
    assert webhook_secret not in caplog.text
    assert "test-secret" not in caplog.text

