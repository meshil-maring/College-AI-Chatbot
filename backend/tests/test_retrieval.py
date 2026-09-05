from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import AppError
from app.services import retrieval


QUERY = [0.25] * 1536
SCOPE = {
    "institution_id": "institution-1",
    "knowledge_source_id": "source-1",
    "document_id": "document-1",
    "document_version_id": "version-1",
    "processing_run_id": "run-1",
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