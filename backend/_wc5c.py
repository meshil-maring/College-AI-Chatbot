"""
Append Part C: Steps 4.5-7 of process_chat_request + closing.
"""

import os
os.chdir('F:\\Git Project\\CollegeAIChatbot\\backend')

part_c = r'''
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
'''

with open('app/services/public_chat.py', 'a') as f:
    f.write('\n' + part_c.lstrip('\n'))

print('Part C appended - file complete')
