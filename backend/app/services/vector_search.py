"""Application service for Phase 3.7 vector storage search."""

import math
from collections.abc import Sequence
from numbers import Real

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.vector_search import EMBEDDING_DIMENSIONS, search_similar_chunks


def search_chunks(
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
    """Search stored vectors without generating or filtering the query."""
    if query_embedding is None or isinstance(query_embedding, (str, bytes)):
        raise AppError(
            "A valid query embedding is required",
            status_code=422,
            code="INVALID_QUERY_EMBEDDING",
        )
    try:
        values = list(query_embedding)
    except TypeError as exc:
        raise AppError(
            "A valid query embedding is required",
            status_code=422,
            code="INVALID_QUERY_EMBEDDING",
        ) from exc
    if len(values) != EMBEDDING_DIMENSIONS or any(
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        for value in values
    ):
        raise AppError(
            "Query embedding must contain exactly 1536 finite numeric values",
            status_code=422,
            code="INVALID_QUERY_EMBEDDING",
        )

    if all(
        value is None
        for value in (
            institution_id,
            knowledge_source_id,
            document_id,
            document_version_id,
            processing_run_id,
        )
    ):
        raise AppError(
            "At least one retrieval scope is required",
            status_code=422,
            code="INVALID_VECTOR_SEARCH_REQUEST",
        )

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
            "Invalid vector search request",
            status_code=422,
            code="INVALID_VECTOR_SEARCH_REQUEST",
        ) from exc
    except Exception as exc:
        raise AppError(
            "Vector search failed",
            status_code=500,
            code="VECTOR_SEARCH_FAILED",
        ) from exc
