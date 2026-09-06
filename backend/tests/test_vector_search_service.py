from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import AppError
from app.services import vector_search


QUERY = [0.25] * 1536
SCOPE = {"institution_id": "institution-1"}


def test_service_uses_admin_client_and_preserves_results():
    client = MagicMock()
    results = [{"chunk_id": "chunk-1", "distance": 0.2}]
    with (
        patch.object(vector_search, "get_admin_client", return_value=client),
        patch.object(
            vector_search, "search_similar_chunks", return_value=results
        ) as search,
    ):
        assert vector_search.search_chunks(QUERY, top_k=3, **SCOPE) == results

    search.assert_called_once_with(
        client,
        QUERY,
        top_k=3,
        model_name="qwen/qwen3-embedding-8b",
        institution_id="institution-1",
        knowledge_source_id=None,
        document_id=None,
        document_version_id=None,
        processing_run_id=None,
    )


def test_service_rejects_wrong_dimension():
    with pytest.raises(AppError) as error:
        vector_search.search_chunks([0.1])

    assert error.value.code == "INVALID_QUERY_EMBEDDING"
    assert error.value.status_code == 422


def test_service_rejects_unscoped_search_before_client_access():
    with patch.object(vector_search, "get_admin_client") as get_client:
        with pytest.raises(AppError, match="scope") as error:
            vector_search.search_chunks(QUERY, model_name="custom-model")

    assert error.value.code == "INVALID_VECTOR_SEARCH_REQUEST"
    assert error.value.status_code == 422
    get_client.assert_not_called()


def test_service_maps_repository_validation_error():
    with patch.object(
        vector_search,
        "search_similar_chunks",
        side_effect=ValueError("internal detail"),
    ):
        with pytest.raises(AppError) as error:
            vector_search.search_chunks(QUERY, **SCOPE)

    assert error.value.code == "INVALID_VECTOR_SEARCH_REQUEST"
    assert error.value.message == "Invalid vector search request"


def test_service_maps_database_error_without_exposing_details():
    with patch.object(
        vector_search,
        "search_similar_chunks",
        side_effect=RuntimeError("database credentials leaked"),
    ):
        with pytest.raises(AppError) as error:
            vector_search.search_chunks(QUERY, **SCOPE)

    assert error.value.code == "VECTOR_SEARCH_FAILED"
    assert error.value.message == "Vector search failed"
