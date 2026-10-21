"""Startup check coordination, safe reporting and environment enforcement."""

from __future__ import annotations

import logging

from app.config import DEV_TEST_ENVIRONMENTS, Settings
from app.core.startup_validation.models import ConfigurationCheck
from app.core.startup_validation.required import collect_required_checks
from app.core.startup_validation.endpoints import collect_endpoint_checks
from app.core.startup_validation.email import collect_email_checks
from app.core.startup_validation.runtime import collect_runtime_checks


logger = logging.getLogger(__name__)


def collect_configuration_checks(cfg: Settings) -> list[ConfigurationCheck]:
    """Collect configuration invariants in their established report order."""
    checks = collect_required_checks(cfg)
    environment = (cfg.environment or "").strip().lower()
    is_local = environment in DEV_TEST_ENVIRONMENTS
    checks.extend(collect_endpoint_checks(cfg, is_local=is_local))
    checks.extend(collect_email_checks(cfg, is_local=is_local))
    checks.extend(collect_runtime_checks(cfg, is_local=is_local))
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
