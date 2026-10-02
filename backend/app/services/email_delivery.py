"""Phase 7.15 — email delivery abstraction for University Admin invitations.

The invitation service NEVER talks to an email vendor. It builds a neutral
:class:`InvitationEmail` and hands it to an :class:`EmailDeliveryProvider`:

    Invitation Service
            ↓
    EmailDeliveryProvider  (the protocol in this module)
            ↓
    ┌───────────────────┬────────────────────┐
    │ LocalEmailProvider│ ProductionProvider  │
    │ (outbox capture)  │ (configuration only)│
    └───────────────────┴────────────────────┘

Design constraints enforced here
--------------------------------
* **No vendor is hard-coded.** ``EMAIL_PROVIDER`` selects an implementation.
  ``local`` (the default) is the only one implemented in this phase; a
  production provider resolves its credentials from server-side settings and
  refuses to claim success while no vendor integration exists.
* **Credentials never leave the server.** ``EMAIL_PROVIDER_API_KEY`` is read
  only inside :class:`ProductionEmailProvider`, is never returned through an
  API, never logged and never placed in a message body or audit record.
* **The local provider never contacts anything.** It appends to a bounded,
  process-local outbox so tests can assert on the exact invitation URL. The
  outbox is never written to the application log, so a captured token does
  not silently become a log line in a deployed environment.
* **A delivery result is always explicit.** ``send_invitation`` either
  returns a success result or raises :class:`EmailDeliveryError`; it can never
  report success silently.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable

from app.config import settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

# Provider identifiers understood by :func:`get_email_provider`.
PROVIDER_LOCAL = "local"

# Maximum number of messages the local outbox retains. The outbox is a test and
# development affordance; bounding it keeps a long-running process from
# accumulating invitation tokens in memory.
OUTBOX_MAX_MESSAGES = 100

DELIVERY_SENT = "sent"
DELIVERY_FAILED = "failed"


class EmailDeliveryError(AppError):
    """A delivery attempt failed.

    Subclasses ``AppError`` so the existing project error handler renders the
    standard ``{"error": {"code", "message"}}`` envelope. The message is always
    safe: it never contains a token, a password or a provider credential.
    """

    def __init__(self, message: str, code: str = "EMAIL_DELIVERY_FAILED") -> None:
        super().__init__(message, status_code=502, code=code)


@dataclass(frozen=True)
class InvitationEmail:
    """A fully rendered invitation email, ready for any provider.

    Only non-sensitive content lives here. There is deliberately no password
    field, no service credential and no database identifier: the invitation
    token appears only inside :attr:`invitation_url`, which is built from the
    configured application base URL and never from a request ``Host`` header.
    """

    to_email: str
    subject: str
    body: str
    institution_name: str
    invitation_url: str
    expires_at: str | None


@dataclass(frozen=True)
class EmailDeliveryResult:
    """The outcome of one delivery attempt.

    ``status`` is ``sent`` or ``failed``. ``provider`` is the provider
    identifier for auditing — never a credential.
    """

    status: str
    provider: str
    detail: str = ""


@runtime_checkable
class EmailDeliveryProvider(Protocol):
    """The boundary every invitation email must cross."""

    name: str

    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult:
        """Deliver one invitation email or raise :class:`EmailDeliveryError`."""


@dataclass
class _Outbox:
    messages: list[InvitationEmail] = field(default_factory=list)


_local_outbox = _Outbox()
_local_outbox_lock = threading.Lock()


# __APPEND_1__
class LocalEmailProvider:
    """Development/test provider that captures messages instead of sending.

    It performs NO network I/O, requires NO credentials and cannot reach an
    external email service. Captured messages are held in a bounded in-process
    outbox so a test can read the exact invitation URL; they are deliberately
    never written to the log, so a captured token can never become a
    production log line.
    """

    name = PROVIDER_LOCAL

    def __init__(self, outbox: _Outbox | None = None) -> None:
        self._outbox = outbox if outbox is not None else _local_outbox

    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult:
        with _local_outbox_lock:
            self._outbox.messages.append(email)
            if len(self._outbox.messages) > OUTBOX_MAX_MESSAGES:
                del self._outbox.messages[:-OUTBOX_MAX_MESSAGES]
            captured = len(self._outbox.messages)
        # Operational counter only: no recipient, no subject, no token.
        logger.info(
            "event=admin_invitation_email_captured provider=%s captured=%d",
            self.name,
            captured,
        )
        return EmailDeliveryResult(
            status=DELIVERY_SENT,
            provider=self.name,
            detail="captured by the local delivery outbox",
        )


class ProductionEmailProvider:
    """Configuration-only production provider boundary.

    Credentials are resolved here and nowhere else. No vendor is hard-coded:
    the vendor integration itself is a later phase, so until one exists this
    provider refuses to report success. That refusal is deliberate — a
    provider that claimed to have sent an invitation it never sent would be a
    delivery-failure bug of the worst kind.
    """

    name = "production"

    def __init__(self, *, provider_name: str, from_address: str) -> None:
        self._provider_name = provider_name
        self._from_address = from_address
        # Read into a private attribute only: never returned, never logged.
        self._api_key = (settings.email_provider_api_key or "").strip()

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key) and bool(self._from_address.strip())

    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult:
        if not self.is_configured:
            raise EmailDeliveryError(
                "Invitation email could not be sent: the email provider is not "
                "configured on this server.",
                code="EMAIL_PROVIDER_NOT_CONFIGURED",
            )
        # No vendor integration is implemented in this phase, so the attempt is
        # reported as failed rather than pretended into a success.
        raise EmailDeliveryError(
            "Invitation email could not be sent: the configured email provider "
            "integration is not available.",
            code="EMAIL_PROVIDER_UNAVAILABLE",
        )


def get_email_provider() -> EmailDeliveryProvider:
    """Resolve the configured provider — the only supported selection path."""
    name = (settings.email_provider or PROVIDER_LOCAL).strip().lower()
    if name in {"", PROVIDER_LOCAL, "test", "capture"}:
        return LocalEmailProvider()
    return ProductionEmailProvider(
        provider_name=name,
        from_address=settings.email_from,
    )


def get_email_sender_address() -> str:
    """Return the configured ``From`` address (never a credential)."""
    return (settings.email_from or "").strip()


def get_email_reply_to() -> str | None:
    """Return the configured ``Reply-To`` address, or None when unset."""
    reply_to = (settings.email_reply_to or "").strip()
    return reply_to or None


def build_invitation_url(raw_token: str) -> str:
    """Return the user-facing invitation URL from the CONFIGURED base URL.

    The base URL is a server setting. A request ``Host`` / ``X-Forwarded-Host``
    header is deliberately never consulted, so an attacker cannot poison the
    link a Super Admin or invitee receives and redirect acceptance to a host
    they control.
    """
    base = (settings.email_base_url or "").strip().rstrip("/")
    if not base:
        raise AppError(
            "Application base URL is not configured",
            status_code=500,
            code="EMAIL_BASE_URL_NOT_CONFIGURED",
        )
    return f"{base}/admin-invite/{raw_token}"


def render_invitation_email(
    *, institution_name: str, invitation_url: str, expires_at: datetime | str | None
) -> tuple[str, str]:
    """Render the invitation email as ``(subject, body)``.

    The body carries only what the invited person needs: who is inviting them,
    what they are invited to do, the one-time link and the expiry. It never
    contains a password, a token hash, a service credential, a database
    identifier or any student data.
    """
    subject = f"You have been invited to administer {institution_name}"
    expiry_text = (
        expires_at.isoformat()
        if isinstance(expires_at, datetime)
        else str(expires_at or "")
    )
    body = "\n".join(
        [
            "You're invited to administer:",
            "",
            institution_name,
            "",
            "You have been invited as a University Administrator.",
            "",
            "Accept the invitation:",
            invitation_url,
            "",
            "This invitation expires at:",
            expiry_text,
            "",
            "This link can only be used once. The account created by this link "
            "is bound to the email address this invitation was sent to; that "
            "address cannot be changed during setup.",
            "",
            "If you did not expect this invitation, you can ignore this email.",
        ]
    )
    return subject, body


def build_invitation_email(
    *,
    to_email: str,
    institution_name: str,
    raw_token: str,
    expires_at: datetime | str | None,
) -> InvitationEmail:
    """Build the complete invitation email from configured, trusted inputs."""
    invitation_url = build_invitation_url(raw_token)
    subject, body = render_invitation_email(
        institution_name=institution_name,
        invitation_url=invitation_url,
        expires_at=expires_at,
    )
    return InvitationEmail(
        to_email=to_email,
        subject=subject,
        body=body,
        institution_name=institution_name,
        invitation_url=invitation_url,
        expires_at=None if expires_at is None else str(expires_at),
    )


def deliver_invitation_email(
    provider: EmailDeliveryProvider | None,
    *,
    to_email: str,
    institution_name: str,
    raw_token: str,
    expires_at: datetime | str | None,
) -> EmailDeliveryResult:
    """Send one invitation email, mapping any provider error to a safe failure.

    The caller records the result. This helper never raises for a delivery
    failure — it returns ``status="failed"`` — so the invitation service can
    always write the audit record that makes the failure auditable and
    retryable.
    """
    resolved = provider if provider is not None else get_email_provider()
    provider_name = getattr(resolved, "name", "unknown")
    try:
        return resolved.send_invitation(
            build_invitation_email(
                to_email=to_email,
                institution_name=institution_name,
                raw_token=raw_token,
                expires_at=expires_at,
            )
        )
    except EmailDeliveryError as exc:
        logger.warning(
            "event=admin_invitation_email_failed provider=%s code=%s",
            provider_name,
            exc.code,
        )
        return EmailDeliveryResult(
            status=DELIVERY_FAILED, provider=provider_name, detail=exc.code
        )
    except Exception:  # noqa: BLE001 - a provider must never break the caller
        logger.warning(
            "event=admin_invitation_email_failed provider=%s category=unexpected",
            provider_name,
        )
        return EmailDeliveryResult(
            status=DELIVERY_FAILED,
            provider=provider_name,
            detail="EMAIL_DELIVERY_ERROR",
        )


def captured_emails() -> list[InvitationEmail]:
    """Return a copy of the local outbox (tests and local development only)."""
    with _local_outbox_lock:
        return list(_local_outbox.messages)


def reset_email_outbox() -> None:
    """Test hook; production code never clears the outbox."""
    with _local_outbox_lock:
        _local_outbox.messages.clear()