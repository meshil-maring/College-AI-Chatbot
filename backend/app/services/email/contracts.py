"""Provider-independent email contracts and safe failure categories."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from app.core.errors import AppError

PROVIDER_LOCAL = "local"
PROVIDER_TEST = "test"
PROVIDER_MAILGUN = "mailgun"
PROVIDER_SMTP = "smtp"
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
        provider_status_code: int | None = None,
    ) -> None:
        super().__init__(message, status_code=502, code=code)
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds
        self.provider_status_code = provider_status_code


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
    html_body: str | None = None


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


def normalize_provider_message_id(value: str) -> str:
    """Normalize RFC-2392-style IDs for send/webhook correlation."""
    normalized = value.strip()
    if normalized.startswith("<") and normalized.endswith(">"):
        normalized = normalized[1:-1].strip()
    return normalized
