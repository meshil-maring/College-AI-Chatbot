"""Stage-level offline timer for the chat pipeline (no network, no DB).

Measures ONLY local CPU-bound stages testable without live credentials:
assembly + mapping + source parsing + usage building.

Usage (from backend dir):
    .venv/Scripts/python.exe _measure_local.py

Writes _measure_local.json with ms timings and token-ish char counts.
"""
import json
import time
import uuid
from unittest.mock import MagicMock


def main() -> dict:
    from app.schemas.chat import ChatRequest, ChatResponse
    from app.schemas.chat_response import StructuredSource
    from app.schemas.generation import (
        AIRequest,
        ConversationTurn,
        RetrievalScope,
        RetrievedChunk,
        SourceReference,
    )
    from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
    from app.services.chat import (
        _build_chat_usage,
        _build_structured_sources,
        _extract_source_references,
        _map_retrieval_result_to_chunk,
    )
    from app.services.context import assemble_context
    from app.services.generation_provider import _build_user_content

    out: dict = {}

    # --- Build representative fixtures -------------------------------------
    chunks = [
        RetrievedChunk(
            chunk_id=uuid.uuid4(),
            text=f"Hostel standard room costs Rs. 48,000 per year. Section {i}.",
            similarity_score=0.9 - i * 0.01,
            metadata={"section": f"Section {i}"},
        )
        for i in range(4)
    ]
    history = [
        ConversationTurn(role="user", content="What is the hostel fee?"),
        ConversationTurn(role="assistant", content="Rs. 48,000 per year."),
    ]

    n = 30

    # --- assemble_context ---------------------------------------------------
    t0 = time.perf_counter()
    for _ in range(n):
        req = AIRequest(
            user_query="What about for girls?",
            retrieval_query="What is the hostel fee for girls?",
            retrieval_scope=RetrievalScope(institution_id=uuid.uuid4()),
            retrieved_chunks=chunks,
            conversation_history=history,
        )
        ctx = assemble_context(req, conversation_history=history)
    out["assemble_context_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)

    # --- prompt build --------------------------------------------------------
    t0 = time.perf_counter()
    for _ in range(n):
        _build_user_content(ctx)
    out["prompt_build_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)
    prompt = _build_user_content(ctx)
    out["prompt_chars"] = len(prompt)
    out["prompt_est_input_tokens_4chars"] = round(len(prompt) / 4)

    # --- validation of ChatRequest -------------------------------------------
    q = "What is the minimum attendance required to appear for the semester examination?"
    t0 = time.perf_counter()
    for _ in range(n):
        ChatRequest(user_query=q, institution_id=uuid.uuid4())
    out["request_validation_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)

    # --- retrieval mapping ---------------------------------------------------
    results = [
        RetrievalResult(
            chunk_id=c.chunk_id,
            text=c.text,
            similarity_score=c.similarity_score,
            metadata=c.metadata,
        )
        for c in chunks
    ]
    t0 = time.perf_counter()
    for _ in range(n):
        [_map_retrieval_result_to_chunk(r) for r in results]
    out["retrieval_mapping_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)

    # --- source reference parsing --------------------------------------------
    answer = "The fee is Rs. 48,000 [Retrieved chunk %s]." % chunks[0].chunk_id
    t0 = time.perf_counter()
    for _ in range(n):
        refs = _extract_source_references(answer, chunks)
    out["source_parse_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)
    out["source_parse_refs"] = len(refs)

    # --- structured sources ---------------------------------------------------
    t0 = time.perf_counter()
    for _ in range(n):
        _build_structured_sources(refs, chunks)
    out["structured_sources_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)

    # --- usage mapping ---------------------------------------------------------
    t0 = time.perf_counter()
    for _ in range(n):
        _build_chat_usage({"usage": {"prompt_tokens": 813, "completion_tokens": 50}})
    out["usage_build_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)

    # --- RetrievalRequest validation -------------------------------------------
    t0 = time.perf_counter()
    for _ in range(n):
        RetrievalRequest(query=q, top_k=4, institution_id=uuid.uuid4())
    out["retrieval_request_validation_avg_ms"] = round(
        (time.perf_counter() - t0) / n * 1000, 3
    )

    # --- rewrite skip path ------------------------------------------------------
    from app.services.query_rewriting import rewrite_query

    provider = MagicMock()
    t0 = time.perf_counter()
    for _ in range(n):
        rewrite_query("What is the hostel fee?", [], provider)
    out["rewrite_skip_avg_ms"] = round((time.perf_counter() - t0) / n * 1000, 3)
    out["rewrite_skip_provider_calls"] = provider.generate.call_count

    with open("_measure_local.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    main()
