"""Document extraction regressions: storage."""

from __future__ import annotations

from .support import (
    DV_ID,
    FAKE_RUN_QUEUED,
    KS_ID,
    MagicMock,
    OBJECT_KEY,
    R2_BUCKET,
    RUN_ID,
    _active_institution_authorization,
    _auth_headers,
    _patch_auth,
    client,
    patch,
)


# ---------------------------------------------------------------------------
# 1. PDF download from R2 — document retrieved successfully
# ---------------------------------------------------------------------------

def test_pdf_download_from_r2_called_with_correct_bucket_and_key():
    run = {
        **FAKE_RUN_QUEUED,
        "document_versions": {
            "document_version_id": DV_ID,
            "knowledge_source_id": KS_ID,
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=run),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", download_mock),
    ):
        response = client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert response.status_code == 200
    download_mock.assert_called_once()
    _, call_args, _ = download_mock.mock_calls[0]
    assert call_args[1] == R2_BUCKET
    assert call_args[2] == OBJECT_KEY


# ---------------------------------------------------------------------------
# 10. Original R2 object remains unchanged
# ---------------------------------------------------------------------------

def test_r2_delete_never_called_during_extraction():
    r2_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=r2_mock),
        patch("app.api.knowledge.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    r2_mock.delete_object.assert_not_called()


def test_r2_put_object_never_called_during_extraction():
    r2_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=r2_mock),
        patch("app.api.knowledge.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    r2_mock.put_object.assert_not_called()


def test_r2_object_unchanged_on_failure():
    r2_mock = MagicMock()
    p1, p2 = _patch_auth()
    with (
        p1,
        p2,
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status"),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=r2_mock),
        patch("app.api.knowledge.ingestion.download_file", side_effect=Exception("fail")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    r2_mock.delete_object.assert_not_called()
    r2_mock.put_object.assert_not_called()
