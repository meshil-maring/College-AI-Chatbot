"""Phase 6.15.8 — safe startup configuration validation.

Verifies the presence/shape of the configuration the deployed backend needs
WITHOUT ever exposing configuration values. Every check detail is either a
static sentence (``"SUPABASE_URL is missing or empty"``) or an explicit
``"configured (value withheld)"`` — a secret value can therefore never reach
a startup log line or a failure message.

Behaviour:

* Local development/testing environments (``DEV_TEST_ENVIRONMENTS``):
  problems are logged as a warning and startup continues, so a partially
  configured laptop stays usable while the problem stays visible.
* Every other environment (production, prod, staging, a typo, empty, ...):
  any failed check raises ``RuntimeError`` at import/startup time so an
  invalid deployment fails fast with a CLEAR message instead of producing
  confusing runtime authentication failures later.

This module performs NO network I/O and constructs NO Supabase clients.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from cryptography.fernet import Fernet

from app.config import DEV_TEST_ENVIRONMENTS, Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConfigurationCheck:
    """One configuration invariant.

    ``detail`` MUST stay value-free: it may name the variable and state that
    it is missing/configured, but never contain the configured value.
    """

    name: str
    ok: bool
    detail: str


def _presence_check(cfg: Settings, attr: str, label: str) -> ConfigurationCheck:
    value = getattr(cfg, attr, "")
    if value and str(value).strip():
        return ConfigurationCheck(
            name=label,
            ok=True,
            detail="configured (value withheld)",
        )
    return ConfigurationCheck(name=label, ok=False, detail=f"{label} is missing or empty")


def _https_origin(value: str) -> bool:
    parsed = urlparse((value or "").strip())
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


def _https_url(value: str) -> bool:
    parsed = urlparse((value or "").strip())
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
    )


def collect_configuration_checks(cfg: Settings) -> list[ConfigurationCheck]:
    """Return every deployment configuration invariant as value-free checks."""
    checks = [
        _presence_check(cfg, "supabase_url", "SUPABASE_URL"),
        _presence_check(cfg, "supabase_publishable_key", "SUPABASE_PUBLISHABLE_KEY"),
        _presence_check(cfg, "supabase_secret_key", "SUPABASE_SECRET_KEY"),
        _presence_check(cfg, "supabase_jwks_url", "SUPABASE_JWKS_URL"),
        _presence_check(cfg, "openrouter_api_key", "OPENROUTER_API_KEY"),
        _presence_check(cfg, "r2_endpoint_url", "R2_ENDPOINT_URL"),
        _presence_check(cfg, "r2_access_key_id", "R2_ACCESS_KEY_ID"),
        _presence_check(cfg, "r2_secret_access_key", "R2_SECRET_ACCESS_KEY"),
        _presence_check(cfg, "r2_bucket", "R2_BUCKET"),
    ]

    environment = (cfg.environment or "").strip().lower()
    is_local = environment in DEV_TEST_ENVIRONMENTS

    if not is_local:
        supabase_origin_ok = _https_origin(cfg.supabase_url)
        expected_issuer = f"{cfg.supabase_url.strip().rstrip('/')}/auth/v1"
        configured_issuer = cfg.effective_supabase_jwt_issuer
        jwks = urlparse((cfg.supabase_jwks_url or "").strip())
        issuer = urlparse(configured_issuer)
        supabase = urlparse((cfg.supabase_url or "").strip())
        checks.extend(
            [
                ConfigurationCheck(
                    name="SUPABASE_URL_HTTPS",
                    ok=supabase_origin_ok,
                    detail=(
                        "configured as an HTTPS origin (value withheld)"
                        if supabase_origin_ok
                        else "must be an HTTPS origin without credentials, path, query, or fragment"
                    ),
                ),
                ConfigurationCheck(
                    name="SUPABASE_JWKS_URL_ORIGIN",
                    ok=(
                        jwks.scheme == "https"
                        and bool(jwks.netloc)
                        and jwks.netloc == supabase.netloc
                        and not jwks.username
                        and not jwks.password
                    ),
                    detail=(
                        "HTTPS origin matches SUPABASE_URL (values withheld)"
                        if jwks.scheme == "https" and jwks.netloc == supabase.netloc
                        else "must use HTTPS and the SUPABASE_URL origin"
                    ),
                ),
                ConfigurationCheck(
                    name="SUPABASE_JWT_ISSUER",
                    ok=(
                        issuer.scheme == "https"
                        and issuer.netloc == supabase.netloc
                        and configured_issuer == expected_issuer
                    ),
                    detail=(
                        "matches the canonical Supabase Auth issuer (value withheld)"
                        if configured_issuer == expected_issuer
                        else "must match SUPABASE_URL/auth/v1"
                    ),
                ),
                ConfigurationCheck(
                    name="OPENROUTER_BASE_URL",
                    ok=_https_url(cfg.openrouter_base_url),
                    detail=(
                        "configured as an HTTPS URL (value withheld)"
                        if _https_url(cfg.openrouter_base_url)
                        else "must be an HTTPS URL without credentials, query, or fragment"
                    ),
                ),
                ConfigurationCheck(
                    name="R2_ENDPOINT_URL",
                    ok=_https_url(cfg.r2_endpoint_url),
                    detail=(
                        "configured as an HTTPS URL (value withheld)"
                        if _https_url(cfg.r2_endpoint_url)
                        else "must be an HTTPS URL without credentials, query, or fragment"
                    ),
                ),
            ]
        )

    cors_origins = cfg.effective_cors_allowed_origins
    cors_ok = all(
        origin != "*" and _https_origin(origin)
        for origin in cors_origins
    ) if not is_local else all(origin != "*" for origin in cors_origins)
    checks.append(
        ConfigurationCheck(
            name="CORS_ALLOWED_ORIGINS",
            ok=cors_ok,
            detail=(
                "empty (same-origin only)"
                if not cors_origins
                else (
                    "explicit trusted origins configured (values withheld)"
                    if cors_ok
                    else "must contain explicit HTTPS origins without wildcard"
                )
            ),
        )
    )

    # Email selection is environment-owned. Local/test always use capture
    # providers. A deployed environment must explicitly name a non-capture
    # provider and supply all server-side configuration; no fallback is legal.
    if not is_local:
        email_provider = (cfg.email_provider or "").strip().lower()
        checks.append(
            ConfigurationCheck(
                name="EMAIL_PROVIDER",
                ok=email_provider == "mailgun",
                detail=(
                    "authorized Mailgun provider configured"
                    if email_provider == "mailgun"
                    else "must be set to the authorized mailgun provider"
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

    # DEV_TEST_MODE must never be enabled outside local development/testing.
    # (config.py already refuses to construct such Settings; this check keeps
    # the startup report complete and defends against future refactors.)
    checks.append(
        ConfigurationCheck(
            name="DEV_TEST_MODE",
            ok=not cfg.dev_test_mode or is_local,
            detail=(
                "enabled (allowed only in a local development/testing environment)"
                if cfg.dev_test_mode
                else "disabled"
            ),
        )
    )

    # DEBUG=true leaks chat timing diagnostics (settings.debug gates the
    # "diagnostics" metadata block) and must never be shipped to production.
    checks.append(
        ConfigurationCheck(
            name="DEBUG",
            ok=not cfg.debug or is_local,
            detail=(
                "enabled (set DEBUG=false outside local development/testing)"
                if cfg.debug
                else "disabled"
            ),
        )
    )

    allowed_hosts = cfg.effective_allowed_hosts
    checks.append(
        ConfigurationCheck(
            name="ALLOWED_HOSTS",
            ok=is_local or bool(allowed_hosts) and "*" not in allowed_hosts,
            detail=(
                "configured without wildcard"
                if allowed_hosts and "*" not in allowed_hosts
                else "must contain explicit deployment host names (wildcard is forbidden)"
            ),
        )
    )

    provider_supported = (cfg.ai_provider or "").strip().lower() == "openrouter"
    checks.append(
        ConfigurationCheck(
            name="AI_PROVIDER",
            ok=provider_supported,
            detail=(
                "supported provider configured"
                if provider_supported
                else "must be set to the supported openrouter provider"
            ),
        )
    )

    return checks


def summarize_configuration_checks(checks: list[ConfigurationCheck]) -> str:
    """Human-readable, value-free one-line report (the ``✓`` list)."""
    return "; ".join(
        f"{'✓' if check.ok else '✗'} {check.name} ({check.detail})" for check in checks
    )


def run_startup_configuration_validation(cfg: Settings) -> list[ConfigurationCheck]:
    """Validate deployment configuration at startup.

    Fails closed (raises ``RuntimeError`` listing only check names/details —
    never values) in any non-local environment; logs a warning and continues
    in local development/testing. Returns the checks either way so callers
    (scripts, tests) can inspect the report.
    """
    checks = collect_configuration_checks(cfg)
    failed = [check for check in checks if not check.ok]
    environment = (cfg.environment or "").strip().lower()
    is_local = environment in DEV_TEST_ENVIRONMENTS

    if not failed:
        logger.info(
            "Configuration validation: all %d checks passed (%s)",
            len(checks),
            summarize_configuration_checks(checks),
        )
        return checks

    report = summarize_configuration_checks(checks)
    if is_local:
        logger.warning(
            "Configuration validation found %d problem(s): %s",
            len(failed),
            report,
        )
        return checks

    raise RuntimeError(
        "Configuration validation failed for ENVIRONMENT="
        f"'{environment or '<unset>'}'. The application refuses to start "
        f"with an incomplete/unsafe deployment configuration: {report}. "
        "Set the listed variables via deployment secrets/configuration and "
        "restart. (Check details never contain secret values.)"
    )
