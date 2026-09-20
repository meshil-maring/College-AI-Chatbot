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


def collect_configuration_checks(cfg: Settings) -> list[ConfigurationCheck]:
    """Return every deployment configuration invariant as value-free checks."""
    checks = [
        _presence_check(cfg, "supabase_url", "SUPABASE_URL"),
        _presence_check(cfg, "supabase_publishable_key", "SUPABASE_PUBLISHABLE_KEY"),
        _presence_check(cfg, "supabase_secret_key", "SUPABASE_SECRET_KEY"),
        _presence_check(cfg, "supabase_jwks_url", "SUPABASE_JWKS_URL"),
    ]

    environment = (cfg.environment or "").strip().lower()
    is_local = environment in DEV_TEST_ENVIRONMENTS

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
