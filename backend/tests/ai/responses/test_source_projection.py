"""Responses: source projection."""

import pytest

from .support import (
    CHUNK_A_ID,
    CHUNK_A_TEXT,
    CHUNK_B_ID,
    CHUNK_B_TEXT,
    ChatUsage,
    GenerationProvider,
    GenerationResult,
    MagicMock,
    RetrievalResult,
    SourceReference,
    StructuredSource,
    UUID,
    _build_structured_sources,
    _chat_request,
    _mock_client,
    _process,
    _retrieval_chunks,
    uuid4,
)


def test_structured_success_response_contains_all_fields():
    """Successful response contains all expected top-level fields."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={
            "provider": "openrouter",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        },
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.session_id is not None
    assert response.conversation_id is not None
    assert response.message_id is not None
    assert response.answer is not None
    assert isinstance(response.source_references, list)
    assert isinstance(response.sources, list)
    assert response.model_used == "openai/gpt-4o-mini"
    assert isinstance(response.metadata, dict)
    assert isinstance(response.usage, ChatUsage)


def test_structured_source_mapping_from_source_reference():
    """SourceReference fields are correctly mapped into StructuredSource."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            document_id=uuid4(),
            document_version_id=uuid4(),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    chunks = _retrieval_chunks().results

    structured = _build_structured_sources(source_refs, chunks)

    assert len(structured) == 1
    s = structured[0]
    assert isinstance(s, StructuredSource)
    assert s.chunk_id == UUID(CHUNK_A_ID)
    assert s.quote == CHUNK_A_TEXT
    assert s.relevance_score == 0.91
    # source_title is None before enrichment
    assert s.source_title is None
    # section comes from chunk metadata
    assert s.section == "Admissions"


@pytest.mark.parametrize('key', ['section', 'section_title'])
def test_section_enriched_from_chunk_metadata(key):
    """Live cards accept both provider metadata and persisted section titles."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    # Chunk with section in metadata
    chunks_with_section = [
        RetrievalResult(
            chunk_id=UUID(CHUNK_A_ID),
            text=CHUNK_A_TEXT,
            similarity_score=0.91,
            metadata={key: "Academic Regulations"},
        )
    ]

    structured = _build_structured_sources(source_refs, chunks_with_section)
    assert structured[0].section == "Academic Regulations"


def test_section_null_when_metadata_unavailable():
    """Section is null when chunk metadata has no section key."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    chunks_no_section = [
        RetrievalResult(
            chunk_id=UUID(CHUNK_A_ID),
            text=CHUNK_A_TEXT,
            similarity_score=0.91,
            metadata={},
        )
    ]

    structured = _build_structured_sources(source_refs, chunks_no_section)
    assert structured[0].section is None


def test_no_citations_produces_empty_sources():
    """Empty source_references produces empty sources list. No citation is inferred."""
    structured = _build_structured_sources([], _retrieval_chunks().results)
    assert structured == []


def test_multiple_sources_produce_multiple_structured_sources():
    """Multiple source references produce corresponding structured sources."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        ),
        SourceReference(
            chunk_id=UUID(CHUNK_B_ID),
            quote=CHUNK_B_TEXT,
            similarity_score=0.85,
        ),
    ]
    chunks = _retrieval_chunks().results

    structured = _build_structured_sources(source_refs, chunks)

    assert len(structured) == 2
    ids = {s.chunk_id for s in structured}
    assert ids == {UUID(CHUNK_A_ID), UUID(CHUNK_B_ID)}
    assert structured[0].section == "Admissions"
    assert structured[1].section == "Deadlines"


def test_retrieved_chunk_not_in_source_references_not_in_sources():
    """A retrieved chunk NOT in source_references does not appear in sources."""
    # Only CHUNK_A is cited, CHUNK_B is retrieved but not cited
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    chunks = _retrieval_chunks().results  # Contains both CHUNK_A and CHUNK_B

    structured = _build_structured_sources(source_refs, chunks)

    assert len(structured) == 1
    assert structured[0].chunk_id == UUID(CHUNK_A_ID)
    # CHUNK_B must NOT appear
    cited_ids = {s.chunk_id for s in structured}
    assert UUID(CHUNK_B_ID) not in cited_ids
