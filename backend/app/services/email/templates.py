"""CollegeAIChatbot transactional templates with safe HTML and text fallbacks."""

from dataclasses import dataclass
from html import escape
from urllib.parse import urlsplit


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text: str
    html: str


def render_html_email(
    subject: str, text: str, *, action_url: str | None = None,
    action_label: str = "Continue",
) -> str:
    """Escape all supplied values; never accept arbitrary HTML from workflows."""
    action = ""
    if action_url:
        parsed = urlsplit(action_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("email action URL must use HTTP or HTTPS")
        action = (
            '<p style="margin:24px 0"><a style="background:#234bc7;color:#fff;'
            'padding:12px 20px;text-decoration:none;border-radius:6px" href="'
            + escape(action_url, quote=True) + '">' + escape(action_label) + "</a></p>"
        )
    paragraphs = "".join(
        '<p style="margin:0 0 16px;overflow-wrap:anywhere">'
        + escape(paragraph).replace("\n", "<br>") + "</p>"
        for paragraph in text.split("\n\n")
    )
    return (
        '<!doctype html><html><head><meta name="viewport" '
        'content="width=device-width, initial-scale=1"></head>'
        '<body style="margin:0;background:#f2f4f8;font-family:Arial,sans-serif;'
        'color:#172238"><table role="presentation" style="width:100%"><tr><td '
        'align="center" style="padding:24px 12px"><table role="presentation" '
        'style="width:100%;max-width:600px;background:#fff;border-radius:8px">'
        '<tr><td style="padding:28px"><p style="color:#234bc7;font-weight:bold">'
        'CollegeAIChatbot</p><h1 style="font-size:22px">' + escape(subject)
        + "</h1>" + paragraphs + action
        + '<p style="font-size:12px;color:#667085">This is an account notification '
        'from CollegeAIChatbot. Keep verification codes and secure links private.</p>'
        '</td></tr></table></td></tr></table></body></html>'
    )


def render_transactional_email(
    kind: str, *, institution_name: str, recipient_name: str = "there",
    action_url: str | None = None, code: str | None = None,
) -> EmailContent:
    """Reusable content for workflows; this renderer never issues/verifies OTPs.

    Supabase-owned confirmation and recovery messages use its own templates.
    These templates are available to application-owned notifications as needed.
    """
    templates = {
        "verification": (
            "Verify your email address",
            f"Your verification code is {code or ''}. It expires in 5 minutes.",
        ),
        "registration": (
            "Registration received",
            "Your registration has been received. Your institution will review it.",
        ),
        "invitation_code": (
            "Your invitation code",
            f"Your invitation code is {code or ''}. Keep this code private.",
        ),
        "password_recovery": (
            "Reset your password",
            "Use the secure link below to reset your password. If you did not "
            "request this, you can ignore this email.",
        ),
        "approval": ("Account approved", "Your account has been approved. You can sign in."),
        "rejection": (
            "Account registration update",
            "Your registration was not approved. Contact your institution for assistance.",
        ),
        "staff_notification": (
            "Account review requested",
            "An account requires review. Sign in to your workspace for details.",
        ),
    }
    if kind not in templates:
        raise ValueError("unsupported transactional email kind")
    if kind in {"verification", "invitation_code"} and not code:
        raise ValueError("a code is required for this template")
    if kind == "password_recovery" and not action_url:
        raise ValueError("a recovery link is required")
    subject, detail = templates[kind]
    text = f"Hello {recipient_name},\n\n{institution_name}\n\n{detail}"
    if action_url:
        text += f"\n\n{action_url}"
    return EmailContent(subject, text, render_html_email(subject, text, action_url=action_url))
