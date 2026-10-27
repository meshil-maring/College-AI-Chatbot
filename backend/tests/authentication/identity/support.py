"""
Tests for Phase 17.5 — Supabase Auth JWT verification.

Scenarios:
  1. Missing Authorization header        → 401
  2. Invalid Bearer token                → 401
  3. Expired JWT                         → 401
  4. Valid JWT, no matching public.users → 404
  5. Valid JWT, matching public.users    → 200
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tests.auth_fixtures.principals import resolved_principal
from fastapi.testclient import TestClient

from app.db.supabase import get_user_by_auth_id
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "student@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FAKE_USER = {
    "id": 1,
    "user_id": 1,
    "auth_user_id": FAKE_CLAIMS["sub"],
    "email": FAKE_CLAIMS["email"],
    "roles": [],
}


def _patch_verify(claims=FAKE_CLAIMS):
    return patch("app.core.security.tokens.verify_jwt", return_value=claims)


def _patch_db(user=FAKE_USER):
    return patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=None if user is None else resolved_principal(user)))
