"""Document extraction regressions: phase boundaries."""

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
# 12. Chunking not performed
# ---------------------------------------------------------------------------

def test_knowledge_chunks_table_never_touched():
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
        patch("app.api.knowledge.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    touched_tables = [c.args[0] for c in db_mock.table.call_args_list if c.args]
    assert "knowledge_chunks" not in touched_tables


def test_extraction_service_has_no_chunking_imports():
    import app.services.knowledge.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "knowledge_chunks" not in source
    assert "chunk" not in source.lower().replace("# chunk", "")


# ---------------------------------------------------------------------------
# 13. Embeddings not generated
# ---------------------------------------------------------------------------

def test_extraction_service_has_no_embedding_imports():
    import app.services.knowledge.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "openai" not in source
    assert "embedding" not in source.lower()
    assert "sentence_transformers" not in source
    assert "tiktoken" not in source


# ---------------------------------------------------------------------------
# 14. Vector storage not performed
# ---------------------------------------------------------------------------

def test_extraction_service_has_no_vector_storage():
    import app.services.knowledge.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "pinecone" not in source
    assert "pgvector" not in source
    assert "weaviate" not in source
    assert "vector" not in source.lower()


# ---------------------------------------------------------------------------
# 15. Retrieval not performed
# ---------------------------------------------------------------------------

def test_extraction_service_has_no_retrieval_calls():
    import app.services.knowledge.extraction as ext_module
    import inspect
    source = inspect.getsource(ext_module)
    assert "retrieval" not in source.lower()
    assert "similarity_search" not in source
    assert "retrieved_chunks" not in source


def test_extract_endpoint_does_not_touch_retrieval_tables():
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
        patch("app.api.knowledge.ingestion.download_file", return_value=b"text"),
    ):
        client.post(f"/api/v1/documents/{RUN_ID}/extract", headers=_auth_headers())

    touched_tables = [c.args[0] for c in db_mock.table.call_args_list if c.args]
    for forbidden in ("retrieval_operations", "retrieved_chunks", "message_citations"):
        assert forbidden not in touched_tables
