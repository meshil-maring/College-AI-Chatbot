from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.core.errors import AppError
from app.services import embeddings


RUN_ID = "run-1"
MODEL = "text-embedding-3-small"
DIMENSIONS = 3
CHUNKS = [
    {"chunk_id": "chunk-1", "content_text": "first", "chunk_sequence": 1},
    {"chunk_id": "chunk-2", "content_text": "second", "chunk_sequence": 2},
]


@contextmanager
def _patch_service(run=None, chunks=None, api_key="test-key", batch_size=100):
    client = MagicMock()
    provider = MagicMock()
    settings = embeddings.settings
    with (
        patch.object(embeddings, "get_admin_client", return_value=client),
        patch.object(
            embeddings,
            "get_processing_run_with_version",
            return_value=run or {"embedding_status": None},
        ),
        patch.object(embeddings, "get_chunks_for_run", return_value=chunks if chunks is not None else CHUNKS),
        patch.object(embeddings, "get_embedding_provider", return_value=provider),
        patch.object(settings, "openrouter_api_key", api_key),
        patch.object(settings, "embedding_model", MODEL),
        patch.object(settings, "embedding_dimensions", DIMENSIONS),
        patch.object(settings, "embedding_batch_size", batch_size),
    ):
        yield client, provider


def test_success_batches_and_persists_configured_values():
    with _patch_service(batch_size=1) as (client, provider):
        provider.embed.side_effect = [[[0.1, 0.2, 0.3]], [[0.4, 0.5, 0.6]]]
        with patch.object(embeddings, "delete_embeddings_for_run") as delete, patch.object(
            embeddings, "upsert_chunk_embeddings", return_value=1
        ) as upsert, patch.object(embeddings, "update_run_embedding_status") as update:
            assert embeddings.embed_processing_run(RUN_ID) == 2

        assert provider.embed.call_count == 2
        assert provider.embed.call_args_list[0].args == (["first"],)
        assert provider.embed.call_args_list[1].args == (["second"],)
        delete.assert_called_once_with(client, RUN_ID, MODEL)
        assert update.call_args_list[0].args[2] == "processing"
        assert update.call_args_list[-1].args[2] == "embedded"


def test_count_mismatch_marks_failed():
    with _patch_service() as (_, provider):
        provider.embed.return_value = []
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError, match="count"):
                embeddings.embed_processing_run(RUN_ID)
        assert update.call_args_list[-1].args[2] == "failed"


def test_dimension_mismatch_marks_failed():
    with _patch_service() as (_, provider):
        provider.embed.return_value = [[0.1], [0.2]]
        with pytest.raises(AppError, match="dimensions"):
            embeddings.embed_processing_run(RUN_ID)


def test_provider_failure_is_wrapped_without_api_key():
    with _patch_service(api_key="secret-key") as (_, provider):
        provider.embed.side_effect = RuntimeError("secret-key refused")
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError) as error:
                embeddings.embed_processing_run(RUN_ID)
        assert "secret-key" not in str(error.value)
        assert "secret-key" not in update.call_args_list[-1].args[3]


def test_failed_run_can_retry():
    with _patch_service(run={"embedding_status": "failed"}) as (_, provider):
        provider.embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        with patch.object(embeddings, "delete_embeddings_for_run") as delete, patch.object(
            embeddings, "upsert_chunk_embeddings", return_value=2
        ):
            assert embeddings.embed_processing_run(RUN_ID) == 2
        delete.assert_called_once()


def test_embedded_run_is_terminal():
    with _patch_service(run={"embedding_status": "embedded"}) as (_, provider):
        with patch.object(embeddings, "update_run_embedding_status") as update:
            assert embeddings.embed_processing_run(RUN_ID) == 0
        provider.embed.assert_not_called()
        update.assert_not_called()


def test_empty_chunks_fail_cleanly():
    with _patch_service(chunks=[]) as (_, _):
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError, match="no chunks"):
                embeddings.embed_processing_run(RUN_ID)
        assert update.call_args_list[-1].args[2] == "failed"


def test_failure_error_is_truncated():
    with _patch_service() as (_, provider):
        provider.embed.side_effect = RuntimeError("x" * 2000)
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError):
                embeddings.embed_processing_run(RUN_ID)
        assert len(update.call_args_list[-1].args[3]) == 1000


def test_repository_functions_are_used():
    with _patch_service() as (client, provider):
        provider.embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        with (
            patch.object(embeddings, "get_chunks_for_run", return_value=CHUNKS) as get_chunks,
            patch.object(embeddings, "delete_embeddings_for_run") as delete,
            patch.object(embeddings, "upsert_chunk_embeddings", return_value=2) as upsert,
            patch.object(embeddings, "update_run_embedding_status") as update,
        ):
            embeddings.embed_processing_run(RUN_ID)
        get_chunks.assert_called_once_with(client, RUN_ID)
        delete.assert_called_once_with(client, RUN_ID, MODEL)
        upsert.assert_called_once()
        assert update.call_count == 2


# ---------------------------------------------------------------------------
# Query-embedding cache (short-lived, configuration-keyed, LRU-bounded).
# ---------------------------------------------------------------------------


def test_query_embedding_repeated_query_hits_cache():
    embeddings._QUERY_EMBEDDING_CACHE.clear()
    provider = MagicMock()
    provider.embed.return_value = [[0.1, 0.2, 0.3]]
    settings = embeddings.settings
    with (
        patch.object(embeddings, "get_embedding_provider") as get_provider,
        patch.object(settings, "embedding_model", MODEL),
        patch.object(settings, "embedding_dimensions", DIMENSIONS),
        patch.object(settings, "openrouter_api_key", "test-key"),
    ):
        get_provider.side_effect = lambda: provider
        assert embeddings.embed_query("What is the hostel fee?") == [0.1, 0.2, 0.3]
        # Second identical call: no provider round trip.
        assert embeddings.embed_query("What is the hostel fee?") == [0.1, 0.2, 0.3]
    assert provider.embed.call_count == 1
    embeddings._QUERY_EMBEDDING_CACHE.clear()


def test_query_embedding_cache_keyed_by_model_configuration():
    embeddings._QUERY_EMBEDDING_CACHE.clear()
    provider = MagicMock()
    provider.embed.return_value = [[0.1, 0.2, 0.3]]
    settings = embeddings.settings
    with (
        patch.object(embeddings, "get_embedding_provider") as get_provider,
        patch.object(settings, "embedding_model", "model-a"),
        patch.object(settings, "embedding_dimensions", DIMENSIONS),
        patch.object(settings, "openrouter_api_key", "test-key"),
    ):
        get_provider.side_effect = lambda: provider
        embeddings.embed_query("same text")
    with (
        patch.object(embeddings, "get_embedding_provider") as get_provider,
        patch.object(settings, "embedding_model", "model-b"),
        patch.object(settings, "embedding_dimensions", DIMENSIONS),
        patch.object(settings, "openrouter_api_key", "test-key"),
    ):
        get_provider.side_effect = lambda: provider
        embeddings.embed_query("same text")
    # Different embedding configuration => different cache key => new call.
    assert provider.embed.call_count == 2
    embeddings._QUERY_EMBEDDING_CACHE.clear()


def test_query_embedding_explicit_provider_bypasses_cache():
    embeddings._QUERY_EMBEDDING_CACHE.clear()
    cached_provider = MagicMock()
    cached_provider.embed.return_value = [[0.1, 0.2, 0.3]]
    explicit_provider = MagicMock()
    explicit_provider.embed.return_value = [[0.1, 0.2, 0.3]]
    settings = embeddings.settings
    with (
        patch.object(embeddings, "get_embedding_provider") as get_provider,
        patch.object(settings, "embedding_model", MODEL),
        patch.object(settings, "embedding_dimensions", DIMENSIONS),
        patch.object(settings, "openrouter_api_key", "test-key"),
    ):
        get_provider.side_effect = lambda: cached_provider
        embeddings.embed_query("same text")
        # Document/ingestion paths pass an explicit provider and must NOT hit
        # the query cache.
        embeddings.embed_query("same text", provider=explicit_provider)
        embeddings.embed_query("same text", provider=explicit_provider)
    assert cached_provider.embed.call_count == 1
    assert explicit_provider.embed.call_count == 2
    embeddings._QUERY_EMBEDDING_CACHE.clear()