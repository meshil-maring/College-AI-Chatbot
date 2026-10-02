"""Reusable, database-coordinated Phase 7.17 email outbox worker.

There is intentionally no scheduler in this repository. Deployments invoke
``EmailOutboxWorker.process_once`` continuously or on a schedule. PostgreSQL
claiming, not process memory, provides concurrency and stale-lease recovery.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.db.supabase import get_admin_client
from app.repositories import email_outbox as outbox_repo
from app.repositories.platform_admin_invitations import hash_invitation_token
from app.services import email_delivery, email_outbox_crypto

logger = logging.getLogger(__name__)

OUTCOME_SENT = "sent"
OUTCOME_RETRY = "retry"
OUTCOME_DEAD_LETTER = "dead_letter"
OUTCOME_CANCELLED = "cancelled"


@dataclass(frozen=True)
class EmailWorkerRun:
    claimed: int = 0
    sent: int = 0
    retried: int = 0
    dead_lettered: int = 0
    cancelled: int = 0


class EmailOutboxWorker:
    """Claim, validate, deliver, and settle a bounded batch of email jobs."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        provider: email_delivery.EmailDeliveryProvider | None = None,
    ) -> None:
        self._client = client
        self._provider = provider

    @staticmethod
    def _retry_delay(attempt_number: int, retry_after: float | None) -> float:
        cap = settings.email_provider_retry_cap_seconds
        if retry_after is not None:
            return min(max(retry_after, 0.0), cap)
        return min(
            settings.email_provider_retry_base_seconds
            * (2 ** max(0, attempt_number - 1)),
            cap,
        )

    def _settle(
        self,
        client: Any,
        job: dict[str, Any],
        *,
        outcome: str,
        provider: str,
        message_id: str | None = None,
        category: str | None = None,
        available_at: datetime | None = None,
    ) -> bool:
        return outbox_repo.complete(
            client,
            outbox_id=job["id"],
            attempt_number=int(job["attempt_count"]),
            outcome=outcome,
            provider_name=provider,
            provider_message_id=message_id,
            failure_category=category,
            available_at=available_at,
        )

    def _process_job(self, client: Any, job: dict[str, Any]) -> str:
        provider = self._provider or email_delivery.get_email_provider()
        provider_name = str(getattr(provider, "name", "unknown"))
        try:
            raw_token = email_outbox_crypto.recover_invitation_token(
                str(job.get("protected_token") or "")
            )
            context = outbox_repo.resolve_context(
                client,
                outbox_id=job["id"],
                token_hash=hash_invitation_token(raw_token),
            )
            if context is None:
                self._settle(
                    client,
                    job,
                    outcome=OUTCOME_CANCELLED,
                    provider=provider_name,
                    category="INVITATION_NOT_CURRENT",
                )
                return OUTCOME_CANCELLED

            started = time.monotonic()
            result = email_delivery.deliver_invitation_email(
                provider,
                to_email=str(context["recipient"]),
                institution_name=str(context["institution_name"]),
                raw_token=raw_token,
                expires_at=context.get("expires_at"),
                idempotency_key=f"email-outbox:{job['id']}",
            )
            logger.info(
                "event=email_outbox_provider_call provider=%s duration_ms=%d",
                result.provider,
                int((time.monotonic() - started) * 1000),
            )
        except Exception:  # noqa: BLE001 - corrupt jobs become safely terminal
            logger.warning("event=email_outbox_payload_failed category=invalid")
            self._settle(
                client,
                job,
                outcome=OUTCOME_DEAD_LETTER,
                provider=provider_name,
                category="EMAIL_OUTBOX_PAYLOAD_INVALID",
            )
            return OUTCOME_DEAD_LETTER

        if result.status == email_delivery.DELIVERY_SENT:
            self._settle(
                client,
                job,
                outcome=OUTCOME_SENT,
                provider=result.provider,
                message_id=result.provider_message_id,
            )
            logger.info("event=email_outbox_sent provider=%s", result.provider)
            return OUTCOME_SENT

        attempt = int(job["attempt_count"])
        if result.retryable and attempt < settings.email_outbox_retry_limit:
            delay = self._retry_delay(attempt, result.retry_after_seconds)
            self._settle(
                client,
                job,
                outcome=OUTCOME_RETRY,
                provider=result.provider,
                category=result.detail or email_delivery.DELIVERY_TEMPORARY_FAILURE,
                available_at=datetime.now(timezone.utc) + timedelta(seconds=delay),
            )
            logger.warning(
                "event=email_outbox_retry provider=%s attempt=%d delay_ms=%d category=%s",
                result.provider,
                attempt,
                int(delay * 1000),
                result.detail or email_delivery.DELIVERY_TEMPORARY_FAILURE,
            )
            return OUTCOME_RETRY

        self._settle(
            client,
            job,
            outcome=OUTCOME_DEAD_LETTER,
            provider=result.provider,
            category=result.detail or email_delivery.DELIVERY_PERMANENT_FAILURE,
        )
        logger.warning(
            "event=email_outbox_dead_letter provider=%s attempt=%d category=%s",
            result.provider,
            attempt,
            result.detail or email_delivery.DELIVERY_PERMANENT_FAILURE,
        )
        return OUTCOME_DEAD_LETTER

    def process_once(self) -> EmailWorkerRun:
        """Process one bounded batch; safe for concurrent worker processes."""
        client = self._client or get_admin_client()
        jobs = outbox_repo.claim_available(
            client,
            batch_size=settings.email_worker_batch_size,
            lock_seconds=settings.email_worker_lock_seconds,
            retry_limit=settings.email_outbox_retry_limit,
        )
        counts = {
            OUTCOME_SENT: 0,
            OUTCOME_RETRY: 0,
            OUTCOME_DEAD_LETTER: 0,
            OUTCOME_CANCELLED: 0,
        }
        for job in jobs:
            counts[self._process_job(client, job)] += 1
        logger.info(
            "event=email_outbox_batch claimed=%d sent=%d retried=%d dead_lettered=%d cancelled=%d",
            len(jobs),
            counts[OUTCOME_SENT],
            counts[OUTCOME_RETRY],
            counts[OUTCOME_DEAD_LETTER],
            counts[OUTCOME_CANCELLED],
        )
        return EmailWorkerRun(
            claimed=len(jobs),
            sent=counts[OUTCOME_SENT],
            retried=counts[OUTCOME_RETRY],
            dead_lettered=counts[OUTCOME_DEAD_LETTER],
            cancelled=counts[OUTCOME_CANCELLED],
        )
