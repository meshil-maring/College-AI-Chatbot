"""Phase 5.6 - Tests for the conversation history API."""

from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tests.auth_fixtures.principals import resolved_principal
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

FAKE_CLAIMS_A = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "user-a@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FAKE_CLAIMS_B = {
    "sub": "11111111-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "user-b@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}

FAKE_USER_A = {
    "user_id": "10000000-0000-0000-0000-000000000001",
    "auth_user_id": FAKE_CLAIMS_A["sub"],
    "email": FAKE_CLAIMS_A["email"],
    "roles": ["student"],
    "institution_id": "30000000-0000-0000-0000-000000000001",
}

FAKE_USER_B = {
    "user_id": "10000000-0000-0000-0000-000000000002",
    "auth_user_id": FAKE_CLAIMS_B["sub"],
    "email": FAKE_CLAIMS_B["email"],
    "roles": ["student"],
    "institution_id": "30000000-0000-0000-0000-000000000001",
}


def _auth_header(claims):
    return {"Authorization": "Bearer fake.token"}


def _patch_auth(user=FAKE_USER_A, claims=FAKE_CLAIMS_A):
    return (
        patch("app.core.security.tokens.verify_jwt", return_value=claims),
        patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=None if user is None else resolved_principal(user))),
    )


def _patch_admin(client_mock):
    return patch("app.services.ai.conversation_history.get_admin_client", return_value=client_mock)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
