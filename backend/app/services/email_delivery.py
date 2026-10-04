"""Provider-neutral invitation email delivery with fail-closed production use.

The invitation service supplies an already-rendered message. Local and test
environments capture it in memory. Production delegates to a vendor adapter;
this repository intentionally registers no adapter until a vendor is selected.
The production boundary owns timeout, retry, idempotency, and error semantics.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Callable, Protocol, runtime_checkable
from urllib.parse import quote

import httpx

from app.config import settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

PROVIDER_LOCAL = "local"
PROVIDER_TEST = "test"
PROVIDER_MAILGUN = "mailgun"
OUTBOX_MAX_MESSAGES = 100

DELIVERY_SENT = "sent"
DELIVERY_FAILED = "failed"
DELIVERY_PENDING = "pending"
DELIVERY_TEMPORARY_FAILURE = "DELIVERY_TEMPORARY_FAILURE"
DELIVERY_PERMANENT_FAILURE = "DELIVERY_PERMANENT_FAILURE"
DELIVERY_CONFIGURATION_ERROR = "DELIVERY_CONFIGURATION_ERROR"
DELIVERY_TIMEOUT = "DELIVERY_TIMEOUT"
DELIVERY_RATE_LIMITED = "DELIVERY_RATE_LIMITED"
DELIVERY_MALFORMED_RESPONSE = "DELIVERY_MALFORMED_RESPONSE"
SAFE_DELIVERY_FAILURE_CATEGORIES = frozenset(
    {
        DELIVERY_TEMPORARY_FAILURE,
        DELIVERY_PERMANENT_FAILURE,
        DELIVERY_CONFIGURATION_ERROR,
        DELIVERY_TIMEOUT,
        DELIVERY_RATE_LIMITED,
        DELIVERY_MALFORMED_RESPONSE,
    }
)


class ProviderHealthState(StrEnum):
    CONFIGURED = "configured"
    NOT_CONFIGURED = "not_configured"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"


class EmailDeliveryError(AppError):
    """Safe, categorized provider failure with bounded retry metadata."""

    def __init__(
        self,
        message: str,
        code: str = DELIVERY_PERMANENT_FAILURE,
        *,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message, status_code=502, code=code)
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class InvitationEmail:
    """Fully rendered provider input; authorization stays outside this type."""

    to_email: str
    subject: str
    body: str
    institution_name: str
    invitation_url: str
    expires_at: str | None
    # Stable across retries for one application attempt. Never a raw token.
    idempotency_key: str = ""


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    provider: str
    detail: str = ""
    provider_message_id: str | None = None
    retryable: bool = False
    retry_after_seconds: float | None = None


@dataclass(frozen=True)
class ProviderSendResult:
    """Minimum normalized success response required from a vendor adapter."""

    message_id: str


@dataclass(frozen=True)
class ProviderHealth:
    state: ProviderHealthState
    provider: str


@runtime_checkable
class EmailDeliveryProvider(Protocol):
    name: str

    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult: ...


@runtime_checkable
class ProductionEmailTransport(Protocol):
    """Small vendor-specific seam below the existing provider abstraction."""

    def send_invitation(
        self,
        email: InvitationEmail,
        *,
        from_address: str,
        reply_to: str | None,
        timeout_seconds: float,
        idempotency_key: str,
    ) -> ProviderSendResult: ...


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


class ProductionEmailProvider:
    """Reliable provider-neutral production delivery boundary.

    The same idempotency key is sent on every bounded retry. The transport must
    apply that key using its provider's idempotency mechanism. If a selected
    provider cannot guarantee this, its adapter must classify uncertain errors
    as non-retryable to avoid duplicate mail.
    """

    name = "production"

    def __init__(
        self,
        *,
        provider_name: str,
        from_address: str,
        reply_to: str | None = None,
        transport: ProductionEmailTransport | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_base_seconds: float | None = None,
        retry_cap_seconds: float | None = None,
        api_key: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._provider_name = provider_name
        self._from_address = from_address
        self._reply_to = reply_to
        self._api_key = (
            settings.email_provider_api_key if api_key is None else api_key
        ).strip()
        self._transport = transport
        self._timeout_seconds = (
            settings.email_provider_timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        )
        self._max_retries = (
            settings.email_provider_max_retries if max_retries is None else max_retries
        )
        self._retry_base_seconds = (
            settings.email_provider_retry_base_seconds
            if retry_base_seconds is None
            else retry_base_seconds
        )
        self._retry_cap_seconds = (
            settings.email_provider_retry_cap_seconds
            if retry_cap_seconds is None
            else retry_cap_seconds
        )
        self._sleep = sleep
        self._health_state = (
            ProviderHealthState.CONFIGURED
            if self.is_configured
            else ProviderHealthState.NOT_CONFIGURED
        )

    @property
    def is_configured(self) -> bool:
        return (
            bool(self._provider_name.strip())
            and bool(self._api_key)
            and bool(self._from_address.strip())
            and self._transport is not None
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            state=self._health_state,
            provider=self._provider_name or self.name,
        )

    def _retry_delay(self, retry_index: int, exc: EmailDeliveryError) -> float:
        if exc.retry_after_seconds is not None:
            return min(max(exc.retry_after_seconds, 0.0), self._retry_cap_seconds)
        return min(
            self._retry_base_seconds * (2 ** max(0, retry_index - 1)),
            self._retry_cap_seconds,
        )

    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult:
        if (
            not self._provider_name.strip()
            or not self._api_key
            or not self._from_address.strip()
            or self._transport is None
            or not email.idempotency_key
        ):
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_CONFIGURATION_ERROR,
            )

        started = time.monotonic()
        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.send_invitation(
                    email,
                    from_address=self._from_address,
                    reply_to=self._reply_to,
                    timeout_seconds=self._timeout_seconds,
                    idempotency_key=email.idempotency_key,
                )
                if (
                    not isinstance(response, ProviderSendResult)
                    or not response.message_id.strip()
                ):
                    raise EmailDeliveryError(
                        "Invitation could not be delivered.",
                        code=DELIVERY_MALFORMED_RESPONSE,
                    )
                logger.info(
                    "event=admin_invitation_email_sent provider=%s attempts=%d duration_ms=%d",
                    self._provider_name,
                    attempt + 1,
                    int((time.monotonic() - started) * 1000),
                )
                self._health_state = ProviderHealthState.CONFIGURED
                return EmailDeliveryResult(
                    DELIVERY_SENT,
                    self._provider_name,
                    provider_message_id=response.message_id,
                )
            except TimeoutError:
                exc = EmailDeliveryError(
                    "Invitation could not be delivered.",
                    code=DELIVERY_TIMEOUT,
                    retryable=True,
                )
            except OSError:
                exc = EmailDeliveryError(
                    "Invitation could not be delivered.",
                    code=DELIVERY_TEMPORARY_FAILURE,
                    retryable=True,
                )
            except EmailDeliveryError as error:
                exc = error

            if not exc.retryable or attempt >= self._max_retries:
                if exc.retryable:
                    self._health_state = ProviderHealthState.TEMPORARILY_UNAVAILABLE
                raise exc
            delay = self._retry_delay(attempt + 1, exc)
            logger.warning(
                "event=admin_invitation_email_retry provider=%s code=%s retry=%d delay_ms=%d",
                self._provider_name,
                exc.code,
                attempt + 1,
                int(delay * 1000),
            )
            self._sleep(delay)

        raise AssertionError("bounded email retry loop exhausted unexpectedly")


def normalize_provider_message_id(value: str) -> str:
    """Normalize RFC-2392-style IDs for send/webhook correlation."""
    normalized = value.strip()
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1].strip()
    return normalized


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value.strip()))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


class MailgunEmailTransport:
    """Mailgun HTTP API adapter below the provider-neutral boundary."""

    def __init__(
        self,
        *,
        api_key: str,
        domain: str,
        base_url: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._domain = domain.strip()
        self._base_url = base_url.strip().rstrip("/")
        self._client = client

    def _request(
        self, url: str, data: dict[str, str], timeout_seconds: float
    ) -> httpx.Response:
        kwargs = {
            "auth": ("api", self._api_key),
            # `(None, value)` makes httpx emit a multipart text field, matching
            # Mailgun's documented Messages API contract.
            "files": {name: (None, value) for name, value in data.items()},
            "timeout": timeout_seconds,
        }
        if self._client is not None:
            return self._client.post(url, **kwargs)
        with httpx.Client() as client:
            return client.post(url, **kwargs)

    def send_invitation(
        self,
        email: InvitationEmail,
        *,
        from_address: str,
        reply_to: str | None,
        timeout_seconds: float,
        idempotency_key: str,
    ) -> ProviderSendResult:
        # Mailgun's Messages API has no general send idempotency key. The
        # stable application key remains useful for local attempt identity but
        # is deliberately not placed in message headers/user variables (which
        # would expose an internal identifier in the delivered message).
        del idempotency_key
        if not all((self._api_key, self._domain, self._base_url, from_address.strip())):
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_CONFIGURATION_ERROR,
            )
        url = f"{self._base_url}/v3/{quote(self._domain, safe='.')}/messages"
        form = {
            "from": from_address,
            "to": email.to_email,
            "subject": email.subject,
            "text": email.body,
        }
        if reply_to:
            form["h:Reply-To"] = reply_to
        try:
            response = self._request(url, form, timeout_seconds)
        except httpx.TimeoutException as exc:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_TIMEOUT,
                retryable=True,
            ) from exc
        except httpx.TransportError as exc:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_TEMPORARY_FAILURE,
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_RATE_LIMITED,
                retryable=True,
                retry_after_seconds=_retry_after_seconds(response.headers.get("Retry-After")),
            )
        if response.status_code in {401, 403}:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_CONFIGURATION_ERROR,
            )
        if 500 <= response.status_code <= 599:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_TEMPORARY_FAILURE,
                retryable=True,
            )
        if response.status_code != 200:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_PERMANENT_FAILURE,
            )
        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_MALFORMED_RESPONSE,
            ) from exc
        message_id = normalize_provider_message_id(
            payload.get("id", "") if isinstance(payload, dict) else ""
        )
        if not message_id:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_MALFORMED_RESPONSE,
            )
        return ProviderSendResult(message_id=message_id)


def _build_production_transport(
    provider_name: str, api_key: str
) -> ProductionEmailTransport | None:
    """Register only the Phase 7.18-authorized Mailgun transport."""
    if provider_name == PROVIDER_MAILGUN:
        return MailgunEmailTransport(
            api_key=api_key,
            domain=settings.mailgun_domain,
            base_url=settings.mailgun_base_url,
        )
    return None


def get_email_provider() -> EmailDeliveryProvider:
    """Select by environment first; production can never capture locally."""
    environment = (settings.environment or "").strip().lower()
    if environment in {"test", "testing"}:
        return TestEmailProvider()
    if environment in {"development", "dev", "local"}:
        return LocalEmailProvider()

    name = (settings.email_provider or "").strip().lower()
    api_key = (
        settings.mailgun_api_key
        if name == PROVIDER_MAILGUN
        else settings.email_provider_api_key
    ).strip()
    return ProductionEmailProvider(
        provider_name=name,
        from_address=settings.email_from,
        reply_to=get_email_reply_to(),
        transport=_build_production_transport(name, api_key),
        api_key=api_key,
    )


def get_email_sender_address() -> str:
    return (settings.email_from or "").strip()


def get_email_reply_to() -> str | None:
    reply_to = (settings.email_reply_to or "").strip()
    return reply_to or None


def build_invitation_url(raw_token: str) -> str:
    """Build only from trusted configuration, never request Host headers."""
    base = (settings.email_base_url or "").strip().rstrip("/")
    if not base:
        raise AppError(
            "Application base URL is not configured",
            status_code=500,
            code="EMAIL_BASE_URL_NOT_CONFIGURED",
        )
    return f"{base}/admin-invite/{raw_token}"


def render_invitation_email(
    *, institution_name: str, invitation_url: str, expires_at: datetime | str | None,
    role_name: str = "admin",
) -> tuple[str, str]:
    role_label = {
        "admin": "University Administrator",
        "staff": "Staff",
        "faculty": "Faculty",
    }.get(role_name)
    if role_label is None:
        raise ValueError("unsupported invitation role")
    subject = (
        f"You have been invited to administer {institution_name}"
        if role_name == "admin"
        else f"You have been invited to join {institution_name} as {role_label}"
    )
    expiry_text = (
        expires_at.isoformat()
        if isinstance(expires_at, datetime)
        else str(expires_at or "")
    )
    body = "\n".join(
        [
            "You're invited to administer:" if role_name == "admin" else "You're invited to join:",
            "",
            institution_name,
            "",
            f"You have been invited as {role_label}.",
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
    idempotency_key: str = "",
    role_name: str = "admin",
) -> InvitationEmail:
    invitation_url = build_invitation_url(raw_token)
    subject, body = render_invitation_email(
        institution_name=institution_name,
        invitation_url=invitation_url,
        expires_at=expires_at,
        role_name=role_name,
    )
    return InvitationEmail(
        to_email=to_email,
        subject=subject,
        body=body,
        institution_name=institution_name,
        invitation_url=invitation_url,
        expires_at=None if expires_at is None else str(expires_at),
        idempotency_key=idempotency_key,
    )


def build_delivery_idempotency_key(invitation_id: str, delivery_attempt: int) -> str:
    """Create a stable non-secret identity: invitation_id + attempt number."""
    if not invitation_id.strip() or delivery_attempt < 1:
        raise ValueError("delivery identity requires invitation id and positive attempt")
    return f"admin-invitation:{invitation_id}:{delivery_attempt}"


def deliver_invitation_email(
    provider: EmailDeliveryProvider | None,
    *,
    to_email: str,
    institution_name: str,
    raw_token: str,
    expires_at: datetime | str | None,
    invitation_id: str | None = None,
    delivery_attempt: int | None = None,
    idempotency_key: str | None = None,
    role_name: str = "admin",
) -> EmailDeliveryResult:
    """Deliver once at the service boundary and return only safe failures."""
    resolved = provider if provider is not None else get_email_provider()
    provider_name = getattr(resolved, "name", "unknown")
    resolved_idempotency_key = idempotency_key or (
        build_delivery_idempotency_key(invitation_id, delivery_attempt)
        if invitation_id is not None and delivery_attempt is not None
        else ""
    )
    try:
        return resolved.send_invitation(
            build_invitation_email(
                to_email=to_email,
                institution_name=institution_name,
                raw_token=raw_token,
                expires_at=expires_at,
                idempotency_key=resolved_idempotency_key,
                role_name=role_name,
            )
        )
    except EmailDeliveryError as exc:
        safe_code = (
            exc.code
            if exc.code in SAFE_DELIVERY_FAILURE_CATEGORIES
            else DELIVERY_PERMANENT_FAILURE
        )
        logger.warning(
            "event=admin_invitation_email_failed provider=%s code=%s",
            provider_name,
            safe_code,
        )
        return EmailDeliveryResult(
            DELIVERY_FAILED,
            provider_name,
            safe_code,
            retryable=exc.retryable,
            retry_after_seconds=exc.retry_after_seconds,
        )
    except Exception:  # noqa: BLE001 - provider failures must not break auditing
        logger.warning(
            "event=admin_invitation_email_failed provider=%s category=unexpected",
            provider_name,
        )
        return EmailDeliveryResult(
            DELIVERY_FAILED, provider_name, DELIVERY_PERMANENT_FAILURE
        )


def captured_emails() -> list[InvitationEmail]:
    with _local_outbox_lock:
        return list(_local_outbox.messages)


def reset_email_outbox() -> None:
    with _local_outbox_lock:
        _local_outbox.messages.clear()
