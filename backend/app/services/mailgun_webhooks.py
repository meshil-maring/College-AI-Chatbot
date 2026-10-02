"""Verified Mailgun webhook parsing and durable delivery reconciliation."""

from __future__ import annotations

import hashlib
import hmac
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.core.errors import AppError
from app.repositories import email_outbox
from app.services.email_delivery import normalize_provider_message_id

_HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_SUPPORTED_TYPES = frozenset(
    {
        "accepted",
        "delivered",
        "permanent_failure",
        "temporary_failure",
        "rejected",
        "complained",
    }
)


@dataclass(frozen=True)
class VerifiedMailgunEvent:
    event_key: str
    replay_token_digest: str
    provider_event_id: str
    provider_message_id: str | None
    event_type: str
    event_timestamp: datetime


def _text(value: Any, *, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    return value if 0 < len(value) <= maximum else ""


def _signature_timestamp(value: Any) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.isdigit() and len(value) <= 12:
        return value
    return ""


def verify_signature(
    signature: Any,
    *,
    signing_key: str,
    tolerance_seconds: int,
    now: float | None = None,
) -> tuple[str, str]:
    """Verify Mailgun's HMAC-SHA256(timestamp + token) contract."""
    if not isinstance(signature, dict) or not signing_key:
        raise AppError(
            "Webhook authentication failed.",
            status_code=401,
            code="MAILGUN_WEBHOOK_INVALID_SIGNATURE",
        )
    timestamp = _signature_timestamp(signature.get("timestamp"))
    token = _text(signature.get("token"), maximum=50)
    supplied = _text(signature.get("signature"), maximum=64)
    if not timestamp or len(token) != 50 or not _HEX_SHA256.fullmatch(supplied):
        raise AppError(
            "Webhook authentication failed.",
            status_code=401,
            code="MAILGUN_WEBHOOK_INVALID_SIGNATURE",
        )
    current = time.time() if now is None else now
    if abs(current - int(timestamp)) > tolerance_seconds:
        raise AppError(
            "Webhook authentication failed.",
            status_code=401,
            code="MAILGUN_WEBHOOK_STALE",
        )
    expected = hmac.new(
        signing_key.encode("utf-8"),
        f"{timestamp}{token}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, supplied.lower()):
        raise AppError(
            "Webhook authentication failed.",
            status_code=401,
            code="MAILGUN_WEBHOOK_INVALID_SIGNATURE",
        )
    return timestamp, token


def _normalized_event_type(event_data: dict[str, Any]) -> str:
    event = _text(event_data.get("event"), maximum=64).lower()
    severity = _text(event_data.get("severity"), maximum=32).lower()
    if event == "failed" and severity == "permanent":
        return "permanent_failure"
    if event == "failed" and severity == "temporary":
        return "temporary_failure"
    if event == "permanent_fail":
        return "permanent_failure"
    if event == "temporary_fail":
        return "temporary_failure"
    if event in {"accepted", "delivered", "rejected", "complained"}:
        return event
    return "unsupported"


def parse_verified_event(
    payload: Any,
    *,
    signing_key: str,
    configured_domain: str,
    tolerance_seconds: int,
    now: float | None = None,
) -> VerifiedMailgunEvent:
    if not isinstance(payload, dict):
        raise AppError(
            "Malformed webhook payload.",
            status_code=400,
            code="MAILGUN_WEBHOOK_MALFORMED",
        )
    _, token = verify_signature(
        payload.get("signature"),
        signing_key=signing_key,
        tolerance_seconds=tolerance_seconds,
        now=now,
    )
    event_data = payload.get("event-data")
    if not isinstance(event_data, dict):
        raise AppError(
            "Malformed webhook payload.",
            status_code=400,
            code="MAILGUN_WEBHOOK_MALFORMED",
        )
    event_id = _text(event_data.get("id"), maximum=255)
    domain = event_data.get("domain")
    domain_name = (
        _text(domain.get("name"), maximum=255).lower()
        if isinstance(domain, dict)
        else ""
    )
    if not event_id or not configured_domain or domain_name != configured_domain.lower():
        raise AppError(
            "Malformed webhook payload.",
            status_code=400,
            code="MAILGUN_WEBHOOK_MALFORMED",
        )
    event_timestamp_value = event_data.get("timestamp")
    if isinstance(event_timestamp_value, bool):
        event_timestamp_value = None
    try:
        event_timestamp_number = float(event_timestamp_value)
    except (TypeError, ValueError):
        event_timestamp_number = math.nan
    if not math.isfinite(event_timestamp_number) or event_timestamp_number <= 0:
        raise AppError(
            "Malformed webhook payload.",
            status_code=400,
            code="MAILGUN_WEBHOOK_MALFORMED",
        )
    try:
        occurred_at = datetime.fromtimestamp(event_timestamp_number, tz=timezone.utc)
    except (ValueError, OverflowError, OSError) as exc:
        raise AppError(
            "Malformed webhook payload.",
            status_code=400,
            code="MAILGUN_WEBHOOK_MALFORMED",
        ) from exc

    event_type = _normalized_event_type(event_data)
    message = event_data.get("message")
    headers = message.get("headers") if isinstance(message, dict) else None
    raw_message_id = headers.get("message-id") if isinstance(headers, dict) else None
    message_id = (
        normalize_provider_message_id(raw_message_id)
        if isinstance(raw_message_id, str)
        else ""
    )
    if event_type in _SUPPORTED_TYPES and not message_id:
        raise AppError(
            "Malformed webhook payload.",
            status_code=400,
            code="MAILGUN_WEBHOOK_MALFORMED",
        )

    # Mailgun documents event IDs as unique only within a day. Domain + UTC
    # day + ID makes the provider identity stable; hashing bounds storage.
    event_day = occurred_at.date().isoformat()
    event_key = hashlib.sha256(
        f"mailgun\0{domain_name}\0{event_day}\0{event_id}".encode("utf-8")
    ).hexdigest()
    return VerifiedMailgunEvent(
        event_key=event_key,
        replay_token_digest=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        provider_event_id=event_id,
        provider_message_id=message_id or None,
        event_type=event_type,
        event_timestamp=occurred_at,
    )


def reconcile(client: Any, event: VerifiedMailgunEvent) -> dict[str, Any]:
    return email_outbox.reconcile_mailgun_event(
        client,
        event_key=event.event_key,
        replay_token_digest=event.replay_token_digest,
        provider_event_id=event.provider_event_id,
        provider_message_id=event.provider_message_id,
        event_type=event.event_type,
        event_timestamp=event.event_timestamp,
    )


def parse_configured_event(payload: Any) -> VerifiedMailgunEvent:
    return parse_verified_event(
        payload,
        signing_key=(settings.mailgun_webhook_signing_key or "").strip(),
        configured_domain=(settings.mailgun_domain or "").strip(),
        tolerance_seconds=settings.mailgun_webhook_tolerance_seconds,
    )

