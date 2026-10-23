"""Privacy-preserving chat latency diagnostics."""

from app.services.ai.personalization import (
    prompt_contains_student_data,
    redact_student_data,
)


def _attach_observability_diagnostics(
    *,
    timings: dict,
    request,
    retrieval_query: str,
    retrieved_chunks,
    generation_result,
    prompt_text: str = "",
) -> None:
    """Attach debug-only latency/observability diagnostics (never user-facing).

    Students never see this dictionary: ``process_chat_request`` only merges
    ``timings`` into response metadata when ``settings.debug`` is enabled.

    Phase 6.10 privacy hardening: the prompt text (which may contain the
    authorized student data block) is REDACTED before any use inside this
    diagnostics path. No prompt text — redacted or otherwise — is stored in
    ``timings``; only counts, scores/ids, and a boolean marker that
    personalization was active. The AI generation itself is unaffected: the
    provider receives the unredacted ``AIContext``.
    """
    timings["student_data_in_prompt"] = prompt_contains_student_data(prompt_text)
    prompt_text = redact_student_data(prompt_text) or ""
    timings["original_query"] = request.user_query
    timings["rewritten_query"] = (
        retrieval_query if retrieval_query != request.user_query else None
    )
    timings["retrieved_chunk_count"] = len(retrieved_chunks)
    timings["retrieved_chunk_ids"] = [str(chunk.chunk_id) for chunk in retrieved_chunks]
    timings["retrieved_scores"] = [chunk.similarity_score for chunk in retrieved_chunks]
    try:
        from app.services.ai.generation_provider import estimate_prompt_tokens

        # Estimated on the REDACTED prompt: diagnostics never need the private
        # block, and a rough dev heuristic does not justify handling it.
        timings["final_context_token_count"] = estimate_prompt_tokens(prompt_text)
    except Exception:
        timings["final_context_token_count"] = 0
    usage = (
        getattr(generation_result, "metadata", {}).get("usage", {})
        if isinstance(getattr(generation_result, "metadata", {}), dict)
        else {}
    )
    timings["final_input_token_count"] = (
        usage.get("prompt_tokens") if isinstance(usage, dict) else None
    )
    timings["output_token_count"] = (
        usage.get("completion_tokens") if isinstance(usage, dict) else None
    )
