"""Orchestration for one request through the application chat boundary."""

import re
import time
from uuid import UUID

from app.db.supabase import get_admin_client
from app.repositories.ai_response import create_ai_response
from app.repositories.conversation import (
    create_conversation,
    get_conversation,
    update_conversation_timestamp,
)
from app.repositories.message import create_message, get_next_message_sequence
from app.repositories.message_citation import create_message_citations
from app.repositories.retrieval_operation import (
    create_retrieval_operation,
    create_retrieved_chunks,
)
from app.schemas.citation import (
    MessageCitationCreate,
    RetrievedChunkCreate,
    RetrievalOperationCreate,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.chat_response import ChatUsage, StructuredSource
from app.schemas.conversation import (
    AIResponseCreate,
    ConversationCreate,
    MessageCreate,
)
from app.schemas.generation import (
    AIRequest,
    RetrievalScope,
    RetrievedChunk,
    SourceReference,
)
from app.schemas.retrieval import RetrievalRequest, RetrievalResult
from app.schemas.session import SessionContext
from app.services.context import assemble_context
from app.services.generation import AIGenerationService
from app.services.generation_provider import GenerationProvider
from app.services.retrieval import retrieve


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

    chunk_id_pattern = r"chunk[_\s]*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
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


# ============================================================================
# Phase 4.4 — Structured chat response helpers
# ============================================================================


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
                section=(
                    chunk.metadata.get("section") if chunk is not None else None
                ),
            )
        )
    return structured


def _enrich_source_titles(client, structured_sources: list[StructuredSource]) -> None:
    """Resolve source_title from knowledge_sources.title via the provenance chain.

    Chain: knowledge_chunks -> document_processing_runs -> document_versions
           -> documents -> knowledge_sources

    Sources that cannot be fully resolved keep source_title=None. Titles are
    only ever taken from the database — never fabricated.
    """
    if not structured_sources:
        return

    def _lookup(table: str, column: str, key: str, ids: list[str]) -> dict:
        if not ids:
            return {}
        response = client.table(table).select(f"{key}, {column}").in_(key, ids).execute()
        data = response.data if isinstance(response.data, list) else []
        return {row[key]: row.get(column) for row in data if row.get(key) is not None}

    chunk_ids = [str(source.chunk_id) for source in structured_sources]

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


def process_chat_request(
    request: ChatRequest,
    session_context: SessionContext,
    provider: GenerationProvider,
    user_id: UUID | str,
) -> ChatResponse:
    """Resolve the validated request through context assembly, generation, and persistence."""
    if not isinstance(request, ChatRequest):
        raise TypeError("request must be a validated ChatRequest")
    if not isinstance(session_context, SessionContext):
        raise TypeError("session_context must be a validated SessionContext")

    client = get_admin_client()

    # Step 1: Resolve or create conversation
    conversation_id = request.conversation_id or request.session_id or session_context.session_id
    conversation = get_conversation(client, conversation_id)

    if conversation is None:
        # Create new conversation
        title = request.user_query[:60] if len(request.user_query) > 60 else request.user_query
        conversation = create_conversation(
            client,
            ConversationCreate(user_id=UUID(str(user_id)), title=title, status="active"),
            conversation_id=conversation_id,
        )
        conversation_id = UUID(conversation["conversation_id"])
    else:
        # Verify ownership
        conversation_id = UUID(conversation["conversation_id"])
        if str(conversation["user_id"]) != str(user_id):
            from app.core.errors import AppError
            raise AppError(
                "Conversation does not belong to the authenticated user",
                status_code=403,
                code="FORBIDDEN",
            )
        # Update conversation timestamp
        update_conversation_timestamp(client, conversation_id)

    # Step 2: Get next message sequence and persist user message
    user_sequence = get_next_message_sequence(client, conversation_id)
    create_message(
        client,
        MessageCreate(
            conversation_id=conversation_id,
            message_sequence=user_sequence,
            message_type="user",
            content_text=request.user_query,
        ),
    )

    # Step 3: If no chunks provided, invoke Phase 3 retrieval
    retrieved_chunks = request.retrieved_chunks
    if not retrieved_chunks:
        retrieval_request = RetrievalRequest(
            query=request.user_query,
            institution_id=request.institution_id,
            knowledge_source_id=request.knowledge_source_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            processing_run_id=request.processing_run_id,
            model_name=request.model_name,
        )
        retrieval_response = retrieve(retrieval_request)
        retrieved_chunks = [
            _map_retrieval_result_to_chunk(result)
            for result in retrieval_response.results
        ]

    # Step 4: Execute generation
    ai_request = AIRequest(
        user_query=request.user_query,
        retrieval_scope=RetrievalScope(
            institution_id=request.institution_id,
            knowledge_source_id=request.knowledge_source_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            processing_run_id=request.processing_run_id,
        ),
        retrieved_chunks=retrieved_chunks,
        model_name=request.model_name,
    )

    start_time = time.perf_counter()
    generation_result = AIGenerationService(provider).generate(assemble_context(ai_request))
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Step 4.5: Extract validated source references from the generated answer
    source_references = _extract_source_references(
        generation_result.answer, retrieved_chunks
    )

    # Step 5: Persist assistant message and AI response only when generation succeeded
    message_id = None
    if generation_result.answer is not None:
        assistant_sequence = get_next_message_sequence(client, conversation_id)
        assistant_message = create_message(
            client,
            MessageCreate(
                conversation_id=conversation_id,
                message_sequence=assistant_sequence,
                message_type="assistant",
                content_text=generation_result.answer,
            ),
        )
        message_id = UUID(assistant_message["message_id"])

        # Step 6: Persist AI response metadata
        input_tokens = None
        output_tokens = None
        if isinstance(generation_result.metadata, dict) and isinstance(
            generation_result.metadata.get("usage"), dict
        ):
            usage = generation_result.metadata["usage"]
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")

        ai_response = create_ai_response(
            client,
            AIResponseCreate(
                message_id=message_id,
                provider_name="openrouter",
                model_name=generation_result.model_used or "openai/gpt-4o-mini",
                validation_status="pending",
                input_token_count=input_tokens,
                output_token_count=output_tokens,
                latency_ms=latency_ms,
            ),
        )

        # Step 6.5 (Phase 4.3): Persist retrieval operation and retrieved chunks
        retrieval_operation = create_retrieval_operation(
            client,
            RetrievalOperationCreate(
                ai_response_id=UUID(ai_response["ai_response_id"]),
                query_text=request.user_query,
                status="completed",
                result_count=len(retrieved_chunks),
            ),
        )
        retrieval_operation_id = UUID(retrieval_operation["retrieval_operation_id"])

        create_retrieved_chunks(
            client,
            [
                RetrievedChunkCreate(
                    retrieval_operation_id=retrieval_operation_id,
                    chunk_id=chunk.chunk_id,
                    retrieval_rank=rank,
                    relevance_score=chunk.similarity_score,
                    selected_for_context=True,
                )
                for rank, chunk in enumerate(retrieved_chunks, start=1)
            ],
        )

        # Step 6.6 (Phase 4.3): Persist message citations for validated references
        create_message_citations(
            client,
            [
                MessageCitationCreate(
                    message_id=message_id,
                    retrieval_operation_id=retrieval_operation_id,
                    chunk_id=reference.chunk_id,
                    display_order=order,
                )
                for order, reference in enumerate(source_references, start=1)
            ],
        )

    # Step 7 (Phase 4.4): Build structured sources and usage for the response
    sources = _build_structured_sources(source_references, retrieved_chunks)
    _enrich_source_titles(client, sources)
    chat_usage = _build_chat_usage(generation_result.metadata)

    # Step 8: Return response with conversation_id, message_id, and session_id
    return ChatResponse(
        session_id=session_context.session_id,
        conversation_id=conversation_id,
        message_id=message_id,
        answer=generation_result.answer,
        source_references=source_references,
        status=generation_result.status,
        model_used=generation_result.model_used,
        metadata=generation_result.metadata,
        sources=sources,
        usage=chat_usage,
    )