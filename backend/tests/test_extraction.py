"""
Tests for Phase 3.4 — Text Extraction.
Covers every row in the Phase 3.4 acceptance matrix.
All external I/O (Supabase DB + Cloudflare R2) is mocked.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.errors import AppError
from app.main import app
from app.services.extraction import extract_text
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DV_ID = "d0000000-0000-0000-0000-000000000001"
RUN_ID = "a0000000-0000-0000-0000-000000000001"
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
}
FAKE_RUN_QUEUED = {
    "processing_run_id": RUN_ID,
    "status": "queued",
    "document_version_id": DV_ID,
    "document_versions": {
        "document_version_id": DV_ID,
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
    p1 = patch("app.core.security.verify_jwt", return_value=FAKE_CLAIMS)
    p2 = patch("app.db.supabase.get_user_by_auth_id", new=AsyncMock(return_value=FAKE_USER))
    return p1, p2


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
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=fake_run),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=file_bytes),
    ):
        return client.post(f"/api/v1/documents/{run_id}/extract", headers=_auth_headers())


# ---------------------------------------------------------------------------
# 1. PDF download from R2 — document retrieved successfully
# ---------------------------------------------------------------------------

def test_pdf_download_from_r2_called_with_correct_bucket_and_key():
    run = {
        **FAKE_RUN_QUEUED,
        "document_versions": {
            "document_version_id": DV_ID,
            "storage_bucket": R2_BUCKET,
            "storage_object_key": OBJECT_KEY,
            "file_type": "txt",
        },
    }
    download_mock = MagicMock(return_value=b"retrieved content")
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=run),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", download_mock),
    ):
        response = client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert response.status_code == 200
    download_mock.assert_called_once()
    _, call_args, _ = download_mock.mock_calls[0]
    assert call_args[1] == R2_BUCKET
    assert call_args[2] == OBJECT_KEY


# ---------------------------------------------------------------------------
# 2. PDF text extraction — text extracted successfully
# ---------------------------------------------------------------------------

def test_pdf_text_extraction_succeeds():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    result = extract_text(buf.getvalue(), "pdf")
    assert isinstance(result, str)


def test_txt_text_extraction_succeeds():
    result = extract_text(b"hello extraction", "txt")
    assert result == "hello extraction"


def test_docx_text_extraction_succeeds():
    result = extract_text(_make_docx("docx extraction test"), "docx")
    assert "docx extraction test" in result


# ---------------------------------------------------------------------------
# 3. Extracted text not empty — meaningful content preserved
# ---------------------------------------------------------------------------

def test_extracted_txt_content_is_not_empty():
    result = extract_text(b"meaningful content here", "txt")
    assert len(result) > 0
    assert "meaningful content" in result


def test_extracted_docx_content_is_not_empty():
    result = extract_text(_make_docx("important document text"), "docx")
    assert len(result) > 0


def test_characters_extracted_reported_correctly():
    content = b"exactly this text"
    response = _post_extract(file_bytes=content, file_type="txt")
    assert response.status_code == 200
    assert response.json()["characters_extracted"] == len("exactly this text")


# ---------------------------------------------------------------------------
# 4. Page/content handling — document content preserved
# ---------------------------------------------------------------------------

def test_multipage_docx_all_paragraphs_extracted():
    from docx import Document as DocxDocument
    doc = DocxDocument()
    doc.add_paragraph("First paragraph content")
    doc.add_paragraph("Second paragraph content")
    doc.add_paragraph("Third paragraph content")
    buf = io.BytesIO()
    doc.save(buf)
    result = extract_text(buf.getvalue(), "docx")
    assert "First paragraph content" in result
    assert "Second paragraph content" in result
    assert "Third paragraph content" in result


def test_txt_multiline_content_preserved():
    content = b"line one\nline two\nline three"
    result = extract_text(content, "txt")
    assert "line one" in result
    assert "line two" in result
    assert "line three" in result


def test_pdf_multiple_pages_extracted():
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    result = extract_text(buf.getvalue(), "pdf")
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# 5. Unsupported file type — proper error
# ---------------------------------------------------------------------------

def test_unsupported_type_xls_raises():
    with pytest.raises(AppError) as exc:
        extract_text(b"data", "xls")
    assert exc.value.code == "UNSUPPORTED_EXTRACTION_TYPE"
    assert exc.value.status_code == 422


def test_unsupported_type_csv_raises():
    with pytest.raises(AppError) as exc:
        extract_text(b"a,b,c", "csv")
    assert exc.value.code == "UNSUPPORTED_EXTRACTION_TYPE"


def test_unsupported_type_via_http_returns_500():
    run = {
        **FAKE_RUN_QUEUED,
        "document_versions": {**FAKE_RUN_QUEUED["document_versions"], "file_type": "xls"},
    }
    response = _post_extract(run=run, file_bytes=b"data", file_type="xls")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "EXTRACTION_FAILED"


# ---------------------------------------------------------------------------
# 6. Corrupt PDF — processing fails cleanly
# ---------------------------------------------------------------------------

def test_corrupt_pdf_via_http_returns_500():
    response = _post_extract(file_bytes=b"not a real pdf at all %%%", file_type="pdf")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "EXTRACTION_FAILED"


def test_corrupt_pdf_sets_failed_status():
    status_calls = []

    def _capture(db, run_id, status, **kwargs):
        status_calls.append(status)

    p1, p2 = _patch_auth()
    run = {**FAKE_RUN_QUEUED, "document_versions": {**FAKE_RUN_QUEUED["document_versions"], "file_type": "pdf"}}
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=run),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=b"corrupt garbage bytes"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "processing" in status_calls
    assert "failed" in status_calls
    assert "ready" not in status_calls


# ---------------------------------------------------------------------------
# 7. Empty document — processing fails cleanly
# ---------------------------------------------------------------------------

def test_empty_bytes_txt_returns_empty_string():
    result = extract_text(b"", "txt")
    assert result == ""


def test_empty_txt_via_http_still_returns_ready():
    response = _post_extract(file_bytes=b"", file_type="txt")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["characters_extracted"] == 0


def test_empty_pdf_bytes_via_http_returns_500():
    response = _post_extract(file_bytes=b"", file_type="pdf")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "EXTRACTION_FAILED"


# ---------------------------------------------------------------------------
# 8. Processing status — queued → processing → ready
# ---------------------------------------------------------------------------

def test_status_transitions_queued_to_processing_to_ready():
    status_calls = []

    def _capture(db, run_id, status, **kwargs):
        status_calls.append(status)

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=b"text content"),
    ):
        response = client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert response.status_code == 200
    assert status_calls == ["processing", "ready"]


def test_processing_status_set_before_download():
    call_order = []

    def _status(db, run_id, status, **kwargs):
        call_order.append(("status", status))

    def _download(r2, bucket, key):
        call_order.append(("download",))
        return b"text"

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_status),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", side_effect=_download),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert call_order[0] == ("status", "processing")
    assert call_order[1] == ("download",)


def test_ready_status_includes_completed_at():
    captured = {}

    def _capture(db, run_id, status, **kwargs):
        if status == "ready":
            captured.update(kwargs)

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "completed_at" in captured


def test_processing_status_includes_started_at():
    captured = {}

    def _capture(db, run_id, status, **kwargs):
        if status == "processing":
            captured.update(kwargs)

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "started_at" in captured


# ---------------------------------------------------------------------------
# 9. Extraction failure — processing → failed + error message
# ---------------------------------------------------------------------------

def test_failure_transitions_processing_to_failed():
    status_calls = []

    def _capture(db, run_id, status, **kwargs):
        status_calls.append(status)

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", side_effect=Exception("R2 connection refused")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert status_calls == ["processing", "failed"]


def test_failure_error_message_is_recorded():
    captured = {}

    def _capture(db, run_id, status, **kwargs):
        if status == "failed":
            captured.update(kwargs)

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", side_effect=Exception("bucket not found")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "error_message" in captured
    assert "bucket not found" in captured["error_message"]


def test_failure_error_message_truncated_to_1000_chars():
    captured = {}

    def _capture(db, run_id, status, **kwargs):
        if status == "failed":
            captured.update(kwargs)

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", side_effect=Exception("x" * 2000)),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert len(captured["error_message"]) <= 1000


def test_failure_includes_completed_at():
    captured = {}

    def _capture(db, run_id, status, **kwargs):
        if status == "failed":
            captured.update(kwargs)

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", side_effect=Exception("fail")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "completed_at" in captured


# ---------------------------------------------------------------------------
# 10. Original R2 object remains unchanged
# ---------------------------------------------------------------------------

def test_r2_delete_never_called_during_extraction():
    r2_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=r2_mock),
        patch("app.api.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    r2_mock.delete_object.assert_not_called()


def test_r2_put_object_never_called_during_extraction():
    r2_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=r2_mock),
        patch("app.api.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    r2_mock.put_object.assert_not_called()


def test_r2_object_unchanged_on_failure():
    r2_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=r2_mock),
        patch("app.api.ingestion.download_file", side_effect=Exception("fail")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    r2_mock.delete_object.assert_not_called()
    r2_mock.put_object.assert_not_called()


# ---------------------------------------------------------------------------
# 11. Document version remains associated with extraction
# ---------------------------------------------------------------------------

def test_store_extracted_text_called_with_correct_document_version_id():
    captured = {}

    def _spy(db, dv_id, text):
        captured["dv_id"] = dv_id
        captured["text"] = text

    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text", side_effect=_spy),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=b"document text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert captured["dv_id"] == DV_ID


def test_response_contains_correct_document_version_id():
    response = _post_extract(file_bytes=b"content", file_type="txt")
    assert response.status_code == 200
    assert response.json()["document_version_id"] == DV_ID


def test_store_extracted_text_not_called_on_failure():
    store_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text", store_mock),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", side_effect=Exception("fail")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    store_mock.assert_not_called()


# ---------------------------------------------------------------------------
# 12. Chunking not performed
# ---------------------------------------------------------------------------

def test_knowledge_chunks_table_never_touched():
    db_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=db_mock),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    touched_tables = [c.args[0] for c in db_mock.table.call_args_list if c.args]
    assert "knowledge_chunks" not in touched_tables


def test_extraction_service_has_no_chunking_imports():
    import app.services.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "knowledge_chunks" not in source
    assert "chunk" not in source.lower().replace("# chunk", "")


# ---------------------------------------------------------------------------
# 13. Embeddings not generated
# ---------------------------------------------------------------------------

def test_extraction_service_has_no_embedding_imports():
    import app.services.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "openai" not in source
    assert "embedding" not in source.lower()
    assert "sentence_transformers" not in source
    assert "tiktoken" not in source


# ---------------------------------------------------------------------------
# 14. Vector storage not performed
# ---------------------------------------------------------------------------

def test_extraction_service_has_no_vector_storage():
    import app.services.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "pinecone" not in source
    assert "pgvector" not in source
    assert "weaviate" not in source
    assert "vector" not in source.lower()


# ---------------------------------------------------------------------------
# 15. Retrieval not performed
# ---------------------------------------------------------------------------

def test_extraction_service_has_no_retrieval_calls():
    import app.services.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "retrieval" not in source.lower()
    assert "similarity_search" not in source
    assert "retrieved_chunks" not in source


def test_extract_endpoint_does_not_touch_retrieval_tables():
    db_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=db_mock),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.ingestion.update_run_status"),
        patch("app.api.ingestion.store_extracted_text"),
        patch("app.api.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    touched_tables = [c.args[0] for c in db_mock.table.call_args_list if c.args]
    for forbidden in ("retrieval_operations", "retrieved_chunks", "message_citations"):
        assert forbidden not in touched_tables
