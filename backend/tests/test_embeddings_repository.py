from unittest.mock import MagicMock

from app.repositories import embeddings


RUN_ID = "pr000000-0000-0000-0000-000000000001"
MODEL_NAME = "text-embedding-3-small"


def _make_client(chunks=None):
    client = MagicMock()
    chunks_table = MagicMock()
    chunks_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
        chunks or []
    )
    client.table.side_effect = lambda name: chunks_table
    return client, chunks_table


def test_get_chunks_for_run_requests_sequence_order():
    chunks = [
        {"chunk_id": "chunk-2", "content_text": "second", "chunk_sequence": 2},
        {"chunk_id": "chunk-1", "content_text": "first", "chunk_sequence": 1},
    ]
    client, table = _make_client(chunks)

    result = embeddings.get_chunks_for_run(client, RUN_ID)

    assert result == chunks
    table.select.assert_called_once_with("chunk_id, content_text, chunk_sequence")
    table.select.return_value.eq.assert_called_once_with(
        "processing_run_id", RUN_ID
    )
    table.select.return_value.eq.return_value.order.assert_called_once_with(
        "chunk_sequence"
    )


def test_delete_embeddings_for_run_scopes_run_and_model():
    chunks = [
        {"chunk_id": "chunk-1", "content_text": "one", "chunk_sequence": 1},
        {"chunk_id": "chunk-2", "content_text": "two", "chunk_sequence": 2},
    ]
    client, chunks_table = _make_client(chunks)
    embeddings_table = MagicMock()
    client.table.side_effect = lambda name: (
        chunks_table if name == "knowledge_chunks" else embeddings_table
    )

    embeddings.delete_embeddings_for_run(client, RUN_ID, MODEL_NAME)

    delete_chain = embeddings_table.delete.return_value
    delete_chain.in_.assert_called_once_with("chunk_id", ["chunk-1", "chunk-2"])
    delete_chain.in_.return_value.eq.assert_called_once_with("model_name", MODEL_NAME)
    delete_chain.in_.return_value.eq.return_value.execute.assert_called_once_with()


def test_upsert_chunk_embeddings_persists_required_fields():
    client = MagicMock()
    embeddings_table = MagicMock()
    client.table.return_value = embeddings_table
    rows = [
        {"chunk_id": "chunk-1", "embedding": [0.1, 0.2]},
        {"chunk_id": "chunk-2", "embedding": [0.3, 0.4]},
    ]

    count = embeddings.upsert_chunk_embeddings(client, MODEL_NAME, 1536, rows)

    assert count == 2
    embeddings_table.upsert.assert_called_once_with(
        [
            {
                "chunk_id": "chunk-1",
                "model_name": MODEL_NAME,
                "embedding_dimensions": 1536,
                "embedding": [0.1, 0.2],
            },
            {
                "chunk_id": "chunk-2",
                "model_name": MODEL_NAME,
                "embedding_dimensions": 1536,
                "embedding": [0.3, 0.4],
            },
        ],
        on_conflict="chunk_id,model_name",
    )


def test_update_run_embedding_status_changes_only_embedding_fields():
    client = MagicMock()
    runs_table = MagicMock()
    client.table.return_value = runs_table

    embeddings.update_run_embedding_status(
        client,
        RUN_ID,
        "failed",
        "x" * 1500,
    )

    runs_table.update.assert_called_once_with(
        {"embedding_status": "failed", "embedding_error": "x" * 1000}
    )
    runs_table.update.return_value.eq.assert_called_once_with(
        "processing_run_id", RUN_ID
    )
    assert "status" not in runs_table.update.call_args.args[0]


def test_repository_does_not_import_openai():
    assert "openai" not in embeddings.__dict__