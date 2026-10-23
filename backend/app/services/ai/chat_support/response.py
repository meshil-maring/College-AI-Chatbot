"""Build the chat response from validated generation and retrieval output."""

import time

from app.config import settings
from app.schemas.ai.chat import ChatResponse
from .diagnostics import _attach_observability_diagnostics
from .sources import _build_chat_usage, _build_structured_sources, _enrich_source_titles


def finish_response(
    *,
    client,
    request,
    session_context,
    conversation_id,
    message_id,
    generation_result,
    retrieval_query,
    retrieved_chunks,
    source_references,
    timings,
    request_start,
    prompt_text,
):
    start = time.perf_counter()
    sources = _build_structured_sources(source_references, retrieved_chunks)
    _enrich_source_titles(client, sources)
    timings["source_enrichment_latency_ms"] = int((time.perf_counter() - start) * 1000)
    usage = _build_chat_usage(generation_result.metadata)
    timings["total_latency_ms"] = int((time.perf_counter() - request_start) * 1000)
    _attach_observability_diagnostics(
        timings=timings,
        request=request,
        retrieval_query=retrieval_query,
        retrieved_chunks=retrieved_chunks,
        generation_result=generation_result,
        prompt_text=prompt_text,
    )
    return ChatResponse(
        session_id=session_context.session_id,
        conversation_id=conversation_id,
        message_id=message_id,
        answer=generation_result.answer,
        source_references=source_references,
        status=generation_result.status,
        model_used=generation_result.model_used,
        metadata={**generation_result.metadata, "diagnostics": timings}
        if settings.debug
        else generation_result.metadata,
        sources=sources,
        usage=usage,
    )
