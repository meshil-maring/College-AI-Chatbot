"""Validated citations, source labels and response usage."""

import re
from uuid import UUID
from app.schemas.ai.generation import RetrievedChunk, SourceReference
from app.schemas.ai.chat_response import ChatUsage, StructuredSource
from app.schemas.knowledge.retrieval import RetrievalResult


def _map_retrieval_result_to_chunk(result: RetrievalResult) -> RetrievedChunk:
    """Map Phase 3 RetrievalResult to Phase 4 RetrievedChunk.

    The contracts are structurally identical, so this is a direct field mapping.
    """
    return RetrievedChunk(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        document_version_id=result.document_version_id,
        text=result.text,
        similarity_score=result.similarity_score,
        metadata=result.metadata,
    )


def _extract_source_references(
    answer: str | None, retrieved_chunks: list[RetrievedChunk]
) -> list[SourceReference]:
    """Extract source references from the model's answer.

    The model is provided with chunks in format "[Retrieved chunk {chunk_id}]",
    so we look for explicit chunk ID references in the answer.

    An answer that does not identify a chunk has no source references. Retrieved
    context alone is not evidence that every chunk supports the answer.
    """
    source_references = []

    if not answer or not retrieved_chunks:
        return source_references

    chunk_id_pattern = (
        r"chunk[_\s]*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    )
    matches = re.findall(chunk_id_pattern, answer, re.IGNORECASE)
    referenced_ids = {UUID(m) for m in matches}

    for chunk in retrieved_chunks:
        if chunk.chunk_id in referenced_ids:
            source_references.append(
                SourceReference(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_version_id=chunk.document_version_id,
                    quote=chunk.text,
                    similarity_score=chunk.similarity_score,
                )
            )

    return source_references


def _build_chat_usage(metadata: dict | None) -> ChatUsage | None:
    """Map GenerationResult metadata["usage"] into a ChatUsage.

    prompt_tokens     -> input_tokens
    completion_tokens -> output_tokens

    Returns None when no usable usage data is present. Never fabricates counts.
    """
    if not isinstance(metadata, dict):
        return None
    usage = metadata.get("usage")
    if not isinstance(usage, dict) or not usage:
        return None
    return ChatUsage(
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
    )


def _build_structured_sources(
    source_references: list[SourceReference],
    retrieved_chunks: list[RetrievedChunk],
) -> list[StructuredSource]:
    """Derive frontend-friendly sources from validated source references ONLY.

    A retrieved chunk that was not cited in the answer never becomes a source.
    section comes from the matching RetrievedChunk.metadata["section"] when
    available; source_title is left None until enriched via provenance.
    """
    chunks_by_id = {chunk.chunk_id: chunk for chunk in retrieved_chunks}
    structured: list[StructuredSource] = []
    for reference in source_references:
        chunk = chunks_by_id.get(reference.chunk_id)
        structured.append(
            StructuredSource(
                chunk_id=reference.chunk_id,
                quote=reference.quote,
                relevance_score=reference.similarity_score,
                section=((chunk.metadata.get("section") or chunk.metadata.get("section_title"))
                    if chunk is not None else None),
            )
        )
    return structured


def _enrich_source_titles(client, structured_sources: list[StructuredSource]) -> None:
    """Resolve source_title from knowledge_sources.title via the provenance chain.

    Chain: knowledge_chunks -> document_processing_runs -> document_versions
           -> documents -> knowledge_sources

    Sources that cannot be fully resolved keep source_title=None. Titles are
    only ever taken from the database — never fabricated.

    Latency note: this runs synchronously before the response is returned
    because the frontend renders document attribution from it. It issues one
    embedded PostgREST foreign-key query (1 round trip) with a 5-query
    sequential fallback for backends without embedded resources. All lookups
    are batched with ``in_`` so the cost is constant in the number of
    sources (typically 0-2). Empty source lists skip the database entirely;
    failures leave titles None rather than failing the chat request.
    """
    if not structured_sources:
        return

    chunk_ids = [str(source.chunk_id) for source in structured_sources]

    def _lookup(table: str, column: str, key: str, ids: list[str]) -> dict:
        if not ids:
            return {}
        response = (
            client.table(table).select(f"{key}, {column}").in_(key, ids).execute()
        )
        data = response.data if isinstance(response.data, list) else []
        return {row[key]: row.get(column) for row in data if row.get(key) is not None}

    # Fast path: ONE embedded PostgREST foreign-key query resolves the full
    # provenance chain (knowledge_chunks -> document_processing_runs ->
    # document_versions -> documents -> knowledge_sources.title). Backends that
    # do not support embedded resources fall back to the sequential 5-query
    # chain below. Both paths are batched with ``in_`` so the cost is constant
    # in the number of cited sources (typically 0-2).
    embedded_select = (
        "chunk_id, document_processing_runs("
        "document_versions("
        "documents("
        "knowledge_sources(title)"
        ")"
        ")"
        ")"
    )
    try:
        embedded = (
            client.table("knowledge_chunks")
            .select(embedded_select)
            .in_("chunk_id", chunk_ids)
            .execute()
        )
        embedded_rows: list | None = (
            embedded.data if isinstance(getattr(embedded, "data", None), list) else None
        )
        if embedded_rows:

            def _first(value: object) -> dict:
                """Normalize embedded PostgREST members (dict or list) to a dict.

                PostgREST returns an object for to-one relationships and an
                array for to-many/to-one-with-array; both shapes occur across
                deployments, so every level of the chain is normalized.
                """
                if isinstance(value, list):
                    return value[0] if value else {}
                if isinstance(value, dict):
                    return value
                return {}

            titles: dict[str, str | None] = {}
            for row in embedded_rows:
                try:
                    run = _first(row.get("document_processing_runs"))
                    version = _first(run.get("document_versions"))
                    document = _first(version.get("documents"))
                    source_row = _first(document.get("knowledge_sources"))
                    title = (
                        source_row.get("title")
                        if isinstance(source_row, dict)
                        else None
                    )
                except (AttributeError, IndexError, TypeError):
                    title = None
                if row.get("chunk_id") is not None:
                    titles[str(row["chunk_id"])] = title
            if any(titles.values()):
                for source in structured_sources:
                    title = titles.get(str(source.chunk_id))
                    if title:
                        source.source_title = title
                return
    except Exception:
        # Embedded resources unsupported or unavailable; fall through to the
        # sequential chain. Failures never fail the chat request.
        pass

    # Step 1: knowledge_chunks -> processing_run_id
    chunk_map = _lookup("knowledge_chunks", "processing_run_id", "chunk_id", chunk_ids)
    # Step 2: document_processing_runs -> document_version_id
    run_map = _lookup(
        "document_processing_runs",
        "document_version_id",
        "processing_run_id",
        [value for value in chunk_map.values() if value],
    )
    # Step 3: document_versions -> document_id
    version_map = _lookup(
        "document_versions",
        "document_id",
        "document_version_id",
        [value for value in run_map.values() if value],
    )
    # Step 4: documents -> knowledge_source_id
    document_map = _lookup(
        "documents",
        "knowledge_source_id",
        "document_id",
        [value for value in version_map.values() if value],
    )
    # Step 5: knowledge_sources -> title
    source_map = _lookup(
        "knowledge_sources",
        "title",
        "knowledge_source_id",
        [value for value in document_map.values() if value],
    )

    for source in structured_sources:
        run_id = chunk_map.get(str(source.chunk_id))
        version_id = run_map.get(run_id) if run_id else None
        document_id = version_map.get(version_id) if version_id else None
        knowledge_source_id = document_map.get(document_id) if document_id else None
        title = source_map.get(knowledge_source_id) if knowledge_source_id else None
        if title:
            source.source_title = title
