"""Value-free configuration check results."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigurationCheck:
    """One configuration invariant.

    ``detail`` MUST stay value-free: it may name the variable and state that
    it is missing/configured, but never contain the configured value.
    """

    name: str
    ok: bool
    detail: str
