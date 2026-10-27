"""Document chunking regressions: endpoint."""

from __future__ import annotations

from .support import (
    DV_ID,
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


# ===========================================================================
# Integration tests — HTTP endpoint
# ===========================================================================


class TestChunkEndpointSuccess:
    def test_returns_200(self):
        response, *_ = _post_chunk(extracted_text="Hello world paragraph.")
        assert response.status_code == 200

    def test_response_contains_processing_run_id(self):
        response, *_ = _post_chunk(extracted_text="Some content.")
        assert response.json()["processing_run_id"] == RUN_ID

    def test_response_contains_document_version_id(self):
        response, *_ = _post_chunk(extracted_text="Some content.")
        assert response.json()["document_version_id"] == DV_ID

    def test_response_status_is_ready(self):
        response, *_ = _post_chunk(extracted_text="Some content.")
        assert response.json()["status"] == "ready"

    def test_chunks_created_count_matches(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        response, *_ = _post_chunk(extracted_text=text)
        assert response.json()["chunks_created"] >= 1

    def test_empty_text_returns_zero_chunks(self):
        response, *_ = _post_chunk(extracted_text="")
        assert response.status_code == 200
        assert response.json()["chunks_created"] == 0

    def test_empty_text_insert_not_called(self):
        _, _, insert_mock, _ = _post_chunk(extracted_text="")
        insert_mock.assert_not_called()

    def test_requires_auth(self):
        response = client.post(f"/api/v1/documents/{RUN_ID}/chunk")
        assert response.status_code == 401


class TestIdempotency:
    def test_delete_called_before_insert(self):
        call_order = []

        def _del(db, run_id):
            call_order.append("delete")

        def _ins(db, run_id, chunks):
            call_order.append("insert")
            return len(chunks)

        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.knowledge.ingestion.get_extracted_text", return_value="Hello world."),
            patch("app.api.knowledge.ingestion.delete_chunks_for_run", side_effect=_del),
            patch("app.api.knowledge.ingestion.insert_chunks", side_effect=_ins),
            patch("app.api.knowledge.ingestion.update_run_status"),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert call_order == ["delete", "insert"]

    def test_delete_called_with_correct_run_id(self):
        _, delete_mock, _, _ = _post_chunk(extracted_text="Content.")
        delete_mock.assert_called_once()
        _, args, _ = delete_mock.mock_calls[0]
        assert args[1] == RUN_ID

    def test_insert_called_with_correct_run_id(self):
        _, _, insert_mock, _ = _post_chunk(extracted_text="Content.")
        insert_mock.assert_called_once()
        _, args, _ = insert_mock.mock_calls[0]
        assert args[1] == RUN_ID


class TestInvalidRun:
    def test_run_not_found_returns_404(self):
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=None),
        ):
            response = client.post(
                f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers()
            )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RUN_NOT_FOUND"

    def test_run_in_queued_status_returns_409(self):
        queued_run = {**FAKE_RUN_READY, "status": "queued"}
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=queued_run),
        ):
            response = client.post(
                f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers()
            )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "RUN_NOT_READY"

    def test_run_in_processing_status_returns_409(self):
        processing_run = {**FAKE_RUN_READY, "status": "processing"}
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=processing_run),
        ):
            response = client.post(
                f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers()
            )
        assert response.status_code == 409

    def test_run_in_failed_status_returns_409(self):
        failed_run = {**FAKE_RUN_READY, "status": "failed"}
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=failed_run),
        ):
            response = client.post(
                f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers()
            )
        assert response.status_code == 409
