from contextlib import contextmanager
from types import SimpleNamespace
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


def _response(vectors):
    return SimpleNamespace(
        data=[SimpleNamespace(embedding=vector) for vector in vectors]
    )


@contextmanager
def _patch_service(run=None, chunks=None, api_key="test-key", batch_size=100):
    client = MagicMock()
    openai_client = MagicMock()
    settings = embeddings.settings
    with (
        patch.object(embeddings, "get_admin_client", return_value=client),
        patch.object(
            embeddings,
            "get_processing_run_with_version",
            return_value=run or {"embedding_status": None},
        ),
        patch.object(embeddings, "get_chunks_for_run", return_value=chunks if chunks is not None else CHUNKS),
        patch.object(embeddings, "OpenAI", return_value=openai_client),
        patch.object(settings, "openai_api_key", api_key),
        patch.object(settings, "embedding_model", MODEL),
        patch.object(settings, "embedding_dimensions", DIMENSIONS),
        patch.object(settings, "embedding_batch_size", batch_size),
    ):
        yield client, openai_client


def test_success_batches_and_persists_configured_values():
    with _patch_service(batch_size=1) as (client, openai_client):
        openai_client.embeddings.create.side_effect = [
            _response([[0.1, 0.2, 0.3]]),
            _response([[0.4, 0.5, 0.6]]),
        ]
        with patch.object(embeddings, "delete_embeddings_for_run") as delete, patch.object(
            embeddings, "upsert_chunk_embeddings", return_value=1
        ) as upsert, patch.object(embeddings, "update_run_embedding_status") as update:
            assert embeddings.embed_processing_run(RUN_ID) == 2

        assert openai_client.embeddings.create.call_count == 2
        assert openai_client.embeddings.create.call_args.kwargs["model"] == MODEL
        assert openai_client.embeddings.create.call_args.kwargs["dimensions"] == DIMENSIONS
        delete.assert_called_once_with(client, RUN_ID, MODEL)
        assert update.call_args_list[0].args[2] == "processing"
        assert update.call_args_list[-1].args[2] == "embedded"


def test_count_mismatch_marks_failed():
    with _patch_service() as (_, openai_client):
        openai_client.embeddings.create.return_value = _response([])
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError, match="count"):
                embeddings.embed_processing_run(RUN_ID)
        assert update.call_args_list[-1].args[2] == "failed"


def test_dimension_mismatch_marks_failed():
    with _patch_service() as (_, openai_client):
        openai_client.embeddings.create.return_value = _response([[0.1], [0.2]])
        with pytest.raises(AppError, match="dimensions"):
            embeddings.embed_processing_run(RUN_ID)


def test_openai_failure_is_wrapped_without_api_key():
    with _patch_service(api_key="secret-key") as (_, openai_client):
        openai_client.embeddings.create.side_effect = RuntimeError("secret-key refused")
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError) as error:
                embeddings.embed_processing_run(RUN_ID)
        assert "secret-key" not in str(error.value)
        assert "secret-key" not in update.call_args_list[-1].args[3]


def test_failed_run_can_retry():
    with _patch_service(run={"embedding_status": "failed"}) as (_, openai_client):
        openai_client.embeddings.create.return_value = _response(
            [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
        with patch.object(embeddings, "delete_embeddings_for_run") as delete, patch.object(
            embeddings, "upsert_chunk_embeddings", return_value=2
        ):
            assert embeddings.embed_processing_run(RUN_ID) == 2
        delete.assert_called_once()


def test_embedded_run_is_terminal():
    with _patch_service(run={"embedding_status": "embedded"}) as (_, openai_client):
        with patch.object(embeddings, "update_run_embedding_status") as update:
            assert embeddings.embed_processing_run(RUN_ID) == 0
        openai_client.embeddings.create.assert_not_called()
        update.assert_not_called()


def test_empty_chunks_fail_cleanly():
    with _patch_service(chunks=[]) as (_, _):
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError, match="no chunks"):
                embeddings.embed_processing_run(RUN_ID)
        assert update.call_args_list[-1].args[2] == "failed"


def test_failure_error_is_truncated():
    with _patch_service() as (_, openai_client):
        openai_client.embeddings.create.side_effect = RuntimeError("x" * 2000)
        with patch.object(embeddings, "update_run_embedding_status") as update:
            with pytest.raises(AppError):
                embeddings.embed_processing_run(RUN_ID)
        assert len(update.call_args_list[-1].args[3]) == 1000


def test_repository_functions_are_used():
    with _patch_service() as (client, openai_client):
        openai_client.embeddings.create.return_value = _response(
            [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        )
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