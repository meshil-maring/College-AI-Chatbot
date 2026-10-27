"""
Tests for Phase 3.4 — Text Extraction.
Covers every row in the Phase 3.4 acceptance matrix.
All external I/O (Supabase DB + Cloudflare R2) is mocked.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tests.auth_fixtures.principals import resolved_principal

from app.core.errors import AppError
from app.main import app
from app.services.knowledge.extraction import extract_text
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DV_ID = "d0000000-0000-0000-0000-000000000001"
RUN_ID = "a0000000-0000-0000-0000-000000000001"
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
KS_ID = "30000000-0000-0000-0000-000000000201"
R2_BUCKET = "college-ai-knowledge"
OBJECT_KEY = "inst/ks/ver/doc.pdf"

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
FAKE_RUN_QUEUED = {
    "processing_run_id": RUN_ID,
    "status": "queued",
    "document_version_id": DV_ID,
    "document_versions": {
        "document_version_id": DV_ID,
        "knowledge_source_id": KS_ID,
        "storage_bucket": R2_BUCKET,
        "storage_object_key": OBJECT_KEY,
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


def _make_pdf(text: str = "Phase 3.4 PDF content") -> bytes:
    from pypdf import PdfWriter
    import io as _io
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    buf = _io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_real_pdf_with_text(pages: list[str]) -> bytes:
    """Build a PDF using reportlab so text is actually extractable."""
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf)
        for page_text in pages:
            c.drawString(50, 700, page_text)
            c.showPage()
        c.save()
        return buf.getvalue()
    except ImportError:
        return None


def _make_docx(text: str = "Phase 3.4 docx content") -> bytes:
    from docx import Document as DocxDocument
    doc = DocxDocument()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _post_extract(run_id=RUN_ID, run=None, file_bytes=b"hello world", file_type="txt"):
    fake_run = run if run is not None else {
        **FAKE_RUN_QUEUED,
        "document_versions": {**FAKE_RUN_QUEUED["document_versions"], "file_type": file_type},
    }
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=fake_run),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", return_value=file_bytes),
    ):
        return client.post(f"/api/v1/documents/{run_id}/extract", headers=_auth_headers())


# ---------------------------------------------------------------------------
# 1. PDF download from R2 — document retrieved successfully
# ---------------------------------------------------------------------------
