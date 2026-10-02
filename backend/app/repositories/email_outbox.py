"""Data access for the service-role-only Phase 7.17 email outbox."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client


def _rows(response: Any) -> list[dict[str, Any]]:
    data = response.data if response is not None else None
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict) and row]
    return [data] if isinstance(data, dict) and data else []


def claim_available(
    client: Client, *, batch_size: int, lock_seconds: int, retry_limit: int
) -> list[dict[str, Any]]:
    """Atomically claim jobs with PostgreSQL row locks and SKIP LOCKED."""
    response = client.rpc(
        "phase717_claim_email_outbox",
        {
            "p_batch_size": batch_size,
            "p_lock_seconds": lock_seconds,
            "p_retry_limit": retry_limit,
        },
    ).execute()
    return _rows(response)


def resolve_context(
    client: Client, *, outbox_id: UUID | str, token_hash: str
) -> dict[str, Any] | None:
    """Validate that a claimed job still targets the current invitation token."""
    response = client.rpc(
        "phase717_resolve_email_outbox_context",
        {"p_outbox_id": str(outbox_id), "p_token_hash": token_hash},
    ).execute()
    rows = _rows(response)
    return rows[0] if rows else None


def complete(
    client: Client,
    *,
    outbox_id: UUID | str,
    attempt_number: int,
    outcome: str,
    provider_name: str,
    provider_message_id: str | None = None,
    failure_category: str | None = None,
    available_at: datetime | None = None,
) -> bool:
    """Apply one legal processing outcome and close its attempt atomically."""
    response = client.rpc(
        "phase717_complete_email_outbox",
        {
            "p_outbox_id": str(outbox_id),
            "p_attempt_number": attempt_number,
            "p_outcome": outcome,
            "p_provider_name": provider_name,
            "p_provider_message_id": provider_message_id,
            "p_failure_category": failure_category,
            "p_available_at": available_at.isoformat() if available_at else None,
        },
    ).execute()
    data = response.data if response is not None else None
    if isinstance(data, list):
        data = data[0] if data else False
    return data is True


def reconcile_mailgun_event(
    client: Client,
    *,
    event_key: str,
    replay_token_digest: str,
    provider_event_id: str,
    provider_message_id: str | None,
    event_type: str,
    event_timestamp: datetime,
) -> dict[str, Any]:
    """Atomically deduplicate and reconcile one verified Mailgun event."""
    response = client.rpc(
        "phase718_reconcile_mailgun_event",
        {
            "p_event_key": event_key,
            "p_replay_token_digest": replay_token_digest,
            "p_provider_event_id": provider_event_id,
            "p_provider_message_id": provider_message_id,
            "p_event_type": event_type,
            "p_event_timestamp": event_timestamp.isoformat(),
        },
    ).execute()
    data = response.data if response is not None else None
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict) or not isinstance(data.get("result"), str):
        raise RuntimeError("email event reconciliation returned no result")
    return data
