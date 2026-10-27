"""Document extraction regressions: lifecycle."""

from __future__ import annotations

from .support import (
    FAKE_RUN_QUEUED,
    MagicMock,
    RUN_ID,
    _active_institution_authorization,
    _auth_headers,
    _patch_auth,
    client,
    patch,
)


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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", return_value=b"text content"),
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_status),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", side_effect=_download),
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", return_value=b"text"),
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "started_at" in captured
