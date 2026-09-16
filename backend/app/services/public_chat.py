"""Phase 6.13 - Public (unauthenticated) chat endpoint service.

Mirrors app.services.chat.process_chat_request so that public conversations
reuse the same chat boundary, turn/conversation ownership model, bounded
history, query rewriting, retrieval, generation, and citation pipeline -
EXCEPT:

1. user_id is always PUBLIC_USER_ID (a constant, never derived from a JWT).
2. Personalization is never loaded (no current_user -> no student context).
3. institution_id is accepted for forward-compatibility but does not
   participate in any tenant-scoped authorization check.
"""

from __future__ import annotations

import re
import threading
import time
from uuid import UUID

from app.config import settings
from app.core.errors import AppError
from app.core.security import PUBLIC_USER_ID
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
    ConversationTurn,
    RetrievalScope,
    RetrievedChunk,
    SourceReference,
)
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.context import assemble_context
from app.services.conversation_history import get_conversation_messages
from app.services.generation import AIGenerationService
from app.services.generation_provider import GenerationProvider
from app.services.query_rewriting import rewrite_query
from app.services.retrieval import retrieve

__all__ = ["process_chat_request"]

# ============================================================================
# Source reference extraction (mirrors chat.py)
# ============================================================================

_CHUNK_REF_RE = re.compile(
    r"\[Retrieved chunk ([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\]",
    re.IGNORECASE,
)


def _extract_source_references(
    answer: str | None,
    retrieved_chunks: list[RetrievedChunk],
) -> list[SourceReference]:
    """Extract source references from answer text using explicit chunk refs."""
    if not answer or not retrieved_chunks:
        return []
    referenced_ids = {
        UUID(m.group(1)) for m in _CHUNK_REF_RE.finditer(answer)
    }
    references = []
    for chunk in retrieved_chunks:
        if chunk.chunk_id in referenced_ids:
            references.append(
                SourceReference(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_version_id=chunk.document_version_id,
                    quote=chunk.text,
                    similarity_score=chunk.similarity_score,
                )
            )
    return references


# ============================================================================
# Structured sources / usage (mirrors chat.py)
# ============================================================================

def _build_structured_sources(
    source_references: list[SourceReference],
    retrieved_chunks: list[RetrievedChunk],
) -> list[StructuredSource]:
    """Build frontend-friendly StructuredSource list from source references."""
    chunks_by_id = {c.chunk_id: c for c in retrieved_chunks}
    sources: list[StructuredSource] = []
    for ref in source_references:
        chunk = chunks_by_id.get(ref.chunk_id)
        sources.append(
            StructuredSource(
                chunk_id=ref.chunk_id,
                quote=ref.quote,
                relevance_score=ref.similarity_score,
                section=(
                    chunk.metadata.get("section")
                    if chunk and chunk.metadata
                    else None
                ),
            )
        )
    return sources


def _build_chat_usage(metadata: dict | None) -> ChatUsage | None:
    """Map generation metadata["usage"] into a ChatUsage."""
    if not isinstance(metadata, dict):
        return None
    usage = metadata.get("usage")
    if not isinstance(usage, dict):
        return None
    return ChatUsage(
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
    )

# ============================================================================
# Background persistence (mirrors chat.py)
# ============================================================================

_background_errors: list[str] = []
_BACKGROUND_ERROR_LIMIT = 20


def _persist_in_background(
    conversation_id: UUID,
    message_id: UUID,
    retrieval_query: str,
    retrieved_chunks: list[RetrievedChunk],
    source_references: list[SourceReference],
    generation_result,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int,
) -> None:
    """Persist AI response, retrieval operation, chunks, and citations in a
    background thread. The worker resolves its own admin client inside the
    thread instead of reusing the request thread's client."""
    try:
        client = get_admin_client()
        ai_response = create_ai_response(
            client,
            AIResponseCreate(
                message_id=message_id,
                provider_name="openrouter",
                model_name=generation_result.model_used or "unknown",
                validation_status="pending",
                input_token_count=input_tokens,
                output_token_count=output_tokens,
                latency_ms=latency_ms,
            ),
        )
        ai_response_id = UUID(ai_response["ai_response_id"])

        update_conversation_timestamp(client, conversation_id)

        retrieval_op = create_retrieval_operation(
            client,
            RetrievalOperationCreate(
                ai_response_id=ai_response_id,
                query_text=retrieval_query,
                status="completed",
                result_count=len(retrieved_chunks),
            ),
        )
        retrieval_op_id = UUID(retrieval_op["retrieval_operation_id"])

        create_retrieved_chunks(
            client,
            [
                RetrievedChunkCreate(
                    retrieval_operation_id=retrieval_op_id,
                    chunk_id=chunk.chunk_id,
                    retrieval_rank=rank,
                    relevance_score=chunk.similarity_score,
                    selected_for_context=True,
                )
                for rank, chunk in enumerate(retrieved_chunks, start=1)
            ],
        )

        create_message_citations(
            client,
            [
                MessageCitationCreate(
                    message_id=message_id,
                    retrieval_operation_id=retrieval_op_id,
                    chunk_id=ref.chunk_id,
                    display_order=order,
                )
                for order, ref in enumerate(source_references, start=1)
            ],
        )
    except Exception as exc:
        import logging

        logging.error("Background persistence failed: %s", exc, exc_info=True)
        _background_errors.append(f"{type(exc).__name__}: {exc}")
        while len(_background_errors) > _BACKGROUND_ERROR_LIMIT:
            _background_errors.pop(0)


def _start_background_persistence(
    conversation_id: UUID,
    message_id: UUID,
    retrieval_query: str,
    retrieved_chunks: list[RetrievedChunk],
    source_references: list[SourceReference],
    generation_result,
    input_tokens: int | None,
    output_tokens: int | None,
    latency_ms: int,
) -> None:
    """Kick off persistence on a daemon thread so the response is not blocked."""
    thread = threading.Thread(
        target=_persist_in_background,
        args=(
            conversation_id,
            message_id,
            retrieval_query,
            retrieved_chunks,
            source_references,
            generation_result,
            input_tokens,
            output_tokens,
            latency_ms,
        ),
        daemon=True,
    )
    thread.start()

# ============================================================================
# Main entry point
# ============================================================================


def process_chat_request(
    request: ChatRequest,
    context: SessionContext,
    provider: GenerationProvider,
) -> ChatResponse:
    """Public-path equivalent of app.services.chat.process_chat_request.

    Ownership model is identical to the authenticated path - same
    ConversationCreate shape, same background persistence, same bounded
    turn history - but every public conversation is owned by PUBLIC_USER_ID
    so the public endpoint cannot read or write into any authenticated
    user's conversation or message rows.
    """
    if not isinstance(request, ChatRequest):
        raise TypeError("request must be a ChatRequest")
    if not isinstance(context, SessionContext):
        raise TypeError("context must be a SessionContext")

    timings: dict = {}
    request_start = time.perf_counter()
    client = get_admin_client()

    # Step 1: Resolve or create conversation (owned by PUBLIC_USER_ID)
    conversation_start = time.perf_counter()
    user_id = PUBLIC_USER_ID
    conversation_id = (
        request.conversation_id
        or request.session_id
        or context.session_id
    )
    conversation = get_conversation(client, conversation_id)

    if conversation is None:
        title = (
            request.user_query[:60]
            if len(request.user_query) > 60
            else request.user_query
        )
        conversation = create_conversation(
            client,
            ConversationCreate(
                user_id=user_id,
                title=title,
                status="active",
            ),
            conversation_id=conversation_id,
        )
        conversation_id = UUID(conversation["conversation_id"])
    else:
        conversation_id = UUID(conversation["conversation_id"])
    timings["conversation_resolution_ms"] = int(
        (time.perf_counter() - conversation_start) * 1000
    )

    # Step 1.5: Bounded conversation history (copy of chat.py logic)
    history_start = time.perf_counter()
    message_summaries = get_conversation_messages(
        conversation_id,
        user_id,
        conversation=conversation,
    )
    timings["history_latency_ms"] = int(
        (time.perf_counter() - history_start) * 1000
    )
    turns = [
        ConversationTurn(role=s.role, content=s.content)
        for s in message_summaries
    ]
    conversation_history = turns[-20:] if len(turns) > 20 else turns

    # Step 2: Persist user message
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

    # Step 2.5: Query rewriting - only rewrite if not self-contained
    rewrite_start = time.perf_counter()
    _self_contained = (
        len(request.user_query) >= 12
        and not re.search(
            r"\b(this|that|these|those|it|he|she|they|we|him|her|them|"
            r"his|its|their|our|you|your)\b",
            request.user_query,
            re.IGNORECASE,
        )
        or conversation_history
    )
    if _self_contained:
        retrieval_query = request.user_query
    else:
        rewritten = rewrite_query(
            request.user_query, conversation_history, provider
        ) or request.user_query
        retrieval_query = rewritten
    timings["query_rewrite_latency_ms"] = int(
        (time.perf_counter() - rewrite_start) * 1000
    )

    # Step 3: Retrieval (skip if chunks already provided)
    retrieved_chunks: list[RetrievedChunk] = list(request.retrieved_chunks)
    if not retrieved_chunks:
        retrieval_timings: dict = {}
        retrieval_request = RetrievalRequest(
            query=retrieval_query,
            top_k=settings.retrieval_top_k,
            institution_id=request.institution_id,
            knowledge_source_id=request.knowledge_source_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            processing_run_id=request.processing_run_id,
            model_name=request.model_name,
        )
        retrieval_response = retrieve(
            retrieval_request, timings=retrieval_timings
        )
        timings["embedding_latency_ms"] = retrieval_timings.get(
            "embedding_latency_ms", 0
        )
        timings["retrieval_latency_ms"] = retrieval_timings.get(
            "vector_search_latency_ms", 0
        )
        retrieved_chunks = [
            RetrievedChunk(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                document_version_id=r.document_version_id,
                text=r.text,
                similarity_score=r.similarity_score,
                metadata=r.metadata,
            )
            for r in retrieval_response.results
        ]
    else:
        timings["embedding_latency_ms"] = 0
        timings["retrieval_latency_ms"] = 0

    # Step 4: Build AIRequest, assemble context, generate
    context_start = time.perf_counter()
    ai_request = AIRequest(
        user_query=request.user_query,
        retrieval_query=(
            retrieval_query
            if retrieval_query != request.user_query
            else None
        ),
        retrieval_scope=RetrievalScope(
            institution_id=request.institution_id,
            knowledge_source_id=request.knowledge_source_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            processing_run_id=request.processing_run_id,
        ),
        retrieved_chunks=retrieved_chunks,
        model_name=request.model_name,
        conversation_history=conversation_history,
    )
    assembled_context = assemble_context(ai_request)
    timings["context_build_latency_ms"] = int(
        (time.perf_counter() - context_start) * 1000
    )

    stage_start = time.perf_counter()
    generation_result = AIGenerationService(provider).generate(
        assembled_context
    )
    latency_ms = int((time.perf_counter() - stage_start) * 1000)
    timings["llm_request_latency_ms"] = latency_ms
    timings["llm_ttft_ms"] = latency_ms
    timings["llm_generation_latency_ms"] = latency_ms

    # Step 4.5: Extract source references from answer
    parse_start = time.perf_counter()
    source_references = _extract_source_references(
        generation_result.answer, retrieved_chunks
    )
    timings["response_parse_latency_ms"] = int(
        (time.perf_counter() - parse_start) * 1000
    )

    # Step 5: Persist assistant message + AI response
    persist_start = time.perf_counter()
    message_id: UUID | None = None
    if generation_result.answer is not None:
        assistant_sequence = get_next_message_sequence(
            client, conversation_id
        )
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

        input_tokens: int | None = None
        output_tokens: int | None = None
        if isinstance(generation_result.metadata, dict) and isinstance(
            generation_result.metadata.get("usage"), dict
        ):
            usage = generation_result.metadata["usage"]
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")

        _start_background_persistence(
            conversation_id=conversation_id,
            message_id=message_id,
            retrieval_query=retrieval_query,
            retrieved_chunks=retrieved_chunks,
            source_references=source_references,
            generation_result=generation_result,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    timings["persistence_latency_ms"] = int(
        (time.perf_counter() - persist_start) * 1000
    )

    # Step 6: Build structured sources and usage
    sources = _build_structured_sources(
        source_references, retrieved_chunks
    )
    chat_usage = _build_chat_usage(generation_result.metadata)

    timings["total_latency_ms"] = int(
        (time.perf_counter() - request_start) * 1000
    )

    # Step 7: Return ChatResponse
    return ChatResponse(
        session_id=context.session_id,
        conversation_id=conversation_id,
        message_id=message_id,
        answer=generation_result.answer,
        source_references=source_references,
        status=generation_result.status,
        model_used=generation_result.model_used,
        metadata=(
            {**generation_result.metadata, "diagnostics": timings}
            if settings.debug
            else generation_result.metadata
        ),
        sources=sources,
        usage=chat_usage,
    )
