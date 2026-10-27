"""Document chunking regressions: provenance."""

from __future__ import annotations

from .support import (
    DV_ID,
    FAKE_RUN_READY,
    MagicMock,
    RUN_ID,
    _active_institution_authorization,
    _auth_headers,
    _patch_auth,
    client,
    patch,
)


class TestProvenance:
    def test_insert_receives_correct_processing_run_id(self):
        captured = {}

        def _ins(db, run_id, chunks):
            captured["run_id"] = run_id
            return len(chunks)

        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.knowledge.ingestion.get_extracted_text", return_value="Content here."),
            patch("app.api.knowledge.ingestion.delete_chunks_for_run"),
            patch("app.api.knowledge.ingestion.insert_chunks", side_effect=_ins),
            patch("app.api.knowledge.ingestion.update_run_status"),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert captured["run_id"] == RUN_ID

    def test_get_extracted_text_called_with_correct_document_version_id(self):
        captured = {}

        def _get_text(db, dv_id):
            captured["dv_id"] = dv_id
            return "Some text."

        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.knowledge.ingestion.get_extracted_text", side_effect=_get_text),
            patch("app.api.knowledge.ingestion.delete_chunks_for_run"),
            patch("app.api.knowledge.ingestion.insert_chunks"),
            patch("app.api.knowledge.ingestion.update_run_status"),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert captured["dv_id"] == DV_ID


class TestPhaseBoundary:
    def test_chunking_service_has_no_embedding_imports(self):
        import inspect

        import app.services.knowledge.chunking as mod

        src = inspect.getsource(mod)
        assert "openai" not in src
        assert "embedding" not in src.lower()
        assert "tiktoken" not in src
        assert "sentence_transformers" not in src

    def test_chunking_service_has_no_vector_storage(self):
        import inspect

        import app.services.knowledge.chunking as mod

        src = inspect.getsource(mod)
        assert "pinecone" not in src
        assert "pgvector" not in src
        assert "vector" not in src.lower()

    def test_chunking_service_has_no_retrieval(self):
        import inspect

        import app.services.knowledge.chunking as mod

        src = inspect.getsource(mod)
        assert "retrieval" not in src.lower()
        assert "similarity" not in src.lower()

    def test_chunk_endpoint_does_not_touch_retrieval_tables(self):
        db_mock = MagicMock()
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=db_mock),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.knowledge.ingestion.get_extracted_text", return_value="Text."),
            patch("app.api.knowledge.ingestion.delete_chunks_for_run"),
            patch("app.api.knowledge.ingestion.insert_chunks"),
            patch("app.api.knowledge.ingestion.update_run_status"),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        touched = [c.args[0] for c in db_mock.table.call_args_list if c.args]
        for forbidden in ("retrieval_operations", "retrieved_chunks", "message_citations"):
            assert forbidden not in touched

    def test_extraction_phase_unchanged(self):
        """Verify the extract endpoint still works and does not touch knowledge_chunks."""
        from tests.knowledge.extraction.support import FAKE_RUN_QUEUED, RUN_ID as EXT_RUN_ID

        db_mock = MagicMock()
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.knowledge.ingestion.get_admin_client", return_value=db_mock),
            patch("app.api.knowledge.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_QUEUED),
            patch("app.api.knowledge.ingestion.update_run_status"),
            patch("app.api.knowledge.ingestion.store_extracted_text"),
            patch("app.api.knowledge.ingestion.get_r2_client", return_value=MagicMock()),
            patch("app.api.knowledge.ingestion.download_file", return_value=b"text content"),
        ):
            response = client.post(
                f"/api/v1/documents/{EXT_RUN_ID}/extract", headers=_auth_headers()
            )

        assert response.status_code == 200
        touched = [c.args[0] for c in db_mock.table.call_args_list if c.args]
        assert "knowledge_chunks" not in touched
