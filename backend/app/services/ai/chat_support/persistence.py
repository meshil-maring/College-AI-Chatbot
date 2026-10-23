"""Background persistence for ordinary authenticated conversations."""

import logging
from uuid import UUID

from app.repositories.ai.ai_response import create_ai_response
from app.repositories.ai.conversation import update_conversation_timestamp
from app.repositories.ai.message_citation import create_message_citations
from app.repositories.knowledge.retrieval_operation import (
    create_retrieval_operation,
    create_retrieved_chunks,
)
from app.schemas.ai.citation import (
    MessageCitationCreate,
    RetrievedChunkCreate,
    RetrievalOperationCreate,
)
from app.schemas.ai.conversation import AIResponseCreate


def persist_response(
    *,
    client_factory,
    errors,
    conversation_id,
    message_id,
    retrieval_query,
    retrieved_chunks,
    source_references,
    generation_result,
    input_tokens,
    output_tokens,
    latency_ms,
):
    """Resolve a client in the worker and retain bounded diagnostic failures."""
    try:
        client = client_factory()
        response = create_ai_response(
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
        update_conversation_timestamp(client, conversation_id)
        operation = create_retrieval_operation(
            client,
            RetrievalOperationCreate(
                ai_response_id=UUID(response["ai_response_id"]),
                query_text=retrieval_query,
                status="completed",
                result_count=len(retrieved_chunks),
            ),
        )
        operation_id = UUID(operation["retrieval_operation_id"])
        create_retrieved_chunks(
            client,
            [
                RetrievedChunkCreate(
                    retrieval_operation_id=operation_id,
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
                    retrieval_operation_id=operation_id,
                    chunk_id=reference.chunk_id,
                    display_order=order,
                )
                for order, reference in enumerate(source_references, start=1)
            ],
        )
    except Exception as error:
        logging.error("Background persistence failed", exc_info=True)
        errors.append(f"{type(error).__name__}: {error}")
        del errors[:-20]
