"""Document chunking regressions: failures."""

from __future__ import annotations

from .support import (
    FAKE_RUN_READY,
    MagicMock,
    RUN_ID,
    _active_institution_authorization,
    _auth_headers,
    _patch_auth,
    _post_chunk,
    client,
    patch,
)


class TestFailureHandling:
    def test_insert_failure_returns_500(self):
        response, *_ = _post_chunk(
            extracted_text="Content.",
            insert_side_effect=Exception("DB write failed"),
        )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "CHUNKING_FAILED"

    def test_insert_failure_triggers_cleanup_delete(self):
        """delete_chunks_for_run must be called twice: once before insert, once on cleanup."""
        _, delete_mock, _, _ = _post_chunk(
            extracted_text="Content.",
            insert_side_effect=Exception("DB write failed"),
        )
        assert delete_mock.call_count == 2

    def test_insert_failure_sets_run_to_failed(self):
        _, _, _, update_mock = _post_chunk(
            extracted_text="Content.",
            insert_side_effect=Exception("DB write failed"),
        )
        # update_run_status is called as update_run_status(db, run_id, status, **kwargs)
        statuses = [c.args[2] if len(c.args) >= 3 else c.kwargs.get("status") for c in update_mock.call_args_list]
        assert "failed" in statuses

    def test_insert_failure_records_error_message(self):
        captured = {}

        def _update(db, run_id, status, **kwargs):
            if status == "failed":
                captured.update(kwargs)

        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.knowledge.ingestion.get_extracted_text", return_value="Content."),
            patch("app.api.knowledge.ingestion.delete_chunks_for_run"),
            patch("app.api.knowledge.ingestion.insert_chunks", side_effect=Exception("write error")),
            patch("app.api.knowledge.ingestion.update_run_status", side_effect=_update),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert "error_message" in captured
        assert "write error" in captured["error_message"]

    def test_insert_failure_error_message_truncated_to_1000(self):
        captured = {}

        def _update(db, run_id, status, **kwargs):
            if status == "failed":
                captured.update(kwargs)

        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.knowledge.ingestion.get_extracted_text", return_value="Content."),
            patch("app.api.knowledge.ingestion.delete_chunks_for_run"),
            patch("app.api.knowledge.ingestion.insert_chunks", side_effect=Exception("e" * 2000)),
            patch("app.api.knowledge.ingestion.update_run_status", side_effect=_update),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert len(captured["error_message"]) <= 1000

    def test_insert_failure_includes_completed_at(self):
        captured = {}

        def _update(db, run_id, status, **kwargs):
            if status == "failed":
                captured.update(kwargs)

        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.knowledge.ingestion.get_extracted_text", return_value="Content."),
            patch("app.api.knowledge.ingestion.delete_chunks_for_run"),
            patch("app.api.knowledge.ingestion.insert_chunks", side_effect=Exception("fail")),
            patch("app.api.knowledge.ingestion.update_run_status", side_effect=_update),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert "completed_at" in captured
