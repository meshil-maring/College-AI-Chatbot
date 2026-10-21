"""Startup runtime configuration checks."""

from __future__ import annotations

from app.config import Settings
from app.core.startup_validation.models import ConfigurationCheck


def collect_runtime_checks(cfg: Settings, *, is_local: bool) -> list[ConfigurationCheck]:
    checks = []
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
