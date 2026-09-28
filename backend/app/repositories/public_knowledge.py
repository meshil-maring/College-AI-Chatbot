"""Data access dedicated to the public-knowledge authorization boundary."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from supabase import Client

from app.repositories.vector_search import _validate_query_embedding


SOURCE_COLUMNS = (
    "knowledge_source_id, institution_id, source_type, title, visibility, "
    "lifecycle_status, effective_from, effective_until"
)

PROVENANCE_PROJECTION = (
    "processing_run_id, status, embedding_status, completed_at, "
    "document_versions(document_version_id, document_id, lifecycle_status, "
    "effective_from, effective_until, documents(document_id, knowledge_source_id, "
    "knowledge_sources(knowledge_source_id, institution_id, source_type, title, "
    "visibility, lifecycle_status, effective_from, effective_until)))"
)


def get_source(client: Client, knowledge_source_id: UUID | str) -> dict | None:
    response = (
        client.table("knowledge_sources")
        .select(SOURCE_COLUMNS)
        .eq("knowledge_source_id", str(knowledge_source_id))
        .maybe_single()
        .execute()
    )
    return response.data if response and response.data else None


def list_public_source_candidates(
    client: Client, institution_id: UUID | str
) -> list[dict]:
    response = (
        client.table("knowledge_sources")
        .select(SOURCE_COLUMNS)
        .eq("institution_id", str(institution_id))
        .eq("visibility", "public")
        .eq("lifecycle_status", "published")
        .execute()
    )
    return response.data if response and isinstance(response.data, list) else []


def get_chunk_provenance(
    client: Client, chunk_ids: set[str]
) -> list[dict]:
    if not chunk_ids:
        return []
    response = (
        client.table("knowledge_chunks")
        .select(
            "chunk_id, processing_run_id, "
            f"document_processing_runs({PROVENANCE_PROJECTION})"
        )
        .in_("chunk_id", sorted(chunk_ids))
        .execute()
    )
    return response.data if response and isinstance(response.data, list) else []


def search_public_chunks(
    client: Client,
    query_embedding: Sequence[float],
    *,
    top_k: int,
    institution_id: UUID | str,
    knowledge_source_id: UUID | str | None = None,
    model_name: str,
) -> list[dict]:
    """Search only rows satisfying the complete SQL public predicate."""
    _validate_query_embedding(query_embedding)
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if institution_id is None:
        raise ValueError("institution_id is required for public retrieval")
    if not isinstance(model_name, str) or not model_name:
        raise ValueError("model_name is required")
    response = client.rpc(
        "search_public_knowledge_chunks",
        {
            "query_embedding": list(query_embedding),
            "match_count": top_k,
            "filter_institution_id": str(institution_id),
            "filter_knowledge_source_id": (
                str(knowledge_source_id) if knowledge_source_id is not None else None
            ),
            "filter_model_name": model_name,
        },
    ).execute()
    return response.data or []
