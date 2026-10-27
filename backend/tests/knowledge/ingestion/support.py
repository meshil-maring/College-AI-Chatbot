"""
Tests for Phase 3.3 — Document Ingestion.

Unit tests mock all external I/O (Supabase DB + Cloudflare R2).
"""

import hashlib
import io
import zipfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tests.auth_fixtures.principals import resolved_principal
from fastapi.testclient import TestClient

from app.core.errors import AppError
from app.main import app
from app.services.knowledge.ingestion import _validate

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
USER_ID = "30000000-0000-0000-0000-000000000101"
KS_ID = "ks000000-0000-0000-0000-000000000001"
DOC_ID = "dc000000-0000-0000-0000-000000000001"
DV_ID = "dv000000-0000-0000-0000-000000000001"
RUN_ID = "pr000000-0000-0000-0000-000000000001"
R2_BUCKET = "college-ai-knowledge"

FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "staff@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}
FAKE_USER = {
    "id": USER_ID,
    "user_id": USER_ID,
    "auth_user_id": FAKE_CLAIMS["sub"],
    "email": FAKE_CLAIMS["email"],
    "roles": ["staff"],
    "institution_id": INSTITUTION_ID,
    "status": "active",
    "role_assignments": [
        {
            "role": "staff",
            "scope_type": "institution",
            "scope_id": INSTITUTION_ID,
            "scope_organization_id": None,
            "is_active": True,
        }
    ],
}
FAKE_KS = {
    "knowledge_source_id": KS_ID,
    "institution_id": INSTITUTION_ID,
    "title": "Student Handbook",
    "source_type": "policy",
    "lifecycle_status": "draft",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_headers():
    return {"Authorization": "Bearer valid.token.here"}


def _patch_auth():
    p1 = patch("app.core.security.tokens.verify_jwt", return_value=FAKE_CLAIMS)
    p2 = patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=resolved_principal(FAKE_USER)))
    return p1, p2


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    with (
        patch("app.services.auth.authorization.get_admin_client", return_value=MagicMock()),
        patch(
            "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
            return_value={"status": "active", "is_active": True},
        ),
    ):
        yield


def _make_db_mock(ks=FAKE_KS):
    """Mock for the Supabase admin DB client only (no storage)."""
    mock_db = MagicMock()

    def _table_side_effect(name):
        tbl = MagicMock()

        def _insert_side_effect(data):
            row_map = {
                "documents": {"document_id": DOC_ID, **data},
                "document_versions": {"document_version_id": DV_ID, **data},
                "document_processing_runs": {"processing_run_id": RUN_ID, **data},
            }
            result = MagicMock()
            result.execute.return_value.data = [row_map.get(name, data)]
            return result

        tbl.insert.side_effect = _insert_side_effect

        select_chain = MagicMock()
        select_chain.eq.return_value.maybe_single.return_value.execute.return_value.data = ks
        tbl.select.return_value = select_chain

        return tbl

    mock_db.table.side_effect = _table_side_effect
    return mock_db


def _make_r2_mock():
    """Mock for the boto3 S3/R2 client."""
    r2 = MagicMock()
    r2.put_object.return_value = {}
    r2.delete_object.return_value = {}
    return r2


def _post_ingest(
    filename: str,
    content: bytes,
    content_type: str,
    ks_id: str = KS_ID,
    db_mock=None,
    r2_mock=None,
):
    p1, p2 = _patch_auth()
    db = db_mock if db_mock is not None else _make_db_mock()
    r2 = r2_mock if r2_mock is not None else _make_r2_mock()
    with (
        p1,
        p2,
        patch("app.services.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.knowledge.ingestion.get_r2_client", return_value=r2),
    ):
        return client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": ks_id},
            files={"file": (filename, io.BytesIO(content), content_type)},
        )


# ---------------------------------------------------------------------------
# 1–3. Valid file type ingestion
# ---------------------------------------------------------------------------


def _post_ingest_as(role: str | None):
    """POST /ingest with a user whose only role is `role` (or no roles if None)."""
    claims = {**FAKE_CLAIMS}
    user = {
        **FAKE_USER,
        "roles": [role] if role else [],
        "role_assignments": (
            [
                {
                    "role": role,
                    "scope_type": "institution",
                    "scope_id": INSTITUTION_ID,
                    "scope_organization_id": None,
                    "is_active": True,
                }
            ]
            if role
            else []
        ),
    }
    p1 = patch("app.core.security.tokens.verify_jwt", return_value=claims)
    p2 = patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=None if user is None else resolved_principal(user)))
    db = _make_db_mock()
    r2 = _make_r2_mock()
    with (
        p1,
        p2,
        patch("app.services.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=db),
        patch("app.api.knowledge.ingestion.get_knowledge_source", return_value=FAKE_KS),
        patch("app.services.knowledge.ingestion.get_r2_client", return_value=r2),
    ):
        return client.post(
            "/api/v1/documents/ingest",
            headers=_auth_headers(),
            data={"knowledge_source_id": KS_ID},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF content"), "application/pdf")},
        )
