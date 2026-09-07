"""Phase 4.4 focused tests for structured chat response.

Tests the structured response models (StructuredSource, ChatUsage),
source enrichment, usage mapping, and backward compatibility.
"""

from uuid import UUID, uuid4
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.chat_response import ChatUsage, StructuredSource
from app.schemas.generation import SourceReference
from app.schemas.retrieval import RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.chat import (
    _build_chat_usage,
    _build_structured_sources,
    _enrich_source_titles,
    process_chat_request,
)
from app.services.generation_provider import GenerationProvider, GenerationResult


INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
CHUNK_A_ID = "40000000-0000-0000-0000-000000000001"
CHUNK_B_ID = "40000000-0000-0000-0000-000000000002"
CHUNK_A_TEXT = "Admission requires a completed application form."
CHUNK_B_TEXT = "The deadline is June 30th."
TEST_USER_ID = uuid4()


def _retrieval_chunks():
    return RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=UUID(CHUNK_A_ID),
                text=CHUNK_A_TEXT,
                similarity_score=0.91,
                metadata={"section": "Admissions"},
            ),
            RetrievalResult(
                chunk_id=UUID(CHUNK_B_ID),
                text=CHUNK_B_TEXT,
                similarity_score=0.85,
                metadata={"section": "Deadlines"},
            ),
        ]
    )


def _chat_request(**overrides):
    base = {
        "user_query": "What are the admission requirements?",
        "institution_id": UUID(INSTITUTION_ID),
    }
    base.update(overrides)
    return ChatRequest(**base)


def _mock_client(insert_side_effects=None):
    """Build a mock Supabase client with standard lookup behavior."""
    mc = MagicMock()
    mc.table().select().eq().maybe_single().execute.return_value = MagicMock(data=None)
    mc.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    if insert_side_effects is not None:
        mc.table().insert().execute.side_effect = insert_side_effects
    else:
        mc.table().insert().execute.side_effect = [
            MagicMock(data=[{"conversation_id": str(uuid4())}]),
            MagicMock(data=[{"message_id": str(uuid4())}]),
            MagicMock(data=[{"message_id": str(uuid4())}]),
            MagicMock(data=[{"ai_response_id": str(uuid4())}]),
            MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
            MagicMock(data=[{"chunk_id": str(uuid4())}]),
            MagicMock(data=[{"message_citation_id": str(uuid4())}]),
        ]
    return mc


def _process(request, provider, client, retrieval=None):
    """Run process_chat_request with mocked dependencies."""
    session_context = SessionContext(session_id=uuid4())
    with (
        patch("app.services.chat.get_admin_client", return_value=client),
        patch("app.services.chat.retrieve", return_value=retrieval or _retrieval_chunks()),
    ):
        return process_chat_request(request, session_context, provider, TEST_USER_ID), session_context


# ---------------------------------------------------------------------------
# TEST 1 — STRUCTURED SUCCESS RESPONSE
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TEST 2 — STRUCTURED SOURCE MAPPING
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TEST 3 — SOURCE TITLE ENRICHMENT
# ---------------------------------------------------------------------------


def test_source_title_enrichment_via_provenance_chain():
    """Enrichment resolves source_title from knowledge_sources.title via provenance chain."""
    source_refs = [
        SourceReference(
            chunk_id=UUID(CHUNK_A_ID),
            quote=CHUNK_A_TEXT,
            similarity_score=0.91,
        )
    ]
    chunks = _retrieval_chunks().results
    structured = _build_structured_sources(source_refs, chunks)

    # Mock the 5-step provenance chain query
    mock_client = MagicMock()

    # Step 1: knowledge_chunks
    mock_client.table().select().in_().execute.side_effect = [
        # knowledge_chunks
        MagicMock(data=[{"chunk_id": CHUNK_A_ID, "processing_run_id": "run-001"}]),
        # document_processing_runs
        MagicMock(data=[{"processing_run_id": "run-001", "document_version_id": "ver-001"}]),
        # document_versions
        MagicMock(data=[{"document_version_id": "ver-001", "document_id": "doc-001"}]),
        # documents
        MagicMock(data=[{"document_id": "doc-001", "knowledge_source_id": "ks-001"}]),
        # knowledge_sources
        MagicMock(data=[{"knowledge_source_id": "ks-001", "title": "Attendance Regulations"}]),
    ]

    _enrich_source_titles(mock_client, structured)

    assert structured[0].source_title == "Attendance Regulations"


# ---------------------------------------------------------------------------
# TEST 4 — SECTION ENRICHMENT
# ---------------------------------------------------------------------------


def test_section_enriched_from_chunk_metadata():
    """Section is extracted from RetrievedChunk.metadata["section"]."""
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
            metadata={"section": "Academic Regulations"},
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


# ---------------------------------------------------------------------------
# TEST 5 — NO CITATIONS
# ---------------------------------------------------------------------------


def test_no_citations_produces_empty_sources():
    """Empty source_references produces empty sources list. No citation is inferred."""
    structured = _build_structured_sources([], _retrieval_chunks().results)
    assert structured == []


# ---------------------------------------------------------------------------
# TEST 6 — USAGE MAPPING
# ---------------------------------------------------------------------------


def test_usage_mapping_from_metadata():
    """metadata["usage"] values are correctly mapped to ChatUsage."""
    metadata = {
        "provider": "openrouter",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
        },
    }

    usage = _build_chat_usage(metadata)

    assert isinstance(usage, ChatUsage)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50


# ---------------------------------------------------------------------------
# TEST 7 — MISSING USAGE
# ---------------------------------------------------------------------------


def test_missing_usage_returns_none():
    """Missing or empty usage data returns None without failure."""
    assert _build_chat_usage({}) is None
    assert _build_chat_usage({"usage": {}}) is None
    assert _build_chat_usage({"usage": {"prompt_tokens": 100}}) is not None
    assert _build_chat_usage(None) is None
    assert _build_chat_usage("not-a-dict") is None


# ---------------------------------------------------------------------------
# TEST 8 — INSUFFICIENT CONTEXT
# ---------------------------------------------------------------------------


def test_insufficient_context_structured_response():
    """Insufficient context produces null/empty structured fields."""
    mock_provider = MagicMock(spec=GenerationProvider)

    mc = _mock_client([
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
    ])

    request = _chat_request(user_query="What is quantum computing?")
    retrieval = RetrievalResponse(results=[])

    session_context = SessionContext(session_id=uuid4())
    with (
        patch("app.services.chat.get_admin_client", return_value=mc),
        patch("app.services.chat.retrieve", return_value=retrieval),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.status == "insufficient_context"
    assert response.answer is None
    assert response.message_id is None
    assert response.source_references == []
    assert response.sources == []
    assert response.usage is None
    assert response.model_used is None


# ---------------------------------------------------------------------------
# TEST 9 — BACKWARD COMPATIBILITY
# ---------------------------------------------------------------------------


def test_backward_compatibility_existing_fields_preserved():
    """All existing ChatResponse fields remain present and functional."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"According to [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={"provider": "openrouter", "usage": {"prompt_tokens": 100, "completion_tokens": 50}},
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    # All original fields present
    assert hasattr(response, "session_id")
    assert hasattr(response, "conversation_id")
    assert hasattr(response, "message_id")
    assert hasattr(response, "answer")
    assert hasattr(response, "source_references")
    assert hasattr(response, "status")
    assert hasattr(response, "model_used")
    assert hasattr(response, "metadata")

    # source_references still populated from Phase 4.3 logic
    assert isinstance(response.source_references, list)
    assert len(response.source_references) == 1
    assert response.source_references[0].chunk_id == UUID(CHUNK_A_ID)

    # metadata still populated
    assert response.metadata["provider"] == "openrouter"
    assert "usage" in response.metadata

    # New fields also present
    assert isinstance(response.sources, list)
    assert isinstance(response.usage, ChatUsage)


# ---------------------------------------------------------------------------
# TEST 10 — MULTIPLE SOURCES
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TEST 11 — NO FABRICATED SOURCE
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TEST 12 — PROVIDER IMMUTABILITY
# ---------------------------------------------------------------------------


def test_generation_provider_file_unchanged():
    """generation_provider.py must not have been modified for Phase 4.4."""
    import pathlib

    provider_path = pathlib.Path(__file__).resolve().parent.parent / "app" / "services" / "generation_provider.py"
    content = provider_path.read_text(encoding="utf-8")

    # Verify key provider characteristics remain intact
    assert "class GenerationResult" in content
    assert "class GenerationProvider" in content
    assert "class OpenRouterGenerationProvider" in content
    assert "def generate(self, context: AIContext) -> GenerationResult:" in content

    # Verify provider does NOT contain Phase 4.4 structured response logic
    assert "StructuredSource" not in content
    assert "ChatUsage" not in content
    assert "_build_structured_sources" not in content
    assert "_enrich_source_titles" not in content
    assert "_build_chat_usage" not in content

    # Verify the model configuration is unchanged
    assert "openrouter" in content
    assert "openai/gpt-4o-mini" in content or "settings.openrouter_model" in content
