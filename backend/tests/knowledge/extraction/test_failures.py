"""Document extraction regressions: failures."""

from __future__ import annotations

from .support import (
    AppError,
    FAKE_RUN_QUEUED,
    MagicMock,
    RUN_ID,
    _active_institution_authorization,
    _auth_headers,
    _patch_auth,
    _post_extract,
    client,
    extract_text,
    patch,
    pytest,
)


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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=run),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", return_value=b"corrupt garbage bytes"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "processing" in status_calls
    assert "failed" in status_calls
    assert "ready" not in status_calls


def test_empty_txt_via_http_still_returns_ready():
    response = _post_extract(file_bytes=b"", file_type="txt")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["characters_extracted"] == 0


def test_empty_pdf_bytes_via_http_returns_500():
    response = _post_extract(file_bytes=b"", file_type="pdf")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "EXTRACTION_FAILED"
