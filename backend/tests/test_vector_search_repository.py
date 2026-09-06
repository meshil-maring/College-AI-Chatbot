from unittest.mock import MagicMock

import pytest

from app.repositories.vector_search import search_similar_chunks


QUERY = [0.25] * 1536
MODEL_NAME = "qwen/qwen3-embedding-8b"
SCOPE = {"institution_id": "institution-1"}


def _make_client(results=None):
    client = MagicMock()
    client.rpc.return_value.execute.return_value.data = results
    return client


def test_search_passes_query_and_top_k_to_database_function():
    client = _make_client([])

    assert search_similar_chunks(client, QUERY, top_k=4, **SCOPE, model_name=MODEL_NAME) == []

    client.rpc.assert_called_once_with(
        "search_similar_chunks",
        {
            "query_embedding": QUERY,
            "match_count": 4,
            "filter_institution_id": "institution-1",
            "filter_knowledge_source_id": None,
            "filter_document_id": None,
            "filter_document_version_id": None,
            "filter_processing_run_id": None,
            "filter_model_name": MODEL_NAME,
        },
    )


@pytest.mark.parametrize(
    "filter_name",
    [
        "institution_id",
        "knowledge_source_id",
        "document_id",
        "document_version_id",
        "processing_run_id",
    ],
)
def test_each_filter_is_forwarded(filter_name):
    client = _make_client([])

    filter_value = MODEL_NAME if filter_name == "model_name" else f"{filter_name}-1"
    search_similar_chunks(
        client,
        QUERY,
        **{filter_name: filter_value},
        **({} if filter_name == "model_name" else {"model_name": MODEL_NAME}),
    )

    payload = client.rpc.call_args.args[1]
    assert payload[f"filter_{filter_name}"] == filter_value
    assert sum(
        value is not None
        for key, value in payload.items()
        if key.startswith("filter_")
    ) == 2


def test_model_name_is_forwarded_with_a_real_scope():
    client = _make_client([])

    search_similar_chunks(
        client,
        QUERY,
        institution_id="institution-1",
        model_name=MODEL_NAME,
    )

    payload = client.rpc.call_args.args[1]
    assert payload["filter_institution_id"] == "institution-1"
    assert payload["filter_model_name"] == MODEL_NAME


def test_all_filters_and_model_are_forwarded():
    client = _make_client([])
    scope = {
        "institution_id": "institution-1",
        "knowledge_source_id": "source-1",
        "document_id": "document-1",
        "document_version_id": "version-1",
        "processing_run_id": "run-1",
    }

    search_similar_chunks(client, QUERY, **scope, model_name=MODEL_NAME)

    assert client.rpc.call_args.args[1] == {
        "query_embedding": QUERY,
        "match_count": 10,
        "filter_institution_id": "institution-1",
        "filter_knowledge_source_id": "source-1",
        "filter_document_id": "document-1",
        "filter_document_version_id": "version-1",
        "filter_processing_run_id": "run-1",
        "filter_model_name": MODEL_NAME,
    }


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

    returned = search_similar_chunks(
        _make_client(results), QUERY, top_k=2, **SCOPE, model_name=MODEL_NAME
    )

    assert returned == results
    assert [row["chunk_id"] for row in returned] == ["chunk-2", "chunk-1"]
    assert [row["distance"] for row in returned] == [0.1, 0.4]
    assert len({row["chunk_id"] for row in returned}) == len(returned)


def test_search_handles_empty_result():
    assert search_similar_chunks(
        _make_client(None), QUERY, **SCOPE, model_name=MODEL_NAME
    ) == []


@pytest.mark.parametrize("top_k", [0, -1, True, 1.5])
def test_search_rejects_invalid_top_k(top_k):
    with pytest.raises(ValueError, match="top_k"):
        search_similar_chunks(
            _make_client(), QUERY, top_k=top_k, **SCOPE, model_name=MODEL_NAME
        )


def test_search_rejects_missing_model_name():
    with pytest.raises(ValueError, match="model_name"):
        search_similar_chunks(_make_client(), QUERY, **SCOPE)


def test_unscoped_search_is_rejected_without_calling_supabase():
    client = _make_client()

    with pytest.raises(ValueError, match="filter"):
        search_similar_chunks(client, QUERY, model_name=MODEL_NAME)

    client.rpc.assert_not_called()


@pytest.mark.parametrize(
    "embedding", [None, [], [0.1], "vector", [float("nan")] * 1536]
)
def test_search_rejects_invalid_or_empty_embedding(embedding):
    with pytest.raises(ValueError, match="embedding"):
        search_similar_chunks(
            _make_client(), embedding, **SCOPE, model_name=MODEL_NAME
        )


def test_database_errors_are_propagated_to_service_boundary():
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        search_similar_chunks(client, QUERY, **SCOPE, model_name=MODEL_NAME)
