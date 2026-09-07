"""Orchestration for one request through the application chat boundary."""

import re
import time
from uuid import UUID

from app.db.supabase import get_admin_client
from app.repositories.conversation import (
    create_conversation,
    get_conversation,
    update_conversation_timestamp,
)
from app.repositories.message import create_message, get_next_message_sequence
from app.repositories.ai_response import create_ai_response
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import (
    AIResponseCreate,
    ConversationCreate,
    MessageCreate,
)
from app.schemas.generation import AIRequest, RetrievalScope, RetrievedChunk, SourceReference
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
    user_message = create_message(
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

    # Step 4.5: Extract source references from generated answer
    source_references = _extract_source_references(generation_result.answer, retrieved_chunks)

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

        create_ai_response(
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

    # Step 7: Return response with conversation_id, message_id, and session_id
    response_data = generation_result.model_dump()
    response_data["source_references"] = source_references
    return ChatResponse(
        session_id=session_context.session_id,
        conversation_id=conversation_id,
        message_id=message_id,
        **response_data,
    )