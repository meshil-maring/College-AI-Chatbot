import logging
import math
import threading
import time
from collections import OrderedDict
from collections.abc import Iterable
from numbers import Real

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.embeddings import (
    delete_embeddings_for_run,
    get_chunks_for_run,
    update_run_embedding_status,
    upsert_chunk_embeddings,
)
from app.repositories.ingestion import get_processing_run_with_version
from app.services.embedding_provider import EmbeddingProvider, get_embedding_provider

# ---------------------------------------------------------------------------
# Query-embedding cache (development-measured optimization).
#
# Measured query embedding latency against OpenRouter's configured embedding
# model ranges from ~2s to ~9s. Repeating the exact same query (retry,
# refresh, common short questions) re-generates an identical vector, so a
# small short-lived cache removes that round trip entirely. Safety properties:
#
#   * keyed by (embedding_model, embedding_dimensions, query) so vectors are
#     never reused across incompatible embedding configurations,
#   * short TTL so newly ingested/re-embedded knowledge is reflected quickly,
#   * bounded size (LRU eviction),
#   * only the DEFAULT configured provider path is cached; callers that pass
#     an explicit provider (document ingestion, tests) bypass the cache, so
#     document embeddings are never cached here.
# ---------------------------------------------------------------------------
_QUERY_EMBEDDING_CACHE: "OrderedDict[tuple, tuple[float, list[float]]]" = OrderedDict()
_QUERY_EMBEDDING_LOCK = threading.Lock()
_QUERY_EMBEDDING_TTL_SECONDS = 600.0
_QUERY_EMBEDDING_MAX_ENTRIES = 128


def _cache_get(key: tuple) -> list[float] | None:
    with _QUERY_EMBEDDING_LOCK:
        entry = _QUERY_EMBEDDING_CACHE.get(key)
        if entry is None:
            return None
    created_at, vector = entry
    if time.monotonic() - created_at >= _QUERY_EMBEDDING_TTL_SECONDS:
        with _QUERY_EMBEDDING_LOCK:
            _QUERY_EMBEDDING_CACHE.pop(key, None)
        return None
    with _QUERY_EMBEDDING_LOCK:
        _QUERY_EMBEDDING_CACHE.move_to_end(key)
    return vector


def _cache_put(key: tuple, vector: list[float]) -> None:
    with _QUERY_EMBEDDING_LOCK:
        _QUERY_EMBEDDING_CACHE[key] = (time.monotonic(), vector)
        _QUERY_EMBEDDING_CACHE.move_to_end(key)
        while len(_QUERY_EMBEDDING_CACHE) > _QUERY_EMBEDDING_MAX_ENTRIES:
            _QUERY_EMBEDDING_CACHE.popitem(last=False)


def embed_query(
    query: str,
    provider: EmbeddingProvider | None = None,
) -> list[float]:
    """Generate and validate one query embedding through the configured provider."""
    if provider is None:
        cache_key = (settings.embedding_model, settings.embedding_dimensions, query)
        cached = _cache_get(cache_key)
        if cached is not None:
            return list(cached)

    embedding_provider = provider or get_embedding_provider()
    vectors = embedding_provider.embed([query])
    if len(vectors) != 1:
        logging.error(
            "embed_query unexpected result count: %d (expected 1); provider=%s",
            len(vectors),
            type(embedding_provider).__name__,
        )
        raise ValueError(
            "Embedding provider returned an unexpected result count"
        )

    vector = vectors[0]
    if len(vector) != settings.embedding_dimensions:
        raise ValueError(
            "Embedding provider returned an embedding with an unexpected number of dimensions"
        )
    if any(
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        for value in vector
    ):
        raise ValueError("Embedding provider returned non-numeric embedding values")

    if provider is None:
        _cache_put(cache_key, vector)
    return vector


def _safe_error_message(error: Exception) -> str:
    message = str(error)
    if settings.openrouter_api_key:
        message = message.replace(settings.openrouter_api_key, "[redacted]")
    return message[:1000]


def _batches(items: list[dict], size: int) -> Iterable[list[dict]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def embed_processing_run(
    processing_run_id: str,
    provider: EmbeddingProvider | None = None,
) -> int:
    """Generate and persist embeddings for all chunks in a processing run."""
    db = get_admin_client()
    run = get_processing_run_with_version(db, processing_run_id)
    if run is None:
        raise AppError("Processing run not found", status_code=404, code="RUN_NOT_FOUND")

    embedding_status = run.get("embedding_status")
    if embedding_status == "embedded":
        return 0
    if embedding_status not in (None, "failed"):
        raise AppError(
            f"Run is not available for embedding (current: {embedding_status})",
            status_code=409,
            code="RUN_NOT_EMBEDDABLE",
        )

    update_run_embedding_status(db, processing_run_id, "processing")
    try:
        chunks = get_chunks_for_run(db, processing_run_id)
        if not chunks:
            raise AppError(
                "Processing run has no chunks to embed",
                status_code=422,
                code="NO_CHUNKS",
            )

        delete_embeddings_for_run(db, processing_run_id, settings.embedding_model)
        embedding_provider = provider or get_embedding_provider()
        total = 0

        if settings.embedding_batch_size <= 0:
            raise ValueError("Embedding batch size must be greater than zero")

        for batch in _batches(chunks, settings.embedding_batch_size):
            vectors = embedding_provider.embed([chunk["content_text"] for chunk in batch])
            if len(vectors) != len(batch):
                raise ValueError(
                    "Embedding provider returned an embedding count that does not match the chunk count"
                )
            for vector in vectors:
                if len(vector) != settings.embedding_dimensions:
                    raise ValueError(
                        "Embedding provider returned an embedding with an unexpected number of dimensions"
                    )

            total += upsert_chunk_embeddings(
                db,
                settings.embedding_model,
                settings.embedding_dimensions,
                [
                    {"chunk_id": chunk["chunk_id"], "embedding": vector}
                    for chunk, vector in zip(batch, vectors)
                ],
            )

        update_run_embedding_status(db, processing_run_id, "embedded")
        return total
    except AppError as exc:
        error_message = _safe_error_message(exc)
        update_run_embedding_status(db, processing_run_id, "failed", error_message)
        raise AppError(error_message, status_code=exc.status_code, code=exc.code) from exc
    except Exception as exc:
        error_message = _safe_error_message(exc)
        update_run_embedding_status(db, processing_run_id, "failed", error_message)
        raise AppError(error_message, status_code=500, code="EMBEDDING_FAILED") from exc