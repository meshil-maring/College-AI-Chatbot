"""Document extraction regressions: persistence."""

from __future__ import annotations

from .support import (
    DV_ID,
    FAKE_RUN_QUEUED,
    MagicMock,
    RUN_ID,
    _active_institution_authorization,
    _auth_headers,
    _patch_auth,
    _post_extract,
    client,
    patch,
)


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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.store_extracted_text", side_effect=_spy),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", return_value=b"document text"),
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.store_extracted_text", store_mock),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", side_effect=Exception("fail")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    store_mock.assert_not_called()
