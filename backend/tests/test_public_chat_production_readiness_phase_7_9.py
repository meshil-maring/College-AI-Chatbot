from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.core.startup_validation import run_startup_configuration_validation
from app.main import app, start


client = TestClient(app, raise_server_exceptions=False)


def production_settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "environment": "production",
        "debug": False,
        "dev_test_mode": False,
        "allowed_hosts": "api.example.edu",
        "supabase_url": "https://example.supabase.co",
        "supabase_publishable_key": "publishable-placeholder",
        "supabase_secret_key": "secret-placeholder",
        "supabase_jwks_url": "https://example.supabase.co/auth/v1/.well-known/jwks.json",
        "r2_endpoint_url": "https://example.r2.cloudflarestorage.com",
        "r2_access_key_id": "access-placeholder",
        "r2_secret_access_key": "r2-secret-placeholder",
        "r2_bucket": "documents",
        "ai_provider": "openrouter",
        "openrouter_api_key": "openrouter-placeholder",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.parametrize(
    "field,variable",
    [
        ("openrouter_api_key", "OPENROUTER_API_KEY"),
        ("r2_endpoint_url", "R2_ENDPOINT_URL"),
        ("r2_access_key_id", "R2_ACCESS_KEY_ID"),
        ("r2_secret_access_key", "R2_SECRET_ACCESS_KEY"),
        ("r2_bucket", "R2_BUCKET"),
        ("allowed_hosts", "ALLOWED_HOSTS"),
    ],
)
def test_production_startup_rejects_missing_public_chat_dependencies(
    field: str, variable: str
) -> None:
    with pytest.raises(RuntimeError) as exc_info:
        run_startup_configuration_validation(production_settings(**{field: ""}))
    rendered = str(exc_info.value)
    assert variable in rendered
    assert "placeholder" not in rendered


def test_production_startup_rejects_wildcard_host() -> None:
    with pytest.raises(RuntimeError, match="ALLOWED_HOSTS"):
        run_startup_configuration_validation(production_settings(allowed_hosts="*"))


def test_api_docs_default_to_local_only() -> None:
    assert Settings(_env_file=None, environment="development").effective_api_docs_enabled
    assert not production_settings().effective_api_docs_enabled


def test_security_headers_are_attached_and_cors_is_not_wildcarded() -> None:
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=()"
    )
    assert "access-control-allow-origin" not in response.headers


def test_untrusted_host_is_rejected() -> None:
    response = client.get("/health", headers={"Host": "evil.example"})
    assert response.status_code == 400
    assert "evil.example" not in response.text


def test_liveness_does_not_touch_database() -> None:
    with patch("app.main.get_admin_client") as admin_client:
        response = client.get("/health")
    assert response.status_code == 200
    admin_client.assert_not_called()


def test_readiness_performs_bounded_database_read() -> None:
    database = MagicMock()
    with patch("app.main.get_admin_client", return_value=database):
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": settings.app_name}
    database.table.assert_called_once_with("institutions")
    database.table.return_value.select.assert_called_once_with("institution_id")
    database.table.return_value.select.return_value.limit.assert_called_once_with(1)


def test_readiness_failure_is_sanitized() -> None:
    with patch("app.main.get_admin_client", side_effect=RuntimeError("secret SQL")):
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "service": settings.app_name,
    }
    assert "secret" not in response.text.lower()
    assert "sql" not in response.text.lower()


def test_root_contains_no_local_development_url() -> None:
    response = client.get("/")
    assert response.status_code == 200
    rendered = response.text.lower()
    assert "localhost" not in rendered
    assert "127.0.0.1" not in rendered


def test_unexpected_public_failure_has_coarse_log_and_safe_response(caplog) -> None:
    with patch(
        "app.main.process_public_request",
        side_effect=RuntimeError("secret database diagnostic"),
    ):
        with caplog.at_level(logging.ERROR):
            response = client.post(
                "/api/v1/chat/public",
                json={"institution_code": "GIT", "message": "Safe question"},
            )
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred. Please try again later.",
        }
    }
    assert "event=public_chat_failed" in caplog.text
    assert "secret database diagnostic" not in caplog.text
    assert "traceback" not in caplog.text.lower()


def test_packaged_start_is_single_worker_and_does_not_trust_proxy_headers() -> None:
    original_environment = settings.environment
    settings.environment = "production"
    try:
        with patch("app.main.uvicorn.run") as run:
            start()
    finally:
        settings.environment = original_environment
    kwargs = run.call_args.kwargs
    assert kwargs["workers"] == 1
    assert kwargs["reload"] is False
    assert kwargs["proxy_headers"] is False
