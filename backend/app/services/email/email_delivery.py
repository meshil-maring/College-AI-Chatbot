"""Shared email service: provider selection and safe workflow delivery.

Existing public contracts remain available here; provider implementations and
message rendering live in focused modules in this feature.
"""

from datetime import datetime
from email.utils import parseaddr
import logging
from urllib.parse import urlsplit

from app.config import settings
from app.services.email.capture import (
    LocalEmailProvider, TestEmailProvider, captured_emails, reset_email_outbox,
)
from app.services.email.contracts import (
    DELIVERY_CONFIGURATION_ERROR, DELIVERY_FAILED, DELIVERY_MALFORMED_RESPONSE,
    DELIVERY_PENDING, DELIVERY_PERMANENT_FAILURE, DELIVERY_RATE_LIMITED,
    DELIVERY_SENT, DELIVERY_TEMPORARY_FAILURE, DELIVERY_TIMEOUT,
    OUTBOX_MAX_MESSAGES, PROVIDER_LOCAL, PROVIDER_MAILGUN, PROVIDER_SMTP, PROVIDER_TEST,
    SAFE_DELIVERY_FAILURE_CATEGORIES,
    EmailDeliveryError, EmailDeliveryProvider, EmailDeliveryResult, InvitationEmail,
    ProductionEmailTransport, ProviderHealth, ProviderHealthState, ProviderSendResult,
    normalize_provider_message_id,
)
from app.services.email.invitation_messages import (
    build_invitation_email, build_invitation_url, render_invitation_email,
)
from app.services.email.mailgun_transport import MailgunEmailTransport
from app.services.email.production import ProductionEmailProvider
from app.core.configuration.smtp import smtp_configuration_errors
from app.services.email.smtp_transport import SmtpEmailTransport

logger = logging.getLogger(__name__)

def _build_production_transport(
    provider_name: str, api_key: str
) -> ProductionEmailTransport | None:
    """Select transport without coupling invitation workflows to a vendor."""
    if provider_name == PROVIDER_SMTP:
        missing = smtp_configuration_errors(settings)
        if missing:
            raise EmailDeliveryError(
                "SMTP email requires: " + ", ".join(missing) + ".",
                code=DELIVERY_CONFIGURATION_ERROR,
            )
        return SmtpEmailTransport(
            host=settings.smtp_host.strip(), port=settings.smtp_port,
            username=settings.smtp_username.strip(), password=settings.smtp_password.strip().replace(" ", ""),
        )
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
    development = environment in {"development", "dev", "local"}
    if development and not settings.email_allow_live_in_development:
        return LocalEmailProvider()

    name = (settings.email_provider or "").strip().lower()
    if development and name != PROVIDER_SMTP:
        _validate_live_development_mailgun(name)
    if development and name == PROVIDER_SMTP:
        missing = smtp_configuration_errors(settings)
        if missing:
            raise EmailDeliveryError(
                "SMTP email requires: " + ", ".join(missing) + ".",
                code=DELIVERY_CONFIGURATION_ERROR,
            )
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
        requires_api_key=name != PROVIDER_SMTP,
    )


def _validate_live_development_mailgun(name: str) -> None:
    """Validate an explicit real-mail test without exposing configured values."""
    from email_validator import EmailNotValidError, validate_email
    missing = []
    if name != PROVIDER_MAILGUN:
        missing.append('EMAIL_PROVIDER=mailgun')
    if not settings.mailgun_api_key.strip():
        missing.append('MAILGUN_API_KEY')
    domain = settings.mailgun_domain.strip().lower()
    if not domain or any(char in domain for char in '/:@ '):
        missing.append('MAILGUN_DOMAIN')
    address = parseaddr(settings.email_from)[1]
    try:
        validate_email(address, check_deliverability=False)
    except EmailNotValidError:
        missing.append('EMAIL_FROM')
    if domain.startswith('sandbox') and domain.endswith('.mailgun.org') and not address.lower().endswith('@' + domain):
        missing.append('EMAIL_FROM using the sandbox domain')
    if settings.mailgun_base_url.strip().rstrip('/') not in {'https://api.mailgun.net', 'https://api.eu.mailgun.net'}:
        missing.append('MAILGUN_BASE_URL using the Mailgun US or EU origin')
    base = urlsplit(settings.email_base_url.strip())
    if base.scheme not in {'http', 'https'} or not base.netloc or base.username or base.password or base.query or base.fragment:
        missing.append('EMAIL_BASE_URL')
    if missing:
        raise EmailDeliveryError('Real development email requires: ' + ', '.join(missing) + '.',
                                 code=DELIVERY_CONFIGURATION_ERROR)


def get_email_sender_address() -> str:
    return (settings.email_from or "").strip()


def get_email_reply_to() -> str | None:
    reply_to = (settings.email_reply_to or "").strip()
    return reply_to or None


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
