"""Document ingestion regressions: formats."""

from __future__ import annotations

from .support import (
    DOC_ID,
    DV_ID,
    KS_ID,
    RUN_ID,
    _active_institution_authorization,
    _post_ingest,
    io,
    zipfile,
)


# ---------------------------------------------------------------------------
# 1–3. Valid file type ingestion
# ---------------------------------------------------------------------------

def test_ingest_pdf_success():
    response = _post_ingest("syllabus.pdf", b"%PDF-1.4 fake content", "application/pdf")
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    assert body["knowledge_source_id"] == KS_ID
    assert body["document_id"] == DOC_ID
    assert body["document_version_id"] == DV_ID
    assert body["processing_run_id"] == RUN_ID
    assert "syllabus.pdf" in body["storage_object_key"]


def test_ingest_docx_success():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<w:document />")
    response = _post_ingest(
        "handbook.docx",
        buffer.getvalue(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "queued"


def test_ingest_txt_success():
    response = _post_ingest("notes.txt", b"plain text content", "text/plain")
    assert response.status_code == 201
    assert response.json()["status"] == "queued"
