"""Phase 6.15.7 — Authentication production-hardening tests.

Focused production-readiness assurances that were NOT already covered by the
Phase 6.13.x / 6.15.x suites (no duplicated coverage):

  1. Configuration guard — ``DEV_TEST_MODE=true`` is refused outside a local
     development/testing ``ENVIRONMENT`` (fail closed, allowlist based).
  2. Dev-route gating — with the flag OFF every ``/dev/auth`` route answers
     404 for EVERY payload shape (including malformed and unknown-field
     bodies), before authentication and before any Supabase client is built;
     with the flag ON the dev schemas reject unexpected fields with 422.
  3. Response minimization — ``/auth/me``, ``/auth/login`` and the public
     registration contract expose exactly the documented field sets (no role,
     token, hash or internal-auth metadata beyond the locked contract).
  4. Error sanitization — an unhandled server exception returns a generic 500
     with no traceback / exception name / file path / internal detail, and a
     rejected login never echoes the submitted password or discloses account
     existence.

Every test uses mocked Supabase clients — no live services are contacted.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from tests.auth_fixtures.principals import resolved_principal
from fastapi.testclient import TestClient
from pydantic import ValidationError
from supabase_auth.errors import AuthApiError

from app.config import DEV_TEST_ENVIRONMENTS, Settings, settings
from app.core.security import get_current_user
from app.main import app
from app.services.auth.auth_security import reset_auth_abuse_state
from app.schemas.platform.tenancy import InstitutionLookupResponse
from app.schemas.auth.users import UserRegistrationResponse

client = TestClient(app, raise_server_exceptions=False)

DEV_ROUTES = (
    "/api/v1/dev/auth/forgot-password",
    "/api/v1/dev/auth/change-password",
    "/api/v1/dev/auth/admin/reset-student-password",
)

ADMIN_USER = {
    "user_id": "90000000-0000-0000-0000-000000000001",
    "auth_user_id": "90000000-0000-0000-0000-0000000000aa",
    "email": "admin@example.com",
    "roles": ["admin"],
    "institution_id": None,
}

# A distinctive value so "is the password echoed anywhere?" is a real question.
SUBMITTED_PASSWORD = "Sup3rSecret-Passw0rd!"


@pytest.fixture(autouse=True)
def _dev_flag_off_and_no_overrides():
    """Every test starts with DEV_TEST_MODE off and no dependency override."""
    original = settings.dev_test_mode
    settings.dev_test_mode = False
    app.dependency_overrides.pop(get_current_user, None)
    reset_auth_abuse_state()
    with patch("app.api.auth.common.record_auth_security_event"):
        yield
    reset_auth_abuse_state()
    settings.dev_test_mode = original
    app.dependency_overrides.pop(get_current_user, None)



# ===========================================================================
# 1. Configuration guard — DEV_TEST_MODE can never be enabled in a deployment
# ===========================================================================


def _fake_claims() -> dict:
    return {
        "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "email": "student@college.edu",
        "aud": "authenticated",
        "exp": 9999999999,
    }
