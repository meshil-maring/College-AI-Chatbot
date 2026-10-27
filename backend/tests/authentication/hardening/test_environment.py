"""Authentication hardening regressions: environment."""

from __future__ import annotations

from .support import (
    DEV_TEST_ENVIRONMENTS,
    Settings,
    ValidationError,
    _dev_flag_off_and_no_overrides,
    pytest,
    settings,
)


# ===========================================================================
# 1. Configuration guard — DEV_TEST_MODE can never be enabled in a deployment
# ===========================================================================


@pytest.mark.parametrize(
    "environment",
    ["production", "Production", "PROD", "prod", "staging", "", "  ", "prod-eu"],
)
def test_dev_test_mode_refused_outside_local_environments(environment):
    """The application must refuse to start rather than expose dev endpoints."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            environment=environment,
            dev_test_mode=True,
        )
    message = str(exc_info.value)
    assert "DEV_TEST_MODE" in message
    # The failure message itself must not leak any secret value.
    assert settings.supabase_secret_key not in message


@pytest.mark.parametrize("environment", sorted(DEV_TEST_ENVIRONMENTS))
def test_dev_test_mode_allowed_in_local_environments(environment, caplog):
    """Local development/testing keeps the dev helpers working (with a warning)."""
    with caplog.at_level("WARNING"):
        local = Settings(_env_file=None, environment=environment, dev_test_mode=True)

    assert local.dev_test_mode is True
    assert "DEV_TEST_MODE is enabled" in caplog.text


@pytest.mark.parametrize("environment", ["production", "prod", "staging", ""])
def test_dev_test_mode_disabled_is_always_allowed(environment):
    """Production is only valid with the dev flag OFF — the default."""
    config = Settings(_env_file=None, environment=environment, dev_test_mode=False)
    assert config.dev_test_mode is False


def test_shipped_settings_are_consistent_with_the_guard():
    """The running configuration satisfies its own production guard."""
    environment = (settings.environment or "").strip().lower()
    if settings.dev_test_mode:
        assert environment in DEV_TEST_ENVIRONMENTS
