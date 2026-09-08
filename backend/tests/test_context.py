"""Tests for Phase 4.2 prompt and context assembly."""

from uuid import UUID, uuid4

import pytest

from app.schemas.generation import AIRequest, RetrievalScope, RetrievedChunk
from app.services.context import (
    EMPTY_RETRIEVAL_NOTICE,
    GROUNDING_INSTRUCTIONS,
    SYSTEM_INSTRUCTIONS,
    assemble_context,
)


def valid_scope() -> RetrievalScope:
    return RetrievalScope(institution_id=uuid4())


def chunk(number: int) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
        document_id=UUID("10000000-0000-0000-0000-000000000001"),
        document_version_id=UUID("20000000-0000-0000-0000-000000000001"),
        text=f"Knowledge text {number}",
        similarity_score=0.9 - number / 100,
        metadata={
            "knowledge_source_id": "source-1",
            "section_title": f"Section {number}",
            "chunk_sequence": number,
        },
    )


def request_with_chunks(chunks: list[RetrievedChunk]) -> AIRequest:
    return AIRequest(
        user_query="  What   are the requirements? ",
        retrieval_scope=valid_scope(),
        retrieved_chunks=chunks,
    )


def test_valid_request_produces_valid_context() -> None:
    context = assemble_context(request_with_chunks([chunk(1)]))

    assert context.user_question == "What are the requirements?"
    assert len(context.retrieved_knowledge) == 1


def test_user_question_is_transferred_after_contract_normalization() -> None:
    request = request_with_chunks([])

    assert assemble_context(request).user_question == request.user_query


def test_retrieved_chunks_are_assembled_in_existing_order() -> None:
    chunks = [chunk(2), chunk(1), chunk(3)]

    context = assemble_context(request_with_chunks(chunks))

    assert context.retrieved_knowledge == chunks
    assert [item.chunk_id for item in context.retrieved_knowledge] == [
        item.chunk_id for item in chunks
    ]


def test_chunk_order_is_deterministic_without_sorting() -> None:
    chunks = [chunk(3), chunk(1), chunk(2)]
    request = request_with_chunks(chunks)

    first_order = [item.metadata["chunk_sequence"] for item in assemble_context(request).retrieved_knowledge]
    second_order = [item.metadata["chunk_sequence"] for item in assemble_context(request).retrieved_knowledge]

    assert first_order == second_order == [3, 1, 2]


def test_chunk_provenance_is_preserved() -> None:
    source_chunk = chunk(1)

    assembled_chunk = assemble_context(request_with_chunks([source_chunk])).retrieved_knowledge[0]

    assert assembled_chunk.chunk_id == source_chunk.chunk_id
    assert assembled_chunk.document_id == source_chunk.document_id
    assert assembled_chunk.document_version_id == source_chunk.document_version_id
    assert assembled_chunk.metadata == source_chunk.metadata
    assert assembled_chunk.text == source_chunk.text


def test_system_instructions_are_present() -> None:
    context = assemble_context(request_with_chunks([]))

    assert context.system_instructions == SYSTEM_INSTRUCTIONS
    assert "authoritative" in context.system_instructions
    assert "Do not invent" in context.system_instructions


def test_system_instructions_permit_conversational_history_use() -> None:
    context = assemble_context(request_with_chunks([]))

    assert "conversational context" in context.system_instructions
    assert "not institutional knowledge" in context.system_instructions
    assert "previous user question" in context.system_instructions
    assert "Never treat a previous assistant statement as" in context.system_instructions


def test_grounding_and_citation_instructions_are_present() -> None:
    context = assemble_context(request_with_chunks([chunk(1)]))

    assert context.grounding_instructions == GROUNDING_INSTRUCTIONS
    assert "factual claim" in context.grounding_instructions
    assert "fabricate citations" in context.grounding_instructions


def test_grounding_instructions_exempt_conversational_meta_questions() -> None:
    context = assemble_context(request_with_chunks([chunk(1)]))

    assert "conversation itself" in context.grounding_instructions
    assert "do not substitute conversation history for institutional knowledge" in (
        context.grounding_instructions
    )


def test_empty_retrieval_produces_insufficient_context() -> None:
    context = assemble_context(request_with_chunks([]))

    assert context.user_question == "What are the requirements?"
    assert context.retrieved_knowledge == []
    assert EMPTY_RETRIEVAL_NOTICE in context.grounding_instructions
    assert "insufficient" in context.grounding_instructions
    assert "conversation history may still be used" in context.grounding_instructions


def test_same_request_produces_identical_context() -> None:
    request = request_with_chunks([chunk(1), chunk(2)])

    first = assemble_context(request)
    second = assemble_context(request)

    assert first == second
    assert first.model_dump() == second.model_dump()


def test_assembler_does_not_call_external_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("external dependency was called")

    monkeypatch.setattr("app.db.supabase.get_admin_client", fail_if_called)
    monkeypatch.setattr("app.services.embeddings.embed_query", fail_if_called)

    context = assemble_context(request_with_chunks([chunk(1)]))

    assert context.retrieved_knowledge[0].chunk_id == chunk(1).chunk_id


def test_assembler_does_not_retrieve_or_generate_answers() -> None:
    context = assemble_context(request_with_chunks([chunk(1)]))

    assert not hasattr(context, "answer")
    assert context.retrieved_knowledge[0].text == "Knowledge text 1"


def test_invalid_ai_request_is_not_silently_converted() -> None:
    with pytest.raises(TypeError, match="validated AIRequest"):
        assemble_context({
            "user_query": "What are the requirements?",
            "retrieval_scope": {"institution_id": str(uuid4())},
            "retrieved_chunks": [],
        })