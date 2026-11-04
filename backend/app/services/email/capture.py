"""Bounded, in-memory email capture for local development and tests."""

import logging
import threading
from dataclasses import dataclass, field

from app.services.email.contracts import (
    DELIVERY_SENT, OUTBOX_MAX_MESSAGES, PROVIDER_LOCAL, PROVIDER_TEST,
    EmailDeliveryResult, InvitationEmail,
)

logger = logging.getLogger(__name__)

@dataclass
class _Outbox:
    messages: list[InvitationEmail] = field(default_factory=list)


_local_outbox = _Outbox()
_local_outbox_lock = threading.Lock()


class LocalEmailProvider:
    """Development capture provider. It performs no external I/O."""

    name = PROVIDER_LOCAL

    def __init__(self, outbox: _Outbox | None = None) -> None:
        self._outbox = outbox if outbox is not None else _local_outbox

    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult:
        with _local_outbox_lock:
            self._outbox.messages.append(email)
            if len(self._outbox.messages) > OUTBOX_MAX_MESSAGES:
                del self._outbox.messages[:-OUTBOX_MAX_MESSAGES]
            captured = len(self._outbox.messages)
        logger.info(
            "event=admin_invitation_email_captured provider=%s captured=%d",
            self.name,
            captured,
        )
        return EmailDeliveryResult(
            status=DELIVERY_SENT,
            provider=self.name,
            detail="captured by the local delivery outbox",
            provider_message_id=f"{self.name}:{email.idempotency_key or captured}",
        )


class TestEmailProvider(LocalEmailProvider):
    """Deterministic test capture, separately identifiable from local."""

    name = PROVIDER_TEST


def captured_emails() -> list[InvitationEmail]:
    with _local_outbox_lock:
        return list(_local_outbox.messages)


def reset_email_outbox() -> None:
    with _local_outbox_lock:
        _local_outbox.messages.clear()
