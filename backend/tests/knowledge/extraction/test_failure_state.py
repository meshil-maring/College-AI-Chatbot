"""Document extraction regressions: failure state."""

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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", side_effect=Exception("R2 connection refused")),
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", side_effect=Exception("bucket not found")),
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", side_effect=Exception("x" * 2000)),
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
        patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
        patch("app.api.knowledge.ingestion.update_run_status", side_effect=_capture),
        patch("app.api.knowledge.ingestion.store_extracted_text"),
        patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
        patch("app.api.knowledge.ingestion.download_file", side_effect=Exception("fail")),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    assert "completed_at" in captured
