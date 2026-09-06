from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import AppError
from app.schemas.retrieval import RetrievalRequest
from app.services import retrieval


QUERY = [0.25] * 1536
SCOPE = {
    "institution_id": "institution-1",
    "knowledge_source_id": "source-1",
    "document_id": "document-1",
    "document_version_id": "version-1",
    "processing_run_id": "run-1",
}

UUID_SCOPE = {
    "institution_id": "00000000-0000-0000-0000-000000000001",
}


def test_valid_embedding_reaches_repository_unchanged():
    client = MagicMock()
    with (
        patch.object(retrieval, "get_admin_client", return_value=client),
        patch.object(retrieval, "search_similar_chunks", return_value=[]) as search,
    ):
        retrieval.retrieve_chunks(QUERY, institution_id="institution-1")

    assert search.call_args.args[1] is QUERY


@pytest.mark.parametrize(
    "embedding, message",
    [
        ([0.1], "exactly 1536"),
        (None, "required"),
        ([0.1] * 1535 + ["not-a-number"], "numeric"),
    ],
)
def test_invalid_embedding_is_rejected_before_repository_access(embedding, message):
    with (
        patch.object(retrieval, "get_admin_client") as get_client,
        patch.object(retrieval, "search_similar_chunks") as search,
    ):
        with pytest.raises(AppError, match=message):
            retrieval.retrieve_chunks(embedding, institution_id="institution-1")

    get_client.assert_not_called()
    search.assert_not_called()


def test_top_k_scope_and_model_are_passed_to_repository():
    client = MagicMock()
    with (
        patch.object(retrieval, "get_admin_client", return_value=client),
        patch.object(retrieval, "search_similar_chunks", return_value=[]) as search,
    ):
        retrieval.retrieve_chunks(
            QUERY,
            top_k=7,
            model_name="qwen/qwen3-embedding-8b",
            **SCOPE,
        )

    assert search.call_args.args[0] is client
    assert search.call_args.args[1] is QUERY
    assert search.call_args.kwargs == {
        "top_k": 7,
        "model_name": "qwen/qwen3-embedding-8b",
        **SCOPE,
    }


def test_repository_results_are_returned_without_dropping_distance():
    results = [
        {
            "chunk_id": "chunk-1",
            "content_text": "Admissions information",
            "processing_run_id": "run-1",
            "chunk_sequence": 1,
            "section_title": "Admissions",
            "model_name": "qwen/qwen3-embedding-8b",
            "distance": 0.12,
        }
    ]
    with (
        patch.object(retrieval, "get_admin_client", return_value=MagicMock()),
        patch.object(retrieval, "search_similar_chunks", return_value=results),
    ):
        returned = retrieval.retrieve_chunks(QUERY, institution_id="institution-1")

    assert returned == results
    assert returned[0]["distance"] == 0.12


def test_empty_repository_results_are_valid():
    with (
        patch.object(retrieval, "get_admin_client", return_value=MagicMock()),
        patch.object(retrieval, "search_similar_chunks", return_value=[]),
    ):
        assert retrieval.retrieve_chunks(QUERY, institution_id="institution-1") == []


def test_repository_validation_errors_use_app_error_convention():
    with (
        patch.object(retrieval, "get_admin_client", return_value=MagicMock()),
        patch.object(
            retrieval,
            "search_similar_chunks",
            side_effect=ValueError("internal validation detail"),
        ),
    ):
        with pytest.raises(AppError) as error:
            retrieval.retrieve_chunks(QUERY, institution_id="institution-1")

    assert error.value.status_code == 422
    assert error.value.code == "INVALID_RETRIEVAL_REQUEST"
    assert "internal validation detail" not in error.value.message


def test_repository_errors_are_safe_app_errors():
    with (
        patch.object(retrieval, "get_admin_client", return_value=MagicMock()),
        patch.object(
            retrieval,
            "search_similar_chunks",
            side_effect=RuntimeError("database credentials leaked"),
        ),
    ):
        with pytest.raises(AppError) as error:
            retrieval.retrieve_chunks(QUERY, institution_id="institution-1")

    assert error.value.status_code == 500
    assert error.value.code == "RETRIEVAL_FAILED"
    assert "database credentials leaked" not in error.value.message


def test_service_does_not_call_embedding_provider_or_llm():
    with (
        patch.object(retrieval, "get_admin_client", return_value=MagicMock()),
        patch.object(retrieval, "search_similar_chunks", return_value=[]),
        patch(
            "app.services.embedding_provider.get_embedding_provider"
        ) as get_provider,
    ):
        retrieval.retrieve_chunks(QUERY, institution_id="institution-1")

    get_provider.assert_not_called()


def test_request_normalizes_query_and_rejects_model_only_scope():
    with pytest.raises(ValueError, match="filter"):
        RetrievalRequest(
            query="  What   are   admissions hours?  ",
            model_name="qwen/qwen3-embedding-8b",
        )


def test_request_normalizes_query():
    request = RetrievalRequest(
        query="  What   are   admissions hours?  ",
        **UUID_SCOPE,
    )

    assert request.query == "What are admissions hours?"


@pytest.mark.parametrize(
    "scope",
    [
        {"institution_id": "00000000-0000-0000-0000-000000000001"},
        {"knowledge_source_id": "00000000-0000-0000-0000-000000000002"},
        {"document_id": "00000000-0000-0000-0000-000000000003"},
        {"document_version_id": "00000000-0000-0000-0000-000000000004"},
        {"processing_run_id": "00000000-0000-0000-0000-000000000005"},
    ],
)
def test_request_accepts_each_data_scope(scope):
    assert RetrievalRequest(query="admissions", **scope)


def test_request_accepts_data_scope_with_model_name():
    assert RetrievalRequest(
        query="admissions",
        institution_id="00000000-0000-0000-0000-000000000001",
        model_name="qwen/qwen3-embedding-8b",
    )


@pytest.mark.parametrize("query", ["", "   "])
def test_request_rejects_empty_query(query):
    with pytest.raises(ValueError, match="query"):
        RetrievalRequest(query=query, **UUID_SCOPE)


@pytest.mark.parametrize("top_k", [0, -1, True, "3"])
def test_request_rejects_invalid_top_k(top_k):
    with pytest.raises(ValueError, match="top_k"):
        RetrievalRequest(query="admissions", top_k=top_k, **UUID_SCOPE)


def test_request_rejects_unscoped_search():
    with pytest.raises(ValueError, match="filter"):
        RetrievalRequest(query="admissions")


def test_request_rejects_invalid_uuid_filter():
    with pytest.raises(ValueError, match="institution_id"):
        RetrievalRequest(query="admissions", institution_id="not-a-uuid")


def test_text_retrieval_passes_normalized_embedding_and_all_filters():
    request = RetrievalRequest(
        query="  admissions   hours ",
        top_k=3,
        institution_id="00000000-0000-0000-0000-000000000001",
        knowledge_source_id="00000000-0000-0000-0000-000000000002",
        document_id="00000000-0000-0000-0000-000000000003",
        document_version_id="00000000-0000-0000-0000-000000000004",
        processing_run_id="00000000-0000-0000-0000-000000000005",
        model_name="custom-model",
    )
    embedding = [0.25] * 1536
    rows = [
        {
            "chunk_id": "00000000-0000-0000-0000-000000000006",
            "document_id": "00000000-0000-0000-0000-000000000003",
            "document_version_id": "00000000-0000-0000-0000-000000000004",
            "content_text": "Admissions hours",
            "processing_run_id": "00000000-0000-0000-0000-000000000005",
            "chunk_sequence": 2,
            "section_title": "Admissions",
            "model_name": "custom-model",
            "distance": 0.2,
        }
    ]
    with (
        patch.object(retrieval, "embed_query", return_value=embedding) as embed,
        patch.object(retrieval, "search_chunks", return_value=rows) as search,
    ):
        response = retrieval.retrieve(request)

    embed.assert_called_once_with("admissions hours")
    assert search.call_args.kwargs == {
        "top_k": 3,
        "institution_id": "00000000-0000-0000-0000-000000000001",
        "knowledge_source_id": "00000000-0000-0000-0000-000000000002",
        "document_id": "00000000-0000-0000-0000-000000000003",
        "document_version_id": "00000000-0000-0000-0000-000000000004",
        "processing_run_id": "00000000-0000-0000-0000-000000000005",
        "model_name": "custom-model",
    }
    assert response.results[0].similarity_score == 0.8
    assert response.results[0].text == "Admissions hours"
    assert response.results[0].metadata["section_title"] == "Admissions"


def test_text_retrieval_preserves_database_order_and_empty_results():
    request = RetrievalRequest(query="admissions", **UUID_SCOPE)
    with (
        patch.object(retrieval, "embed_query", return_value=[0.25] * 1536),
        patch.object(retrieval, "search_chunks", return_value=[]),
    ):
        assert retrieval.retrieve(request).results == []


def test_embedding_failure_is_wrapped():
    request = RetrievalRequest(query="admissions", **UUID_SCOPE)
    with patch.object(retrieval, "embed_query", side_effect=RuntimeError("provider down")):
        with pytest.raises(AppError) as error:
            retrieval.retrieve(request)

    assert error.value.code == "EMBEDDING_FAILED"
    assert error.value.status_code == 500


def test_invalid_query_embedding_is_rejected_by_embedding_service():
    from app.services import embeddings

    provider = MagicMock()
    provider.embed.return_value = [[0.1]]
    with pytest.raises(ValueError, match="dimensions"):
        embeddings.embed_query("admissions", provider)