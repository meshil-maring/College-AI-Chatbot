"""Rendering for administrator, faculty and staff invitation messages."""

from datetime import datetime

from app.config import settings
from app.core.errors import AppError
from app.services.email.contracts import InvitationEmail
from app.services.email.templates import render_html_email

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
        html_body=render_html_email(
            subject, body, action_url=invitation_url, action_label="Accept invitation",
        ),
    )
