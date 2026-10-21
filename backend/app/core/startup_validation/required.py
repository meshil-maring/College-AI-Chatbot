"""Startup required configuration checks."""

from __future__ import annotations

from app.config import Settings
from app.core.startup_validation.models import ConfigurationCheck
from app.core.startup_validation.helpers import _presence_check


def collect_required_checks(cfg: Settings) -> list[ConfigurationCheck]:
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
    return checks
