"""Phase 6.13.1 — Organization & Institution FOUNDATION tests.

Scope of this file is strictly the foundation:

    Organization 1 ──── N Institutions
            │                    │
            └──── Users ─────── Roles + Scope ──── Institution-specific data

Covered:
  * schema contract of the Phase 6.13 migration (organizations table,
    institutions.organization_id NOT NULL + FK, legacy backfill,
    status -> is_active single source of truth, ADDITIVE role scope columns,
    non-destructive / idempotent DDL)
  * organization -> institution relationship (repository + authorization)
  * organization isolation (org A admin can never touch org B)
  * institution isolation (institution A1 can never touch institution A2)
  * server-side scope resolution — a client-supplied scope id is never trusted
  * compatibility of EXISTING authentication, RBAC, student authentication,
    PUBLIC_USER_ID and public chat (nothing in this phase replaces them)

NOT covered here (deliberately out of scope for 6.13.1): organization
registration, institution registration, join/membership approval workflows
(Phase 6.13.2+).

Physical (live database) verification lives in a skip-by-default class at the
bottom of this file, mirroring the project's existing
``test_physical_validation_phase_4_4.py`` opt-in convention. No credentials are
hardcoded — the app's own service-role configuration is reused, and every check
in that class is READ-ONLY.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from tests.auth_fixtures.principals import resolved_principal

from app.core.errors import AppError
from app.core.security import (
    PUBLIC_USER_ID,
    get_current_user,
    require_roles,
    scope_tenant,
)
from app.repositories.platform import tenancy as tenancy_repo
from app.services.auth import authorization as authz
from app.services.ai import public_chat
from app.services.auth.student_auth import SafeAuthFailure, _assert_institution_active

_ROOT = Path(__file__).resolve().parents[3]
PHASE_6_13_MIGRATION = (
    _ROOT
    / "supabase"
    / "migrations"
    / "20260915000000_phase_6_13_organization_institution_tenancy.sql"
)

# ---------------------------------------------------------------------------
# Stable identifiers used across the tests
# ---------------------------------------------------------------------------

ORG_A = "a0000000-0000-0000-0000-00000000000a"
ORG_B = "a0000000-0000-0000-0000-00000000000b"
INST_A1 = "b0000000-0000-0000-0000-0000000000a1"
INST_A2 = "b0000000-0000-0000-0000-0000000000a2"
INST_B1 = "b0000000-0000-0000-0000-0000000000b1"
USER_ID = "c0000000-0000-0000-0000-000000000001"
JOIN_REQUEST_ID = "d0000000-0000-0000-0000-000000000001"


def _sql() -> str:
    return PHASE_6_13_MIGRATION.read_text(encoding="utf-8")


def _context(
    *,
    role: str = "admin",
    scope_type: str,
    organization_id: str | None = None,
    institution_id: str | None = None,
    scope_id: str | None = None,
) -> dict:
    """Build a resolved authorization context (as ``resolve_authorization_context``
    would return it server-side)."""
    return {
        "user_id": USER_ID,
        "email": "user@example.com",
        "roles": [role],
        "scope_type": scope_type,
        "scope_id": scope_id or organization_id or institution_id,
        "organization_id": organization_id,
        "institution_id": institution_id,
    }


# ============================================================================
# 1. SCHEMA CONTRACT — organization -> institution foundation
# ============================================================================


def _expect(error_code: str, func, *args, **kwargs) -> None:
    with pytest.raises(AppError) as excinfo:
        func(*args, **kwargs)
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == error_code
