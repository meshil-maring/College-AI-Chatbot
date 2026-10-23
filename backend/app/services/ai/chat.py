"""Authenticated conversation orchestration without academic data access."""

import threading
import time
from uuid import UUID

from app.config import settings
from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.ai.conversation import create_conversation, get_conversation
from app.repositories.ai.message import create_message, get_next_message_sequence
from app.schemas.ai.chat import ChatRequest, ChatResponse
from app.schemas.ai.conversation import ConversationCreate, MessageCreate
from app.schemas.ai.generation import ConversationTurn
from app.schemas.ai.session import SessionContext
from app.services.ai.conversation_history import get_conversation_messages
from app.services.ai.conversation_intent import (
    ConversationIntent,
    classify_conversation_intent,
)
from app.services.ai.generation import AIGenerationService
from app.services.ai.generation_provider import (
    GenerationProvider,
    _build_user_content,
)
from app.services.ai.query_rewriting import rewrite_query
from app.services.knowledge.retrieval import retrieve
from .chat_support.context import build_chat_context, build_retrieval_request
from .chat_support.generation import generate_chat_response
from .chat_support.history import (
    _bounded_conversation_history,
    _is_self_contained_question,
)
from .chat_support.persistence import persist_response
from .chat_support.response import finish_response
from .chat_support.sources import (
    _build_chat_usage,
    _build_structured_sources,
    _enrich_source_titles,
    _extract_source_references,
    _map_retrieval_result_to_chunk,
)

_background_errors: list[str] = []


def _persist_in_background(**kwargs):
    persist_response(
        client_factory=get_admin_client, errors=_background_errors, **kwargs
    )


def _start_background_persistence(**kwargs):
    threading.Thread(target=_persist_in_background, kwargs=kwargs, daemon=True).start()


def process_chat_request(
    request: ChatRequest,
    session_context: SessionContext,
    provider: GenerationProvider,
    user_id: UUID | str,
    *,
    current_user: dict | None = None,
) -> ChatResponse:
    """Retain conversation ownership, institutional RAG, generation and citations."""
    if not isinstance(request, ChatRequest):
        raise TypeError("request must be a validated ChatRequest")
    if not isinstance(session_context, SessionContext):
        raise TypeError("session_context must be a validated SessionContext")
    timings: dict = {}
    request_start = time.perf_counter()
    client = get_admin_client()
    start = time.perf_counter()
    conversation_id = (
        request.conversation_id or request.session_id or session_context.session_id
    )
    conversation = get_conversation(client, conversation_id)
    if conversation is None:
        conversation = create_conversation(
            client,
            ConversationCreate(
                user_id=UUID(str(user_id)),
                title=request.user_query[:60],
                status="active",
            ),
            conversation_id=conversation_id,
        )
    elif str(conversation["user_id"]) != str(user_id):
        raise AppError(
            "Conversation not found", status_code=404, code="CONVERSATION_NOT_FOUND"
        )
    conversation_id = UUID(conversation["conversation_id"])
    timings["conversation_resolution_ms"] = int((time.perf_counter() - start) * 1000)

    # Read history before saving this turn, avoiding duplicate current messages.
    start = time.perf_counter()
    messages = get_conversation_messages(
        conversation_id, UUID(str(user_id)), conversation=conversation
    )
    conversation_history = _bounded_conversation_history(
        [
            ConversationTurn(role=message.message_type, content=message.content_text)
            for message in messages
        ],
        max_messages=settings.conversation_history_max_messages,
    )
    timings["history_latency_ms"] = int((time.perf_counter() - start) * 1000)
    intent = classify_conversation_intent(
        request.user_query, conversation_history, authenticated=True
    )
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

    direct_intents = {
        ConversationIntent.CASUAL,
        ConversationIntent.GENERAL_KNOWLEDGE,
        ConversationIntent.AI_IDENTITY,
        ConversationIntent.AMBIGUOUS,
        ConversationIntent.RESTRICTED_ACTION,
        ConversationIntent.PERSONAL_DATA,
    }
    start = time.perf_counter()
    if intent in direct_intents or _is_self_contained_question(
        request.user_query, conversation_history
    ):
        retrieval_query = request.user_query
        timings["query_rewrite_skipped"] = True
    else:
        retrieval_query = (
            rewrite_query(request.user_query, conversation_history, provider)
            or request.user_query
        )
        timings["query_rewrite_skipped"] = (
            retrieval_query == request.user_query and not conversation_history
        )
    timings["query_rewrite_latency_ms"] = int((time.perf_counter() - start) * 1000)
    retrieved_chunks = [] if intent in direct_intents else request.retrieved_chunks
    timings["embedding_latency_ms"] = 0
    timings["retrieval_latency_ms"] = 0
    if intent not in direct_intents and not retrieved_chunks:
        retrieval_timings: dict = {}
        response = retrieve(
            build_retrieval_request(request, retrieval_query, settings.retrieval_top_k),
            timings=retrieval_timings,
        )
        timings["embedding_latency_ms"] = retrieval_timings.get(
            "embedding_latency_ms", 0
        )
        timings["retrieval_latency_ms"] = retrieval_timings.get(
            "vector_search_latency_ms", 0
        )
        retrieved_chunks = [
            _map_retrieval_result_to_chunk(result) for result in response.results
        ]

    start = time.perf_counter()
    context = build_chat_context(
        request=request,
        retrieval_query=retrieval_query,
        conversation_history=conversation_history,
        retrieved_chunks=retrieved_chunks,
        intent=intent,
    )
    timings["context_build_latency_ms"] = int((time.perf_counter() - start) * 1000)
    start = time.perf_counter()
    prompt_text = ""
    if context is not None:
        try:
            prompt_text = _build_user_content(context)
        except Exception:
            pass
    timings["prompt_build_latency_ms"] = int((time.perf_counter() - start) * 1000)
    start = time.perf_counter()
    result = generate_chat_response(
        query=request.user_query,
        intent=intent,
        context=context,
        provider=provider,
        service_factory=AIGenerationService,
    )
    latency_ms = int((time.perf_counter() - start) * 1000)
    timings["llm_request_latency_ms"] = latency_ms
    timings["llm_ttft_ms"] = latency_ms
    timings["llm_generation_latency_ms"] = latency_ms
    start = time.perf_counter()
    references = _extract_source_references(result.answer, retrieved_chunks)
    timings["response_parse_latency_ms"] = int((time.perf_counter() - start) * 1000)

    start = time.perf_counter()
    message_id = None
    if result.answer is not None:
        assistant = create_message(
            client,
            MessageCreate(
                conversation_id=conversation_id,
                message_sequence=get_next_message_sequence(client, conversation_id),
                message_type="assistant",
                content_text=result.answer,
            ),
        )
        message_id = UUID(assistant["message_id"])
        usage = (
            result.metadata.get("usage", {})
            if isinstance(result.metadata, dict)
            else {}
        )
        if not isinstance(usage, dict):
            usage = {}
        _start_background_persistence(
            conversation_id=conversation_id,
            message_id=message_id,
            retrieval_query=retrieval_query,
            retrieved_chunks=retrieved_chunks,
            source_references=references,
            generation_result=result,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
        )
    timings["persistence_latency_ms"] = int((time.perf_counter() - start) * 1000)
    return finish_response(
        client=client,
        request=request,
        session_context=session_context,
        conversation_id=conversation_id,
        message_id=message_id,
        generation_result=result,
        retrieval_query=retrieval_query,
        retrieved_chunks=retrieved_chunks,
        source_references=references,
        timings=timings,
        request_start=request_start,
        prompt_text=prompt_text,
    )
