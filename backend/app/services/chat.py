"""Orchestration for one request through the application chat boundary."""

import re
import threading
import time
from uuid import UUID

from app.config import settings
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
from app.schemas.retrieval import RetrievalRequest, RetrievalResult
from app.schemas.session import SessionContext
from app.services.context import assemble_context
from app.services.conversation_history import get_conversation_messages
from app.services.generation import AIGenerationService
from app.services.generation_provider import GenerationProvider
from app.services.query_rewriting import rewrite_query
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


def _persist_in_background(conversation_id, message_id, retrieval_query, retrieved_chunks, source_references, generation_result, input_tokens, output_tokens, latency_ms):
    """Persist AI response, retrieval operation, chunks, and citations in a background thread.

    The worker resolves its own admin client inside the thread instead of
    reusing the request thread's client, so pooled connections are never shared
    unsafely across threads. Failures are logged and retained (bounded) for
    development diagnostics; they never alter the response already computed.
    """
    try:
        thread_client = get_admin_client()
        ai_response = create_ai_response(thread_client, AIResponseCreate(message_id=message_id, provider_name="openrouter", model_name=generation_result.model_used or "openai/gpt-4o-mini", validation_status="pending", input_token_count=input_tokens, output_token_count=output_tokens, latency_ms=latency_ms))
        update_conversation_timestamp(thread_client, conversation_id)
        retrieval_operation = create_retrieval_operation(thread_client, RetrievalOperationCreate(ai_response_id=UUID(ai_response["ai_response_id"]), query_text=retrieval_query, status="completed", result_count=len(retrieved_chunks)))
        retrieval_operation_id = UUID(retrieval_operation["retrieval_operation_id"])
        create_retrieved_chunks(thread_client, [RetrievedChunkCreate(retrieval_operation_id=retrieval_operation_id, chunk_id=chunk.chunk_id, retrieval_rank=rank, relevance_score=chunk.similarity_score, selected_for_context=True) for rank, chunk in enumerate(retrieved_chunks, start=1)])
        create_message_citations(thread_client, [MessageCitationCreate(message_id=message_id, retrieval_operation_id=retrieval_operation_id, chunk_id=reference.chunk_id, display_order=order) for order, reference in enumerate(source_references, start=1)])
    except Exception as exc:
        import logging
        logging.error("Background persistence failed", exc_info=True)
        try:
            _background_errors.append(f"{type(exc).__name__}: {exc}")
            while len(_background_errors) > _BACKGROUND_ERROR_LIMIT:
                _background_errors.pop(0)
        except Exception:
            pass

# Bounded record of recent background-persistence failures for development
# diagnostics. Never user-facing; deliberately not part of the response.
_background_errors: list = []
_BACKGROUND_ERROR_LIMIT = 20

def _start_background_persistence(conversation_id, message_id, retrieval_query, retrieved_chunks, source_references, generation_result, input_tokens, output_tokens, latency_ms):
    """Kick off persistence on a daemon thread so the response is not blocked.

    No client is passed: the worker resolves its own admin client in-thread.
    """
    thread = threading.Thread(target=_persist_in_background, args=(conversation_id, message_id, retrieval_query, retrieved_chunks, source_references, generation_result, input_tokens, output_tokens, latency_ms), daemon=True)
    thread.start()


def _attach_observability_diagnostics(*, timings: dict, request, retrieval_query: str, retrieved_chunks, generation_result, prompt_text: str = "") -> None:
    """Attach debug-only latency/observability diagnostics (never user-facing).

    Students never see this dictionary: ``process_chat_request`` only merges
    ``timings`` into response metadata when ``settings.debug`` is enabled.
    """
    timings["original_query"] = request.user_query
    timings["rewritten_query"] = retrieval_query if retrieval_query != request.user_query else None
    timings["retrieved_chunk_count"] = len(retrieved_chunks)
    timings["retrieved_chunk_ids"] = [str(chunk.chunk_id) for chunk in retrieved_chunks]
    timings["retrieved_scores"] = [chunk.similarity_score for chunk in retrieved_chunks]
    try:
        from app.services.generation_provider import estimate_prompt_tokens

        timings["final_context_token_count"] = estimate_prompt_tokens(prompt_text)
    except Exception:
        timings["final_context_token_count"] = 0
    usage = getattr(generation_result, "metadata", {}).get("usage", {}) if isinstance(
        getattr(generation_result, "metadata", {}), dict
    ) else {}
    timings["final_input_token_count"] = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    timings["output_token_count"] = usage.get("completion_tokens") if isinstance(usage, dict) else None


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
        response = client.table(table).select(f"{key}, {column}").in_(key, ids).execute()
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
                    title = source_row.get("title") if isinstance(source_row, dict) else None
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


def _bounded_conversation_history(
    turns: list[ConversationTurn], max_messages: int
) -> list[ConversationTurn]:
    """Select the most recent bounded window of conversation turns.

    Keeps recent messages (never the oldest), caps total message count at
    ``max_messages``, and — when the budget forces trimming — starts the window
    at a user turn where practical so a user/assistant exchange is not split
    unnecessarily. Ordering stays chronological (message_sequence ASC).

    Fallback behavior: if ``max_messages <= 0`` or no messages exist, an empty
    list is returned (first-message / no-history behavior).
    """
    if max_messages <= 0 or not turns:
        return []
    if len(turns) <= max_messages:
        return turns
    window = turns[-max_messages:]
    if window and window[0].role == "assistant":
        # Trimming to the most recent max_messages would start mid-exchange;
        # drop the orphaned assistant turn so the window starts at a user turn.
        window = window[1:]
    return window


# Follow-up signal detection for the self-contained-question fast path.
#
# A message is treated as a follow-up (rewriter must run) when it is short or
# contains anaphoric / elliptical phrasing: pronouns and demonstratives ("it",
# "that", "those", ...), "what about ...", "how about ...", "and ...?", "also",
# "same", comparatives ("cheaper", "bigger", ...), ordinals ("first", "second"),
# or bare fragments without a question word or noun content. Long, specific,
# reference-free questions skip the extra LLM rewrite call.
_FOLLOW_UP_PATTERN = re.compile(
    r"(?i)\b(it|its|this|that|these|those|they|them|their|he|she|him|her|"
    r"same|also|else|other|another|above|former|latter|previous|"
    r"first|second|third|cheaper|bigger|smaller|higher|lower|better|more|less)\b"
    r"|\bwhat\s+about\b|\bhow\s+about\b|^\s*and\b|^\s*or\b|\bfor\s+(it|that|those|them)\b"
)
_QUESTION_WORD_PATTERN = re.compile(
    r"(?i)\b(what|how|when|where|which|who|whom|whose|why|is|are|do|does|did|"
    r"can|could|should|will|would|have|has|had|may|might|shall)\b"
)
_NOUNISH_PATTERN = re.compile(r"[A-Za-z]{4,}")


def _is_self_contained_question(user_query: str, history: list) -> bool:
    """Return True when the rewrite LLM call can be safely skipped.

    Skip conditions (all must hold):
      * there is prior conversation (otherwise ``rewrite_query`` already skips),
      * the message is at least 40 characters (elliptical fragments are short),
      * it contains a question word or verb signal AND noun-like content,
      * it carries no anaphoric / elliptical follow-up signals.

    The higher 40-char floor matters because a *new* topic question in an
    existing conversation (e.g. "How much is the hostel security deposit?"
    asked after an attendance question, 38 chars) still benefits from the
    rewriter confirming it is standalone. Short or reference-laden messages
    always go through the rewriter, preserving follow-up behavior exactly.
    """
    if not history:
        return True
    text = (user_query or "").strip()
    if len(text) < 40:
        return False
    if _FOLLOW_UP_PATTERN.search(text):
        return False
    if not _QUESTION_WORD_PATTERN.search(text):
        return False
    if not _NOUNISH_PATTERN.search(text):
        return False
    return True


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

    # Development timing diagnostics (never exposed to normal students).
    timings: dict = {}
    request_start = time.perf_counter()

    client = get_admin_client()

    # Step 1: Resolve or create conversation
    conversation_start = time.perf_counter()
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
        # NOTE (latency): the blocking ``update_conversation_timestamp`` write
        # that used to live here is intentionally NOT on the request path. The
        # background persistence worker already refreshes ``updated_at`` after
        # a successful generation, and the insufficient-context path leaves the
        # timestamp untouched. See ``_start_background_persistence``.
    timings["conversation_resolution_ms"] = int((time.perf_counter() - conversation_start) * 1000)

    # Step 1.5: Retrieve bounded conversation history for multi-turn context.
    # Runs BEFORE the current user message is persisted, so the history never
    # contains the current query (no duplication). Reuses the already-fetched
    # ``conversation`` row for ownership verification (the boundary resolved it
    # above), so this step performs exactly one DB round trip instead of two.
    history_start = time.perf_counter()
    message_summaries = get_conversation_messages(
        conversation_id, UUID(str(user_id)), conversation=conversation
    )
    timings["history_latency_ms"] = int((time.perf_counter() - history_start) * 1000)
    conversation_history = _bounded_conversation_history(
        [
            ConversationTurn(role=msg.message_type, content=msg.content_text)
            for msg in message_summaries
        ],
        max_messages=settings.conversation_history_max_messages,
    )

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

    # Step 2.5: Conversational query interpretation. A follow-up such as
    # "what about for girl?" is rewritten into a standalone retrieval question
    # using only the recent conversation. Standalone first messages pass
    # through unchanged, and failures fall back to the original query.
    #
    # Optimization (measured baseline: rewrite cost ~0 ms when skipped, a full
    # extra LLM round trip when it fires): skip the rewrite call entirely when
    # the message is self-contained — long enough AND free of anaphoric /
    # elliptical follow-up signals. Short or reference-laden messages still go
    # through the rewriter, preserving follow-up behavior exactly.
    rewrite_start = time.perf_counter()
    if _is_self_contained_question(request.user_query, conversation_history):
        retrieval_query = request.user_query
        timings["query_rewrite_skipped"] = True
    else:
        retrieval_query = rewrite_query(request.user_query, conversation_history, provider) or request.user_query
        timings["query_rewrite_skipped"] = retrieval_query == request.user_query and not conversation_history
    timings["query_rewrite_latency_ms"] = int((time.perf_counter() - rewrite_start) * 1000)


    # Step 3: If no chunks provided, invoke Phase 3 retrieval
    retrieved_chunks = request.retrieved_chunks
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
        retrieval_response = retrieve(retrieval_request, timings=retrieval_timings)
        timings["embedding_latency_ms"] = retrieval_timings.get("embedding_latency_ms", 0)
        timings["retrieval_latency_ms"] = retrieval_timings.get("vector_search_latency_ms", 0)
        retrieved_chunks = [
            _map_retrieval_result_to_chunk(result)
            for result in retrieval_response.results
        ]
    else:
        timings["embedding_latency_ms"] = 0
        timings["retrieval_latency_ms"] = 0

    # Step 4: Execute generation
    context_start = time.perf_counter()
    ai_request = AIRequest(
        user_query=request.user_query,
        retrieval_query=(retrieval_query if retrieval_query != request.user_query else None),
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

    assembled_context = assemble_context(ai_request, conversation_history=conversation_history)
    timings["context_build_latency_ms"] = int((time.perf_counter() - context_start) * 1000)

    prompt_start = time.perf_counter()
    prompt_text = ""
    try:
        from app.services.generation_provider import _build_user_content

        prompt_text = _build_user_content(assembled_context)
    except Exception:
        pass
    timings["prompt_build_latency_ms"] = int((time.perf_counter() - prompt_start) * 1000)

    stage_start = time.perf_counter()
    generation_result = AIGenerationService(provider).generate(
        assembled_context
    )
    latency_ms = int((time.perf_counter() - stage_start) * 1000)
    timings["llm_request_latency_ms"] = latency_ms
    # Non-streaming provider: time-to-first-token equals total generation time.
    # The API has no streaming path yet, so TTFT cannot be measured separately;
    # both fields report the single request duration until streaming is added.
    timings["llm_ttft_ms"] = latency_ms
    timings["llm_generation_latency_ms"] = latency_ms

    # Step 4.5: Extract validated source references from the generated answer
    parse_start = time.perf_counter()
    source_references = _extract_source_references(
        generation_result.answer, retrieved_chunks
    )
    timings["response_parse_latency_ms"] = int((time.perf_counter() - parse_start) * 1000)

    # Step 5: Persist assistant message and AI response only when generation succeeded
    persist_start = time.perf_counter()
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

        # Step 6.3: Persist AI response, retrieval operation, chunks, and citations
        # in the BACKGROUND. This is the largest controllable internal latency
        # contributor (~3-4s of DB work per the development latency baseline).
        # The response is returned without waiting for these writes. Failures
        # are logged only; they never affect the already-computed response.
        # Thread-safety: the worker issues its own admin client (created once
        # per process in ``get_admin_client``) rather than sharing a client
        # borrowed from the request thread, so concurrent requests cannot race
        # on one connection. A bounded ``background_errors`` list retains the
        # latest failure for development diagnostics.
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

    # Step 7 (Phase 4.4): Build structured sources and usage for the response
    # timings["persistence_latency_ms"] measures the blocking assistant-message
    # write. Heavy AI-response/retrieval/citation persistence runs in a
    # background thread and is therefore 0 on the request path by design.
    timings["persistence_latency_ms"] = int((time.perf_counter() - persist_start) * 1000)
    enrich_start = time.perf_counter()
    sources = _build_structured_sources(source_references, retrieved_chunks)
    _enrich_source_titles(client, sources)
    timings["source_enrichment_latency_ms"] = int((time.perf_counter() - enrich_start) * 1000)
    chat_usage = _build_chat_usage(generation_result.metadata)
    timings["total_latency_ms"] = int((time.perf_counter() - request_start) * 1000)
    _attach_observability_diagnostics(
        timings=timings,
        request=request,
        retrieval_query=retrieval_query,
        retrieved_chunks=retrieved_chunks,
        generation_result=generation_result,
        prompt_text=prompt_text,
    )

    # Step 8: Return response with conversation_id, message_id, and session_id
    return ChatResponse(
        session_id=session_context.session_id,
        conversation_id=conversation_id,
        message_id=message_id,
        answer=generation_result.answer,
        source_references=source_references,
        status=generation_result.status,
        model_used=generation_result.model_used,
        metadata={**generation_result.metadata, "diagnostics": timings} if settings.debug else generation_result.metadata,
        sources=sources,
        usage=chat_usage,
    )