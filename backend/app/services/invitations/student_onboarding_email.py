"""Student account setup email rendering and provider delivery."""

from dataclasses import replace
from datetime import datetime
import logging

from app.config import settings
from app.core.errors import AppError
from app.services.email.templates import render_html_email
from app.services.email.email_delivery import (
    DELIVERY_FAILED,
    DELIVERY_SENT,
    DELIVERY_PERMANENT_FAILURE,
    SAFE_DELIVERY_FAILURE_CATEGORIES,
    EmailDeliveryError,
    EmailDeliveryResult,
    InvitationEmail,
    get_email_provider,
)

logger = logging.getLogger(__name__)


def send_setup_link(
    *,
    to_email: str,
    institution_name: str,
    student_name: str,
    batch_code: str,
    section_name: str,
    raw_token: str,
    expires_at: datetime,
    invitation_id: str,
    attempt: int,
) -> EmailDeliveryResult:
    base_url = (settings.email_base_url or "").strip().rstrip("/")
    if not base_url:
        raise AppError("Student setup email is not configured.", 503, "EMAIL_NOT_CONFIGURED")
    link = f"{base_url}/student-setup#{raw_token}"
    expiry = expires_at.isoformat()
    message = InvitationEmail(
        to_email=to_email,
        subject=f"Set up your student account - {batch_code}",
        body="\n".join(
            [
                f"Hello {student_name},",
                "",
                f"Your student account has been created for {institution_name}.",
                f"Registration batch: {batch_code}",
                f"Section: {section_name}",
                "",
                "Open this secure link to verify your invitation and set your password:",
                link,
                "",
                f"This single-use link expires at {expiry}.",
                "If you did not expect this email, you can ignore it.",
            ]
        ),
        institution_name=institution_name,
        invitation_url=link,
        expires_at=expiry,
        idempotency_key=f"student-onboarding:{invitation_id}:{attempt}",
    )
    provider = None
    try:
        message = replace(
            message, html_body=render_html_email(
                message.subject, message.body, action_url=link,
                action_label="Set up student account",
            ),
        )
        provider = get_email_provider()
        return provider.send_invitation(message)
    except EmailDeliveryError as exc:
        code = (
            exc.code if exc.code in SAFE_DELIVERY_FAILURE_CATEGORIES
            else DELIVERY_PERMANENT_FAILURE
        )
        logger.warning(
            "event=student_setup_email_failed provider=%s code=%s",
            settings.email_provider, code,
        )
        return EmailDeliveryResult(
            status=DELIVERY_FAILED,
            provider=getattr(provider, "name", settings.email_provider or "unknown"),
            detail=code,
            retryable=exc.retryable,
            retry_after_seconds=exc.retry_after_seconds,
        )
    except Exception:
        # Provider diagnostics can contain recipients, tokens or credentials.
        logger.warning("event=student_setup_email_failed category=unexpected")
        return EmailDeliveryResult(
            status=DELIVERY_FAILED,
            provider=getattr(provider, "name", settings.email_provider or "unknown"),
            detail=DELIVERY_PERMANENT_FAILURE,
        )


def delivery_message(status: str) -> str:
    if status == DELIVERY_SENT:
        return "Setup link submitted for sending. Inbox delivery is not confirmed."
    return "Setup link could not be delivered. Resend a new link."
