"""Application service for scoped vector retrieval."""

import math
import time
from collections.abc import Sequence
from numbers import Real

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.vector_search import (
    EMBEDDING_DIMENSIONS,
    search_similar_chunks,
)
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
from app.services.embeddings import embed_query
from app.services.vector_search import search_chunks


def retrieve(
    request: RetrievalRequest, timings: dict | None = None
) -> RetrievalResponse:
    """Execute the internal text-to-vector retrieval pipeline.

    When ``timings`` is a dict, per-stage durations (milliseconds) are recorded
    into it for development latency diagnostics; retrieval behavior is
    completely unchanged.
    """
    start = time.perf_counter() if timings is not None else None
    try:
        query_embedding = embed_query(request.query)
    except AppError:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise AppError(
            "Query embedding failed",
            status_code=500,
            code="EMBEDDING_FAILED",
        ) from exc
    if timings is not None:
        timings["embedding_latency_ms"] = int((time.perf_counter() - start) * 1000)

    start = time.perf_counter() if timings is not None else None
    try:
        rows = search_chunks(
            query_embedding,
            top_k=request.top_k,
            institution_id=_as_string(request.institution_id),
            knowledge_source_id=_as_string(request.knowledge_source_id),
            document_id=_as_string(request.document_id),
            document_version_id=_as_string(request.document_version_id),
            processing_run_id=_as_string(request.processing_run_id),
            model_name=request.model_name or settings.embedding_model,
        )
    except AppError as exc:
        raise AppError(
            "Retrieval failed",
            status_code=exc.status_code,
            code="RETRIEVAL_FAILED",
        ) from exc
    if timings is not None:
        timings["vector_search_latency_ms"] = int((time.perf_counter() - start) * 1000)

    return RetrievalResponse(results=[_map_result(row) for row in rows])


def _as_string(value: object) -> str | None:
    return str(value) if value is not None else None


def _map_result(row: dict) -> RetrievalResult:
    metadata = {
        key: row[key]
        for key in ("processing_run_id", "chunk_sequence", "section_title", "model_name")
        if key in row and row[key] is not None
    }
    return RetrievalResult(
        chunk_id=row["chunk_id"],
        document_id=row.get("document_id"),
        document_version_id=row.get("document_version_id"),
        text=row["content_text"],
        similarity_score=1 - row["distance"],
        metadata=metadata,
    )


def _validate_query_embedding(query_embedding: Sequence[float] | None) -> None:
    if query_embedding is None or isinstance(query_embedding, (str, bytes)):
        raise AppError(
            "A valid query embedding is required",
            status_code=422,
            code="INVALID_QUERY_EMBEDDING",
        )
    if len(query_embedding) != EMBEDDING_DIMENSIONS:
        raise AppError(
            "Query embedding must contain exactly 1536 values",
            status_code=422,
            code="INVALID_QUERY_EMBEDDING",
        )
    if any(
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        for value in query_embedding
    ):
        raise AppError(
            "Query embedding values must be numeric",
            status_code=422,
            code="INVALID_QUERY_EMBEDDING",
        )


def retrieve_chunks(
    query_embedding: Sequence[float] | None,
    *,
    top_k: int = 10,
    institution_id: str | None = None,
    knowledge_source_id: str | None = None,
    document_id: str | None = None,
    document_version_id: str | None = None,
    processing_run_id: str | None = None,
    model_name: str = settings.embedding_model,
) -> list[dict]:
    """Retrieve nearest chunks for an explicitly scoped query embedding."""
    _validate_query_embedding(query_embedding)

    try:
        return search_similar_chunks(
            get_admin_client(),
            query_embedding,
            top_k=top_k,
            institution_id=institution_id,
            knowledge_source_id=knowledge_source_id,
            document_id=document_id,
            document_version_id=document_version_id,
            processing_run_id=processing_run_id,
            model_name=model_name,
        )
    except ValueError as exc:
        raise AppError(
            "Invalid retrieval request",
            status_code=422,
            code="INVALID_RETRIEVAL_REQUEST",
        ) from exc
    except Exception as exc:
        raise AppError(
            "Retrieval failed",
            status_code=500,
            code="RETRIEVAL_FAILED",
        ) from exc