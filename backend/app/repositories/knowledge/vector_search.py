"""Repository operations for vector similarity search."""

import math
from collections.abc import Sequence
from numbers import Real

from supabase import Client


EMBEDDING_DIMENSIONS = 1536
DEFAULT_MODEL_NAME = "qwen/qwen3-embedding-8b"


def search_similar_chunks(
    client: Client,
    query_embedding: Sequence[float],
    *,
    top_k: int = 10,
    institution_id: str | None = None,
    knowledge_source_id: str | None = None,
    document_id: str | None = None,
    document_version_id: str | None = None,
    processing_run_id: str | None = None,
    model_name: str | None = None,
) -> list[dict]:
    """Return nearest stored chunks ordered by pgvector cosine distance.

    The query vector is supplied by the caller and is passed to PostgreSQL
    unchanged. At least one metadata scope is required so this repository
    cannot issue an unscoped search.
    """
    _validate_query_embedding(query_embedding)
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if not isinstance(model_name, str) or not model_name:
        raise ValueError("model_name is required")
    filters = {
        "filter_institution_id": institution_id,
        "filter_knowledge_source_id": knowledge_source_id,
        "filter_document_id": document_id,
        "filter_document_version_id": document_version_id,
        "filter_processing_run_id": processing_run_id,
        "filter_model_name": model_name,
    }
    if all(
        filters[key] is None
        for key in (
            "filter_institution_id",
            "filter_knowledge_source_id",
            "filter_document_id",
            "filter_document_version_id",
            "filter_processing_run_id",
        )
    ):
        raise ValueError("at least one search filter is required")

    response = client.rpc(
        "search_similar_chunks",
        {
            "query_embedding": list(query_embedding),
            "match_count": top_k,
            **filters,
        },
    ).execute()
    return response.data or []


def _validate_query_embedding(query_embedding: Sequence[float]) -> None:
    if query_embedding is None or isinstance(query_embedding, (str, bytes)):
        raise ValueError("query_embedding must be a 1536-dimensional sequence")
    try:
        values = list(query_embedding)
    except TypeError as exc:
        raise ValueError(
            "query_embedding must be a 1536-dimensional sequence"
        ) from exc
    if len(values) != EMBEDDING_DIMENSIONS:
        raise ValueError("query_embedding must be a 1536-dimensional sequence")
    if any(
        isinstance(value, bool)
        or not isinstance(value, Real)
        or not math.isfinite(value)
        for value in values
    ):
        raise ValueError("query_embedding values must be finite numbers")