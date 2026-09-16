"""
Append Part B: Steps 2.5-4 of process_chat_request.
"""

import os
os.chdir('F:\\Git Project\\CollegeAIChatbot\\backend')

part_b = r'''
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
'''

with open('app/services/public_chat.py', 'a') as f:
    f.write('\n' + part_b.lstrip('\n'))

print('Part B appended')
