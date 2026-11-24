"""BACKEND_ENV=local is opt-in and can never reach a remote database."""

import pytest

from app.core.configuration.environment_files import assert_local_target, backend_env_files


def test_default_reads_only_the_live_env_file(monkeypatch):
    monkeypatch.delenv("BACKEND_ENV", raising=False)
    assert backend_env_files() == ".env"
    assert_local_target("https://example.supabase.co")


def test_local_mode_layers_env_local_over_env(monkeypatch):
    monkeypatch.setenv("BACKEND_ENV", "local")
    assert backend_env_files() == (".env", ".env.local")
    assert_local_target("http://127.0.0.1:54321")
    assert_local_target("http://localhost:54321")


def test_local_mode_refuses_a_remote_project(monkeypatch):
    monkeypatch.setenv("BACKEND_ENV", "local")
    with pytest.raises(RuntimeError, match="local stack"):
        assert_local_target("https://example.supabase.co")
    with pytest.raises(RuntimeError):
        assert_local_target("")


def test_unknown_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("BACKEND_ENV", "staging")
    with pytest.raises(ValueError):
        backend_env_files()
