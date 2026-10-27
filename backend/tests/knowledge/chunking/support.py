"""
Tests for Phase 3.5 — Text Chunking.

Covers:
  - Normal multi-paragraph document
  - Sentence-boundary splitting
  - Hard-limit splitting
  - Overlap carry-over
  - Sequence numbering (1-based, contiguous)
  - Section title detection and propagation
  - Empty extracted text
  - Oversized single paragraph
  - Idempotent re-processing (delete + reinsert)
  - Partial insertion failure / cleanup
  - Invalid processing run (404)
  - Wrong processing status (409)
  - Provenance: response contains correct document_version_id
  - No embeddings / vector / retrieval side-effects
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from tests.auth_fixtures.principals import resolved_principal
from fastapi.testclient import TestClient

from app.main import app
from app.services.knowledge.chunking import _build_chunks, _is_heading, _split_paragraph, chunk_text

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DV_ID = "d0000000-0000-0000-0000-000000000002"
RUN_ID = "a0000000-0000-0000-0000-000000000002"
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
KS_ID = "30000000-0000-0000-0000-000000000201"

FAKE_CLAIMS = {
    "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "email": "staff@college.edu",
    "aud": "authenticated",
    "exp": 9999999999,
}
FAKE_USER = {
    "id": "30000000-0000-0000-0000-000000000101",
    "user_id": "30000000-0000-0000-0000-000000000101",
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
FAKE_RUN_READY = {
    "processing_run_id": RUN_ID,
    "status": "ready",
    "document_version_id": DV_ID,
    "document_versions": {
        "document_version_id": DV_ID,
        "knowledge_source_id": KS_ID,
        "storage_bucket": "college-ai-knowledge",
        "storage_object_key": "inst/ks/ver/doc.txt",
        "file_type": "txt",
    },
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
        patch(
            "app.api.knowledge.ingestion.knowledge_repo.get_knowledge_source_detail",
            return_value={"knowledge_source_id": KS_ID, "institution_id": INSTITUTION_ID},
        ),
    ):
        yield


def _post_chunk(
    run_id=RUN_ID,
    run=None,
    extracted_text="Some text.",
    delete_side_effect=None,
    insert_side_effect=None,
):
    fake_run = run if run is not None else FAKE_RUN_READY
    p1, p2 = _patch_auth()
    delete_mock = MagicMock(side_effect=delete_side_effect)
    insert_mock = MagicMock(side_effect=insert_side_effect)
    update_mock = MagicMock()
    with (
        p1,
        p2,
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=fake_run),
        patch("app.api.knowledge.ingestion.get_extracted_text", return_value=extracted_text),
        patch("app.api.knowledge.ingestion.delete_chunks_for_run", delete_mock),
        patch("app.api.knowledge.ingestion.insert_chunks", insert_mock),
        patch("app.api.knowledge.ingestion.update_run_status", update_mock),
    ):
        response = client.post(f"/api/v1/documents/{run_id}/chunk", headers=_auth_headers())
    return response, delete_mock, insert_mock, update_mock


# ===========================================================================
# Unit tests — chunking service
# ===========================================================================
