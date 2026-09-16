"""
Append background persistence helpers to public_chat.py.
"""

import os
os.chdir('F:\\Git Project\\CollegeAIChatbot\\backend')

bg_helpers = '''
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
'''

with open('app/services/public_chat.py', 'a') as f:
    f.write('\n' + bg_helpers.lstrip('\n'))

print('Background helpers appended')
