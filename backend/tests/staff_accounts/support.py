"""Shared authorization principals and test doubles."""

import io

from contextlib import ExitStack, contextmanager

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

import pytest

from fastapi.testclient import TestClient

from app.core.security import SUPPORTED_ROLES, resolve_primary_role

from app.main import app
from tests.auth_fixtures.principals import resolved_principal

from app.repositories.admin.admin_academics import STUDENT_APPROVAL_COLUMNS

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_A = "30000000-0000-0000-0000-000000000001"

INSTITUTION_B = "30000000-0000-0000-0000-000000000002"

USER_ID = "30000000-0000-0000-0000-000000000401"

STUDENT_A = "30000000-0000-0000-0000-000000000301"

STUDENT_B = "30000000-0000-0000-0000-000000000302"

STAFF_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "staff@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}


def _staff_user(institution_id=INSTITUTION_A):
    """A staff principal with a server-owned ``user_roles`` grant (Phase 7.20).

    A tenant-less staff account holds a platform grant, never an institution
    grant, so the approval/ingestion scope can never widen to a global queue.
    """
    return resolved_principal({
        "id": USER_ID,
        "user_id": USER_ID,
        "auth_user_id": STAFF_CLAIMS["sub"],
        "email": STAFF_CLAIMS["email"],
        "roles": ["staff"],
        "status": "active",
        "institution_id": institution_id,
        "role_assignments": [
            {
                "role": "staff",
                "scope_type": "institution" if institution_id else "platform",
                "scope_id": institution_id,
                "scope_organization_id": None,
                "is_active": True,
            }
        ],
    })


STAFF_USER = _staff_user()

TENANT_LESS_STAFF_USER = _staff_user(None)


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    """Provide an ACTIVE institution to the scoped admin dependency only."""
    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
        data={
            "institution_id": INSTITUTION_A,
            "status": "active",
            "is_active": True,
        }
    )
    with patch("app.services.auth.authorization.get_admin_client", return_value=db):
        yield


AUTH_HEADERS = {"Authorization": "Bearer valid.token.here"}

PENDING_STUDENT_ROW = {
    "student_id": STUDENT_A,
    "user_id": "u-1",
    "institution_id": INSTITUTION_A,
    "student_number": "STU-0001",
    "email": "student@college.edu",
    "register_number": "REG-001",
    "university_roll_number": None,
    "approval_status": "pending",
    "status": "active",
    "is_active": True,
    "enrollment_date": None,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@contextmanager
def _patch_staff_auth(user=STAFF_USER):
    """Authenticate every request as the staff principal."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("app.core.security.tokens.verify_jwt", return_value=STAFF_CLAIMS)
        )
        stack.enter_context(
            patch(
                "app.db.supabase.get_user_by_auth_id",
                new=AsyncMock(return_value=user),
            )
        )
        yield


def _assert_staff_forbidden(method: str, path: str, **kwargs) -> None:
    """Every admin-only surface must stay 403 FORBIDDEN for staff."""
    with _patch_staff_auth():
        response = client.request(method, path, headers=AUTH_HEADERS, **kwargs)
    assert response.status_code == 403, f"{method} {path}: {response.status_code}"
    assert response.json()["error"]["code"] == "FORBIDDEN"


def _assert_staff_denied_on_student_endpoint(path: str) -> None:
    """The /students/me/* identity chain fails closed for a staff principal."""
    with (
        _patch_staff_auth(),
        patch(
            "app.repositories.admin.admin_academics.get_student_by_user_id",
            return_value=None,
        ),
        patch(
            "app.repositories.admin.admin_academics.get_student_approval_row_by_user_id",
            return_value=None,
        ),
    ):
        response = client.get(path, headers=AUTH_HEADERS)
    assert response.status_code == 404, f"{path}: {response.status_code}"
    assert response.json()["error"]["code"] == "STUDENT_PROFILE_NOT_FOUND"


def _ingest_with_tenant(ks_institution: str | None):
    """POST /documents/ingest as staff against a knowledge source whose
    tenant is controlled by the test. The downstream pipeline is stubbed so
    the test isolates ONLY the role + tenant authorization gate."""
    from app.schemas.knowledge.ingestion import IngestResponse

    claims = dict(STAFF_CLAIMS)
    user = dict(STAFF_USER, institution_id=INSTITUTION_A)
    ks = {"knowledge_source_id": "ks1", "institution_id": ks_institution}
    db = MagicMock()
    stub_response = IngestResponse(
        knowledge_source_id="ks1",
        document_id="doc1",
        document_version_id="dv1",
        processing_run_id="pr1",
        storage_object_key="k",
    )
    with (
        patch("app.core.security.tokens.verify_jwt", return_value=claims),
        patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=user)),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=ks),
        patch(
            "app.api.knowledge.ingestion.ingest_document",
            new=AsyncMock(return_value=stub_response),
        ),
    ):
        return client.post(
            "/api/v1/documents/ingest",
            headers=AUTH_HEADERS,
            data={"knowledge_source_id": "ks1"},
            files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        )
