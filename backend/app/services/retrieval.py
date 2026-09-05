"""Application service for scoped vector retrieval."""

import math
from collections.abc import Sequence
from numbers import Real

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.vector_search import (
    EMBEDDING_DIMENSIONS,
    search_similar_chunks,
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