"""Phase 7.17 durable outbox, worker, retry, and token-security tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import settings
from app.repositories import email_outbox as outbox_repo
from app.services import email_delivery, email_outbox_crypto
from app.services.email_outbox_worker import EmailOutboxWorker

MIGRATION = (
    Path(__file__).parents[2]
    / "supabase"
    / "migrations"
    / "20261002000000_phase_7_17_email_outbox_worker.sql"
)
RAW_TOKEN = "phase717-token-that-must-never-be-stored-in-plaintext-1234567890"
OUTBOX_ID = "77000000-0000-0000-0000-000000000001"


class _Provider:
    name = "test"

    def __init__(self, result: email_delivery.EmailDeliveryResult) -> None:
        self.result = result
        self.messages: list[email_delivery.InvitationEmail] = []

    def send_invitation(
        self, email: email_delivery.InvitationEmail
    ) -> email_delivery.EmailDeliveryResult:
        self.messages.append(email)
        return self.result


def _job(*, attempt: int = 1, protected: str | None = None) -> dict:
    return {
        "id": OUTBOX_ID,
        "aggregate_id": "77000000-0000-0000-0000-000000000002",
        "protected_token": protected or email_outbox_crypto.protect_invitation_token(RAW_TOKEN),
        "attempt_count": attempt,
    }


def _context() -> dict:
    return {
        "invitation_id": "77000000-0000-0000-0000-000000000002",
        "recipient": "dean@example.edu",
        "institution_name": "Example University",
        "expires_at": "2099-01-01T00:00:00+00:00",
    }


def _run(monkeypatch, provider: _Provider, *, job: dict | None = None, context=True):
    claimed = job or _job()
    complete = MagicMock(return_value=True)
    monkeypatch.setattr(outbox_repo, "claim_available", MagicMock(return_value=[claimed]))
    monkeypatch.setattr(
        outbox_repo,
        "resolve_context",
        MagicMock(return_value=_context() if context else None),
    )
    monkeypatch.setattr(outbox_repo, "complete", complete)
    result = EmailOutboxWorker(client=MagicMock(), provider=provider).process_once()
    return result, complete


def test_protected_delivery_secret_round_trips_without_plaintext() -> None:
    protected = email_outbox_crypto.protect_invitation_token(RAW_TOKEN)
    assert RAW_TOKEN not in protected
    assert email_outbox_crypto.recover_invitation_token(protected) == RAW_TOKEN


def test_success_records_provider_message_id_and_stable_outbox_idempotency(monkeypatch) -> None:
    provider = _Provider(
        email_delivery.EmailDeliveryResult(
            "sent", "test", provider_message_id="provider-message-1"
        )
    )
    result, complete = _run(monkeypatch, provider)
    assert result.sent == 1
    assert provider.messages[0].idempotency_key == f"email-outbox:{OUTBOX_ID}"
    assert complete.call_args.kwargs["outcome"] == "sent"
    assert complete.call_args.kwargs["provider_message_id"] == "provider-message-1"


def test_retryable_failure_is_scheduled_without_busy_loop(monkeypatch) -> None:
    provider = _Provider(
        email_delivery.EmailDeliveryResult(
            "failed",
            "test",
            email_delivery.DELIVERY_TIMEOUT,
            retryable=True,
            retry_after_seconds=1,
        )
    )
    result, complete = _run(monkeypatch, provider)
    assert result.retried == 1
    assert complete.call_args.kwargs["outcome"] == "retry"
    assert complete.call_args.kwargs["available_at"] is not None


def test_permanent_failure_becomes_dead_letter(monkeypatch) -> None:
    provider = _Provider(
        email_delivery.EmailDeliveryResult(
            "failed", "test", email_delivery.DELIVERY_PERMANENT_FAILURE
        )
    )
    result, complete = _run(monkeypatch, provider)
    assert result.dead_lettered == 1
    assert complete.call_args.kwargs["outcome"] == "dead_letter"


def test_retry_limit_is_enforced(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_outbox_retry_limit", 3)
    provider = _Provider(
        email_delivery.EmailDeliveryResult(
            "failed", "test", email_delivery.DELIVERY_TIMEOUT, retryable=True
        )
    )
    result, complete = _run(monkeypatch, provider, job=_job(attempt=3))
    assert result.dead_lettered == 1
    assert complete.call_args.kwargs["outcome"] == "dead_letter"


def test_superseded_or_cancelled_invitation_is_never_sent(monkeypatch) -> None:
    provider = _Provider(email_delivery.EmailDeliveryResult("sent", "test"))
    result, complete = _run(monkeypatch, provider, context=False)
    assert result.cancelled == 1
    assert provider.messages == []
    assert complete.call_args.kwargs["outcome"] == "cancelled"


def test_corrupt_ciphertext_fails_closed_without_provider_call(monkeypatch) -> None:
    provider = _Provider(email_delivery.EmailDeliveryResult("sent", "test"))
    result, complete = _run(monkeypatch, provider, job=_job(protected="not-a-ciphertext"))
    assert result.dead_lettered == 1
    assert provider.messages == []
    assert complete.call_args.kwargs["failure_category"] == "EMAIL_OUTBOX_PAYLOAD_INVALID"


def test_claiming_is_database_level_skip_locked_and_stale_leases_recover() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "FOR UPDATE OF o SKIP LOCKED" in sql
    assert "phase717_claim_email_outbox" in sql
    assert "WORKER_LEASE_EXPIRED" in sql
    assert '"locked_at" <= now() - make_interval' in sql
    assert '"attempt_count" >= p_retry_limit' in sql


def test_create_and_resend_are_transactional_database_functions() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "phase717_create_invitation_with_outbox" in sql
    assert "phase717_rotate_invitation_with_outbox" in sql
    assert sql.count('INSERT INTO "public"."email_outbox"') >= 2
    assert "INVITATION_SUPERSEDED" in sql
    assert "A non-stale worker may already be inside provider I/O" in sql


def test_outbox_has_constrained_states_attempt_history_and_service_role_boundary() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    for value in ("pending", "processing", "sent", "dead_letter", "cancelled"):
        assert f"'{value}'::text" in sql
    assert 'CREATE TABLE IF NOT EXISTS "public"."email_delivery_attempts"' in sql
    assert 'ALTER TABLE "public"."email_outbox" ENABLE ROW LEVEL SECURITY' in sql
    assert 'FROM PUBLIC, "anon", "authenticated"' in sql
    assert '"raw_token"' not in sql


def test_no_vendor_webhook_is_exposed_without_authorization() -> None:
    """The provider gate forbids inventing a signature scheme or endpoint."""
    from app.main import app

    assert not [path for path in app.openapi()["paths"] if "/email/webhooks/" in path]


def test_worker_batch_configuration_is_bounded() -> None:
    assert 1 <= settings.email_worker_batch_size <= 200
    assert 30 <= settings.email_worker_lock_seconds <= 3600
    assert 1 <= settings.email_outbox_retry_limit <= 20


def test_production_requires_outbox_encryption_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_outbox_token_encryption_key", "")
    with pytest.raises(Exception) as excinfo:
        email_outbox_crypto.protect_invitation_token(RAW_TOKEN)
    assert getattr(excinfo.value, "code", None) == "EMAIL_OUTBOX_ENCRYPTION_NOT_CONFIGURED"
