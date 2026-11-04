"""Value-free SMTP validation, shared by startup and service initialization."""

from email.utils import parseaddr
from urllib.parse import urlsplit

from email_validator import EmailNotValidError, validate_email


def valid_mailbox(value: str, *, allow_display_name: bool = False) -> bool:
    if not value or any(char in value for char in "\r\n\x00"):
        return False
    name, address = parseaddr(value)
    if not allow_display_name and (name or address != value):
        return False
    try:
        validate_email(address, check_deliverability=False)
    except EmailNotValidError:
        return False
    return True


def smtp_configuration_errors(cfg) -> list[str]:
    """Return setting names only; never include credentials or their values."""
    errors = []
    host = cfg.smtp_host.strip()
    if not host or any(char.isspace() or char in "/:@?#" for char in host):
        errors.append("SMTP_HOST")
    if not 1 <= cfg.smtp_port <= 65535 or cfg.smtp_port == 465:
        errors.append("SMTP_PORT (use a STARTTLS port, normally 587)")
    if not cfg.smtp_username.strip():
        errors.append("SMTP_USERNAME")
    if not cfg.smtp_password.strip():
        errors.append("SMTP_PASSWORD")
    if not valid_mailbox(cfg.email_from.strip(), allow_display_name=True):
        errors.append("EMAIL_FROM")
    if cfg.email_reply_to.strip() and not valid_mailbox(
        cfg.email_reply_to.strip(), allow_display_name=True
    ):
        errors.append("EMAIL_REPLY_TO")
    try:
        base = urlsplit(cfg.email_base_url.strip())
    except ValueError:
        errors.append("EMAIL_BASE_URL")
        return errors
    if (
        base.scheme not in {"http", "https"} or not base.netloc
        or base.username or base.password or base.query or base.fragment
    ):
        errors.append("EMAIL_BASE_URL")
    return errors
