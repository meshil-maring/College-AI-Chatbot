"""Phase 6.15.8 — Authentication deployment & operational readiness tests.

Covers the deployment configuration invariants WITHOUT needing any real
production secret (every check below uses placeholder/fake values):

  1. DEV_TEST_MODE defaults safely to ``False``.
  2. Production configuration validation — missing required Supabase
     configuration stops startup with a CLEAR, VALUE-FREE error; configured
     checks are reported without exposing the configured values.
  3. Secret-hygiene — validation details/logs never contain configured
     secret values, even when those values look like real credentials.
  4. DEV_TEST_MODE=true with a production ENVIRONMENT is refused (startup
     guard), so dev auth routes can never be enabled in a deployment.
  5. ``/health`` is public, unauthenticated, stable and reveals no secret
     or environment-specific detail.

All Supabase interaction in the route tests is mocked — no live services.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import DEV_TEST_ENVIRONMENTS, Settings, settings
from app.core.startup_validation import (
    collect_configuration_checks,
    run_startup_configuration_validation,
)
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# Fake-but-realistic credential SHAPES used only to prove values never leak.
FAKE_SERVICE_KEY = "sb_secret_real-looking-service-role-key-1234567890abcdef"
FAKE_ANON_KEY = "sb_publishable_real-looking-anon-key-1234567890abcdef"
FAKE_OPENROUTER_KEY = "sk-or-v1-1234567890abcdef1234567890abcdef"

PRODUCTION_ENVIRONMENTS = ["production", "prod", "staging", ""]


def _production_settings(**overrides) -> Settings:
    """A fully-configured, production-shaped Settings object (fake values)."""
    base = dict(
        _env_file=None,  # never read the developer's local .env
        environment="production",
        debug=False,
        dev_test_mode=False,
        supabase_url="https://prod-ref.supabase.co",
        supabase_publishable_key=FAKE_ANON_KEY,
        supabase_secret_key=FAKE_SERVICE_KEY,
        supabase_jwks_url="https://prod-ref.supabase.co/auth/v1/.well-known/jwks.json",
    )
    base.update(overrides)
    return Settings(**base)


# ===========================================================================
# 1. DEV_TEST_MODE defaults safely
# ===========================================================================


def test_dev_test_mode_defaults_to_false():
    config = Settings(_env_file=None)
    assert config.dev_test_mode is False


def test_environment_defaults_to_local_development():
    config = Settings(_env_file=None)
    assert (config.environment or "").strip().lower() in DEV_TEST_ENVIRONMENTS


# ===========================================================================
# 2. Production configuration validation
# ===========================================================================


def test_fully_configured_production_settings_pass_validation():
    config = _production_settings()
    checks = run_startup_configuration_validation(config)  # must not raise
    assert all(check.ok for check in checks)
    names = {check.name for check in checks}
    assert {
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_SECRET_KEY",
        "SUPABASE_JWKS_URL",
        "DEV_TEST_MODE",
        "DEBUG",
    } <= names


@pytest.mark.parametrize(
    "missing",
    ["supabase_url", "supabase_publishable_key", "supabase_secret_key", "supabase_jwks_url"],
)
def test_missing_required_production_config_stops_startup(missing):
    config = _production_settings(**{missing: ""})
    with pytest.raises(RuntimeError) as exc_info:
        run_startup_configuration_validation(config)
    message = str(exc_info.value)
    assert missing.upper() in message  # the VARIABLE NAME is named ...
    assert "refuses to start" in message  # ... clearly, and ...
    # ... the configured values are never echoed back.
    assert FAKE_SERVICE_KEY not in message
    assert FAKE_ANON_KEY not in message
    assert "prod-ref.supabase.co" not in message


def test_debug_true_stops_startup_outside_local_environments():
    config = _production_settings(debug=True)
    with pytest.raises(RuntimeError) as exc_info:
        run_startup_configuration_validation(config)
    assert "DEBUG" in str(exc_info.value)



@pytest.mark.parametrize("environment", ["development", "dev", "local", "test", "testing"])
def test_incomplete_local_configuration_only_warns(environment, caplog):
    """Local development stays usable; problems are visible but non-fatal."""
    config = Settings(
        _env_file=None,
        environment=environment,
        dev_test_mode=False,
        supabase_url="",
        supabase_publishable_key="",
        supabase_secret_key="",
        supabase_jwks_url="",
    )
    with caplog.at_level(logging.WARNING):
        checks = run_startup_configuration_validation(config)
    assert any(not check.ok for check in checks)
    assert any("Configuration validation found" in record.message for record in caplog.records)


# ===========================================================================
# 3. Secret hygiene — validation output is always value-free
# ===========================================================================


def test_check_details_never_contain_secret_values():
    config = _production_settings(
        openrouter_api_key=FAKE_OPENROUTER_KEY,
        r2_secret_access_key="r2-secret-value-abcdef",
    )
    checks = collect_configuration_checks(config)
    rendered = "; ".join(f"{c.name}: {c.detail}" for c in checks)
    for secret in (
        FAKE_SERVICE_KEY,
        FAKE_ANON_KEY,
        FAKE_OPENROUTER_KEY,
        "r2-secret-value-abcdef",
    ):
        assert secret not in rendered


def test_failure_log_lines_never_contain_secret_values(caplog):
    config = _production_settings(supabase_secret_key="")
    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError):
            run_startup_configuration_validation(config)
    assert FAKE_ANON_KEY not in caplog.text
    assert "prod-ref.supabase.co" not in caplog.text


def test_shipped_settings_pass_their_own_validation(caplog):
    """The developer's actual running configuration satisfies the guard.

    This project's working configuration is a local development one; if the
    configuration ever drifted into an unsafe combination, this test fails.
    """
    with caplog.at_level(logging.WARNING):
        run_startup_configuration_validation(settings)  # must not raise
    assert "refuses to start" not in caplog.text


# ===========================================================================
# 4. Dev auth routes can never be enabled in a deployment
# ===========================================================================


@pytest.mark.parametrize("environment", PRODUCTION_ENVIRONMENTS)
def test_dev_test_mode_true_with_production_environment_is_refused(environment):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment=environment, dev_test_mode=True)


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/dev/auth/forgot-password",
        "/api/v1/dev/auth/change-password",
        "/api/v1/dev/auth/admin/reset-student-password",
    ],
)
def test_dev_auth_routes_return_404_with_flag_off(route):
    """DEV_TEST_MODE=false (the shipped default) → every dev route is 404."""
    original = settings.dev_test_mode
    settings.dev_test_mode = False
    try:
        with patch("app.db.supabase.create_client") as never_client:
            response = client.post(route, json={})
        assert response.status_code == 404
        assert response.json() == {
            "error": {"code": "NOT_FOUND", "message": "Not found"}
        }
        never_client.assert_not_called()
    finally:
        settings.dev_test_mode = original


# ===========================================================================
# 5. /health — public, stable, non-sensitive
# ===========================================================================


def test_health_endpoint_is_public_and_minimal():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "service", "environment"}
    # No secrets, tokens, URLs, keys or connection details are exposed.
    rendered = str(body)
    for forbidden in (
        "key",
        "secret",
        "token",
        "password",
        "supabase.co",
        "service_role",
    ):
        assert forbidden not in rendered.lower()


def test_health_endpoint_requires_no_authorization_header():
    response = client.get("/health", headers={})
    assert response.status_code == 200
