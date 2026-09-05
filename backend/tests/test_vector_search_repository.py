from unittest.mock import MagicMock

import pytest

from app.repositories.vector_search import search_similar_chunks


QUERY = [0.25] * 1536


def _make_client(results=None):
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = results
    return client


def test_search_passes_query_and_top_k_to_database_function():
    client = _make_client([])

    assert search_similar_chunks(client, QUERY, top_k=4) == []

    client.rpc.assert_called_once_with(
        "search_similar_chunks",
        {"query_embedding": QUERY, "match_count": 4},
    )


def test_search_returns_identifiers_content_distance_and_database_order():
    results = [
        {
            "chunk_id": "chunk-2",
            "document_id": "document-2",
            "document_version_id": "version-2",
            "content_text": "near",
            "processing_run_id": "run-2",
            "chunk_sequence": 2,
            "section_title": "Admissions",
            "model_name": "qwen/qwen3-embedding-8b",
            "distance": 0.1,
        },
        {
            "chunk_id": "chunk-1",
            "document_id": "document-1",
            "document_version_id": "version-1",
            "content_text": "far",
            "processing_run_id": "run-1",
            "chunk_sequence": 1,
            "section_title": "Overview",
            "model_name": "qwen/qwen3-embedding-8b",
            "distance": 0.4,
        },
    ]

    returned = search_similar_chunks(_make_client(results), QUERY, top_k=2)

    assert returned == results
    assert [row["chunk_id"] for row in returned] == ["chunk-2", "chunk-1"]
    assert [row["distance"] for row in returned] == [0.1, 0.4]
    assert len({row["chunk_id"] for row in returned}) == len(returned)


def test_search_handles_empty_result():
    assert search_similar_chunks(_make_client(None), QUERY) == []


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_search_rejects_invalid_top_k(top_k):
    with pytest.raises(ValueError, match="top_k"):
        search_similar_chunks(_make_client(), QUERY, top_k=top_k)


@pytest.mark.parametrize(
    "embedding", [None, [], [0.1], "vector", [float("nan")] * 1536]
)
def test_search_rejects_invalid_or_empty_embedding(embedding):
    with pytest.raises(ValueError, match="embedding"):
        search_similar_chunks(_make_client(), embedding)


def test_database_errors_are_propagated_to_service_boundary():
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        search_similar_chunks(client, QUERY)
