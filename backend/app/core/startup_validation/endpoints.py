"""Startup endpoints configuration checks."""

from __future__ import annotations

from urllib.parse import urlparse

from app.config import Settings
from app.core.startup_validation.models import ConfigurationCheck
from app.core.startup_validation.helpers import _https_origin, _https_url


def collect_endpoint_checks(cfg: Settings, *, is_local: bool) -> list[ConfigurationCheck]:
    checks = []
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
    return checks
