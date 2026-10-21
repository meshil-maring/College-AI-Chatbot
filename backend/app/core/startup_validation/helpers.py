"""Presence and URL shape checks without network access."""

from __future__ import annotations

from urllib.parse import urlparse

from app.config import Settings
from app.core.startup_validation.models import ConfigurationCheck


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
