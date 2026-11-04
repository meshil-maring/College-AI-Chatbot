"""Startup email configuration checks."""

from __future__ import annotations

from urllib.parse import urlparse

from cryptography.fernet import Fernet

from app.config import Settings
from app.core.configuration.smtp import smtp_configuration_errors
from app.core.startup_validation.models import ConfigurationCheck
from app.core.startup_validation.helpers import _presence_check


def collect_email_checks(cfg: Settings, *, is_local: bool) -> list[ConfigurationCheck]:
    checks = []
    email_provider = (cfg.email_provider or "").strip().lower()
    live_development = (
        cfg.environment.strip().lower() in {"development", "dev", "local"}
        and cfg.email_allow_live_in_development
    )
    if email_provider == "smtp" and (not is_local or live_development):
        errors = smtp_configuration_errors(cfg)
        for name in (
            "SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD",
            "EMAIL_FROM", "EMAIL_REPLY_TO", "EMAIL_BASE_URL",
        ):
            failed = any(error.split(" ")[0] == name for error in errors)
            checks.append(ConfigurationCheck(
                name=name, ok=not failed,
                detail="invalid or missing" if failed else "configured (value withheld)",
            ))
    if not is_local:
        checks.append(
            ConfigurationCheck(
                name="EMAIL_PROVIDER",
                ok=email_provider in {"smtp", "mailgun"},
                detail=(
                    "supported email provider configured"
                    if email_provider in {"smtp", "mailgun"}
                    else "must be set to smtp or mailgun"
                ),
            )
        )
        checks.append(_presence_check(cfg, "email_from", "EMAIL_FROM"))
        if email_provider == "mailgun":
            checks.extend(
                [
                    _presence_check(cfg, "mailgun_api_key", "MAILGUN_API_KEY"),
                    _presence_check(cfg, "mailgun_domain", "MAILGUN_DOMAIN"),
                    _presence_check(
                        cfg,
                        "mailgun_webhook_signing_key",
                        "MAILGUN_WEBHOOK_SIGNING_KEY",
                    ),
                ]
            )
            mailgun_base_url = (cfg.mailgun_base_url or "").strip()
            parsed_mailgun_url = urlparse(mailgun_base_url)
            mailgun_base_url_ok = (
                parsed_mailgun_url.scheme == "https"
                and bool(parsed_mailgun_url.netloc)
                and not parsed_mailgun_url.username
                and not parsed_mailgun_url.password
                and parsed_mailgun_url.path in {"", "/"}
                and not parsed_mailgun_url.query
                and not parsed_mailgun_url.fragment
            )
            checks.append(
                ConfigurationCheck(
                    name="MAILGUN_BASE_URL",
                    ok=mailgun_base_url_ok,
                    detail=(
                        "configured as an HTTPS API origin (value withheld)"
                        if mailgun_base_url_ok
                        else "must be an HTTPS origin without credentials, query, or fragment"
                    ),
                )
            )
        outbox_key = (cfg.email_outbox_token_encryption_key or "").strip()
        try:
            Fernet(outbox_key.encode("ascii"))
            outbox_key_ok = True
        except (TypeError, ValueError, UnicodeError):
            outbox_key_ok = False
        checks.append(
            ConfigurationCheck(
                name="EMAIL_OUTBOX_TOKEN_ENCRYPTION_KEY",
                ok=outbox_key_ok,
                detail=(
                    "configured as a valid Fernet key (value withheld)"
                    if outbox_key_ok
                    else "must be a valid backend-only Fernet key"
                ),
            )
        )
        email_base_url = (cfg.email_base_url or "").strip()
        parsed_email_base_url = urlparse(email_base_url)
        email_base_url_ok = (
            parsed_email_base_url.scheme == "https"
            and bool(parsed_email_base_url.netloc)
            and not parsed_email_base_url.username
            and not parsed_email_base_url.password
        )
        checks.append(
            ConfigurationCheck(
                name="EMAIL_BASE_URL",
                ok=email_base_url_ok,
                detail=(
                    "configured as an HTTPS origin (value withheld)"
                    if email_base_url_ok
                    else "must be an HTTPS origin without embedded credentials"
                ),
            )
        )
    return checks
