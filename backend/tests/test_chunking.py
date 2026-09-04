"""
Tests for Phase 3.5 — Text Chunking.

Covers:
  - Normal multi-paragraph document
  - Sentence-boundary splitting
  - Hard-limit splitting
  - Overlap carry-over
  - Sequence numbering (1-based, contiguous)
  - Section title detection and propagation
  - Empty extracted text
  - Oversized single paragraph
  - Idempotent re-processing (delete + reinsert)
  - Partial insertion failure / cleanup
  - Invalid processing run (404)
  - Wrong processing status (409)
  - Provenance: response contains correct document_version_id
  - No embeddings / vector / retrieval side-effects
"""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.chunking import _build_chunks, _is_heading, _split_paragraph, chunk_text

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DV_ID = "d0000000-0000-0000-0000-000000000002"
RUN_ID = "a0000000-0000-0000-0000-000000000002"

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
FAKE_RUN_READY = {
    "processing_run_id": RUN_ID,
    "status": "ready",
    "document_version_id": DV_ID,
    "document_versions": {
        "document_version_id": DV_ID,
        "storage_bucket": "college-ai-knowledge",
        "storage_object_key": "inst/ks/ver/doc.txt",
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


def _post_chunk(
    run_id=RUN_ID,
    run=None,
    extracted_text="Some text.",
    delete_side_effect=None,
    insert_side_effect=None,
):
    fake_run = run if run is not None else FAKE_RUN_READY
    p1, p2 = _patch_auth()
    delete_mock = MagicMock(side_effect=delete_side_effect)
    insert_mock = MagicMock(side_effect=insert_side_effect)
    update_mock = MagicMock()
    with (
        p1,
        p2,
        patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
        patch("app.api.ingestion.get_processing_run_with_version", return_value=fake_run),
        patch("app.api.ingestion.get_extracted_text", return_value=extracted_text),
        patch("app.api.ingestion.delete_chunks_for_run", delete_mock),
        patch("app.api.ingestion.insert_chunks", insert_mock),
        patch("app.api.ingestion.update_run_status", update_mock),
    ):
        response = client.post(f"/api/v1/documents/{run_id}/chunk", headers=_auth_headers())
    return response, delete_mock, insert_mock, update_mock


# ===========================================================================
# Unit tests — chunking service
# ===========================================================================


class TestIsHeading:
    def test_all_caps_short_line(self):
        assert _is_heading("INTRODUCTION")

    def test_numbered_section(self):
        assert _is_heading("1.2. Admission Requirements")

    def test_mixed_case_long_line_not_heading(self):
        assert not _is_heading("This is a normal sentence with lowercase letters.")

    def test_empty_string_not_heading(self):
        assert not _is_heading("")

    def test_line_over_80_chars_not_heading(self):
        assert not _is_heading("A" * 81)


class TestSplitParagraph:
    def test_splits_at_sentence_boundary(self):
        para = "First sentence. Second sentence. Third sentence."
        pieces = _split_paragraph(para, target=30)
        assert all(len(p) <= 30 for p in pieces)
        # All original words must appear across the pieces
        combined = " ".join(pieces)
        for word in ["First", "Second", "Third"]:
            assert word in combined

    def test_hard_cut_when_sentence_exceeds_target(self):
        long_word = "x" * 100
        pieces = _split_paragraph(long_word, target=40)
        assert all(len(p) <= 40 for p in pieces)
        assert "".join(pieces) == long_word

    def test_single_sentence_within_target_unchanged(self):
        para = "Short sentence."
        pieces = _split_paragraph(para, target=200)
        assert pieces == ["Short sentence."]


class TestBuildChunks:
    def test_empty_text_returns_empty(self):
        assert _build_chunks("") == []

    def test_whitespace_only_returns_empty(self):
        assert _build_chunks("   \n\n   ") == []

    def test_single_short_paragraph_one_chunk(self):
        chunks = _build_chunks("Hello world.")
        assert len(chunks) == 1
        assert chunks[0]["content_text"] == "Hello world."

    def test_sequence_starts_at_one(self):
        text = "\n\n".join(["Para " + str(i) + " " + "x" * 100 for i in range(5)])
        chunks = _build_chunks(text, target=200, overlap=20)
        assert chunks[0]["chunk_sequence"] == 1

    def test_sequence_is_contiguous(self):
        text = "\n\n".join(["Para " + str(i) + " " + "x" * 300 for i in range(10)])
        chunks = _build_chunks(text, target=400, overlap=50)
        seqs = [c["chunk_sequence"] for c in chunks]
        assert seqs == list(range(1, len(chunks) + 1))

    def test_multi_paragraph_produces_multiple_chunks(self):
        para = "word " * 500  # ~2500 chars
        text = para + "\n\n" + para
        chunks = _build_chunks(text, target=2000, overlap=200)
        assert len(chunks) >= 2

    def test_token_count_is_estimate(self):
        chunks = _build_chunks("Hello world this is a test.")
        assert chunks[0]["token_count"] == len(chunks[0]["content_text"]) // 4

    def test_token_count_non_negative(self):
        chunks = _build_chunks("Hi.")
        assert chunks[0]["token_count"] >= 0

    def test_page_metadata_absent(self):
        """chunk_text returns dicts — page_start/page_end are not in the service output."""
        chunks = chunk_text("Some text here.")
        for c in chunks:
            assert "page_start" not in c
            assert "page_end" not in c

    def test_content_text_not_empty(self):
        text = "\n\n".join(["Paragraph " + str(i) for i in range(20)])
        chunks = _build_chunks(text)
        for c in chunks:
            assert c["content_text"].strip() != ""

    def test_all_text_preserved_across_chunks(self):
        """Every word in the source appears in at least one chunk."""
        words = ["alpha", "beta", "gamma", "delta", "epsilon"]
        text = "\n\n".join(w * 10 + " content" for w in words)
        chunks = _build_chunks(text, target=100, overlap=20)
        combined = " ".join(c["content_text"] for c in chunks)
        for w in words:
            assert w in combined


class TestSectionTitles:
    def test_heading_captured_as_section_title(self):
        text = "INTRODUCTION\n\nThis section covers the basics of the program."
        chunks = _build_chunks(text)
        assert any(c["section_title"] == "INTRODUCTION" for c in chunks)

    def test_section_title_propagates_to_following_chunk(self):
        heading = "POLICIES AND PROCEDURES"
        body = ("This is policy content. " * 100).strip()
        text = heading + "\n\n" + body
        chunks = _build_chunks(text, target=300, overlap=50)
        # All chunks after the heading should carry the section title
        content_chunks = [c for c in chunks if c["content_text"] != heading]
        assert all(c["section_title"] == heading for c in content_chunks)

    def test_no_heading_section_title_is_none(self):
        text = "Just a normal paragraph without any heading."
        chunks = _build_chunks(text)
        assert chunks[0]["section_title"] is None

    def test_numbered_heading_detected(self):
        text = "1.1. Eligibility Criteria\n\nStudents must meet the following requirements."
        chunks = _build_chunks(text)
        assert any(c["section_title"] is not None for c in chunks)


class TestOverlap:
    def test_overlap_text_appears_in_consecutive_chunks(self):
        # Build text that forces at least 2 chunks
        para_a = "Alpha content. " * 80   # ~1200 chars
        para_b = "Beta content. " * 80    # ~1120 chars
        para_c = "Gamma content. " * 80   # ~1200 chars
        text = para_a.strip() + "\n\n" + para_b.strip() + "\n\n" + para_c.strip()
        chunks = _build_chunks(text, target=2000, overlap=200)
        assert len(chunks) >= 2
        # The tail of chunk N should appear somewhere in chunk N+1
        tail = chunks[0]["content_text"][-100:]
        assert tail in chunks[1]["content_text"]

    def test_overlap_does_not_exceed_target_significantly(self):
        para = "sentence content here. " * 200
        chunks = _build_chunks(para, target=2000, overlap=200)
        for c in chunks:
            # Allow some slack for sentence-boundary rounding
            assert len(c["content_text"]) <= 2000 + 500


class TestOversizedParagraph:
    def test_single_oversized_paragraph_split_into_multiple_chunks(self):
        big = "word " * 1000  # ~5000 chars
        chunks = _build_chunks(big, target=2000, overlap=200)
        assert len(chunks) >= 2

    def test_hard_limit_applied_when_no_sentence_boundary(self):
        no_sentences = "x" * 6000
        chunks = _build_chunks(no_sentences, target=2000, overlap=200)
        assert len(chunks) >= 2
        for c in chunks:
            # Allow for overlap separator ("\n\n" = 2 chars) on top of target
            assert len(c["content_text"]) <= 2300


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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.ingestion.get_extracted_text", return_value="Hello world."),
            patch("app.api.ingestion.delete_chunks_for_run", side_effect=_del),
            patch("app.api.ingestion.insert_chunks", side_effect=_ins),
            patch("app.api.ingestion.update_run_status"),
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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.ingestion.get_extracted_text", return_value="Content."),
            patch("app.api.ingestion.delete_chunks_for_run"),
            patch("app.api.ingestion.insert_chunks", side_effect=Exception("write error")),
            patch("app.api.ingestion.update_run_status", side_effect=_update),
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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.ingestion.get_extracted_text", return_value="Content."),
            patch("app.api.ingestion.delete_chunks_for_run"),
            patch("app.api.ingestion.insert_chunks", side_effect=Exception("e" * 2000)),
            patch("app.api.ingestion.update_run_status", side_effect=_update),
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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.ingestion.get_extracted_text", return_value="Content."),
            patch("app.api.ingestion.delete_chunks_for_run"),
            patch("app.api.ingestion.insert_chunks", side_effect=Exception("fail")),
            patch("app.api.ingestion.update_run_status", side_effect=_update),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert "completed_at" in captured


class TestInvalidRun:
    def test_run_not_found_returns_404(self):
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=None),
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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=queued_run),
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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=processing_run),
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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=failed_run),
        ):
            response = client.post(
                f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers()
            )
        assert response.status_code == 409


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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.ingestion.get_extracted_text", return_value="Content here."),
            patch("app.api.ingestion.delete_chunks_for_run"),
            patch("app.api.ingestion.insert_chunks", side_effect=_ins),
            patch("app.api.ingestion.update_run_status"),
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
            patch("app.api.ingestion.get_admin_client", return_value=MagicMock()),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.ingestion.get_extracted_text", side_effect=_get_text),
            patch("app.api.ingestion.delete_chunks_for_run"),
            patch("app.api.ingestion.insert_chunks"),
            patch("app.api.ingestion.update_run_status"),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        assert captured["dv_id"] == DV_ID


class TestPhaseBoundary:
    def test_chunking_service_has_no_embedding_imports(self):
        import inspect

        import app.services.chunking as mod

        src = inspect.getsource(mod)
        assert "openai" not in src
        assert "embedding" not in src.lower()
        assert "tiktoken" not in src
        assert "sentence_transformers" not in src

    def test_chunking_service_has_no_vector_storage(self):
        import inspect

        import app.services.chunking as mod

        src = inspect.getsource(mod)
        assert "pinecone" not in src
        assert "pgvector" not in src
        assert "vector" not in src.lower()

    def test_chunking_service_has_no_retrieval(self):
        import inspect

        import app.services.chunking as mod

        src = inspect.getsource(mod)
        assert "retrieval" not in src.lower()
        assert "similarity" not in src.lower()

    def test_chunk_endpoint_does_not_touch_retrieval_tables(self):
        db_mock = MagicMock()
        p1, p2 = _patch_auth()
        with (
            p1,
            p2,
            patch("app.api.ingestion.get_admin_client", return_value=db_mock),
            patch("app.api.ingestion.get_processing_run_with_version", return_value=FAKE_RUN_READY),
            patch("app.api.ingestion.get_extracted_text", return_value="Text."),
            patch("app.api.ingestion.delete_chunks_for_run"),
            patch("app.api.ingestion.insert_chunks"),
            patch("app.api.ingestion.update_run_status"),
        ):
            client.post(f"/api/v1/documents/{RUN_ID}/chunk", headers=_auth_headers())

        touched = [c.args[0] for c in db_mock.table.call_args_list if c.args]
        for forbidden in ("retrieval_operations", "retrieved_chunks", "message_citations"):
            assert forbidden not in touched

    def test_extraction_phase_unchanged(self):
        """Verify the extract endpoint still works and does not touch knowledge_chunks."""
        from tests.test_extraction import FAKE_RUN_QUEUED, RUN_ID as EXT_RUN_ID

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
            patch("app.api.ingestion.download_file", return_value=b"text content"),
        ):
            response = client.post(
                f"/api/v1/documents/{EXT_RUN_ID}/extract", headers=_auth_headers()
            )

        assert response.status_code == 200
        touched = [c.args[0] for c in db_mock.table.call_args_list if c.args]
        assert "knowledge_chunks" not in touched
