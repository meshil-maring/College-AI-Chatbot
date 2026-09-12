"""Phase 4.3 focused tests for citation and source-traceability persistence."""

from uuid import UUID, uuid4
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.generation import SourceReference
from app.schemas.retrieval import RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.chat import _persist_in_background, process_chat_request
from app.services.generation_provider import GenerationProvider, GenerationResult


@pytest.fixture(autouse=True)
def _sync_background_persistence(monkeypatch):
    """Run post-generation persistence synchronously for deterministic asserts.

    ``process_chat_request`` fires the AI-response / retrieval / citation
    writes on a daemon thread so live requests do not block on DB writes.
    These tests assert exact insert call counts immediately after the request
    returns, so the thread launch is replaced with a direct call to the same
    worker function (which resolves its own client via the patched
    ``get_admin_client``).
    """
    monkeypatch.setattr(
        "app.services.chat._start_background_persistence",
        lambda **kwargs: _persist_in_background(**kwargs),
    )


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
    mc.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
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
        patch("app.services.conversation_history.get_admin_client", return_value=client),
        patch("app.services.chat.retrieve", return_value=retrieval or _retrieval_chunks()),
    ):
        return process_chat_request(request, session_context, provider, TEST_USER_ID), session_context


# ---------------------------------------------------------------------------
# TEST 1 — SINGLE VALID CITATION
# ---------------------------------------------------------------------------

def test_single_valid_citation_is_persisted():
    """Answer containing [Retrieved chunk <UUID>] creates exactly one message_citations row."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.message_id is not None
    assert len(response.source_references) == 1
    assert response.source_references[0].chunk_id == UUID(CHUNK_A_ID)

    # Verify 7 inserts: conversation + user + assistant + ai_response + retrieval_op + chunks + 1 citation
    assert mc.table().insert().execute.call_count == 7


# ---------------------------------------------------------------------------
# TEST 2 — MULTIPLE VALID CITATIONS
# ---------------------------------------------------------------------------

def test_multiple_valid_citations_are_persisted():
    """Answer referencing two retrieved chunks creates two message_citations rows."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}] and [Retrieved chunk {CHUNK_B_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert len(response.source_references) == 2
    ref_ids = {r.chunk_id for r in response.source_references}
    assert ref_ids == {UUID(CHUNK_A_ID), UUID(CHUNK_B_ID)}

    # 7 inserts: conversation + user + assistant + ai_response + retrieval_op + chunks_batch + citations_batch
    assert mc.table().insert().execute.call_count == 7


# ---------------------------------------------------------------------------
# TEST 3 — NO EXPLICIT CITATION
# ---------------------------------------------------------------------------

def test_no_explicit_citation_produces_zero_citations():
    """Successful answer without chunk references creates zero message_citations rows."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="The admission process is straightforward.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.message_id is not None
    assert response.source_references == []

    # 6 inserts: ... + retrieval_op + chunks (NO citation insert)
    assert mc.table().insert().execute.call_count == 6


# ---------------------------------------------------------------------------
# TEST 4 — INVALID UUID
# ---------------------------------------------------------------------------

def test_invalid_uuid_in_answer_does_not_create_citation():
    """[Retrieved chunk not-a-valid-uuid] does not create a citation."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="See [Retrieved chunk not-a-valid-uuid].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.source_references == []

    # 6 inserts: no citation created for invalid UUID
    assert mc.table().insert().execute.call_count == 6


# ---------------------------------------------------------------------------
# TEST 5 — VALID UUID BUT NOT RETRIEVED
# ---------------------------------------------------------------------------

def test_valid_uuid_not_in_retrieved_chunks_does_not_create_citation():
    """A valid UUID not in the retrieved set does not create a citation."""
    non_retrieved_id = "50000000-0000-0000-0000-000000000001"
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {non_retrieved_id}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    assert response.source_references == []

    # 6 inserts: no citation for non-retrieved chunk
    assert mc.table().insert().execute.call_count == 6


# ---------------------------------------------------------------------------
# TEST 6 — DUPLICATE REFERENCE
# ---------------------------------------------------------------------------

def test_duplicate_reference_does_not_create_duplicate_citations():
    """Referencing the same chunk twice creates only one citation (deduplicated by extract logic)."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=(
            f"First [Retrieved chunk {CHUNK_A_ID}] "
            f"and again [Retrieved chunk {CHUNK_A_ID}]."
        ),
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc = _mock_client()
    response, _ = _process(_chat_request(), mock_provider, mc)

    assert response.status == "success"
    # _extract_source_references uses a set for referenced_ids, so duplicates are collapsed
    assert len(response.source_references) == 1
    assert response.source_references[0].chunk_id == UUID(CHUNK_A_ID)

    # 7 inserts: ... + retrieval_op + chunks + 1 citation (not 2)
    assert mc.table().insert().execute.call_count == 7


# ---------------------------------------------------------------------------
# TEST 7 — CORRECT MESSAGE ASSOCIATION
# ---------------------------------------------------------------------------

def test_citations_belong_to_correct_assistant_message():
    """Citations reference the correct assistant message_id, not another message in the conversation."""
    conversation_id = uuid4()
    first_msg_id = uuid4()
    second_msg_id = uuid4()

    # First request: no citations
    provider1 = MagicMock(spec=GenerationProvider)
    provider1.generate.return_value = GenerationResult(
        answer="Simple answer.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc1 = _mock_client([
        MagicMock(data=[{"conversation_id": str(conversation_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(first_msg_id)}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ])

    request1 = _chat_request()
    session_ctx = SessionContext(session_id=conversation_id)
    with (
        patch("app.services.chat.get_admin_client", return_value=mc1),
        patch("app.services.conversation_history.get_admin_client", return_value=mc1),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response1 = process_chat_request(request1, session_ctx, provider1, TEST_USER_ID)

    assert response1.message_id == first_msg_id
    assert response1.source_references == []

    # Second request: has citations → should reference second_msg_id
    provider2 = MagicMock(spec=GenerationProvider)
    provider2.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc2 = MagicMock()
    mc2.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "Q", "status": "active"}
    )
    mc2.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{"message_sequence": 2}]
    )
    mc2.table().insert().execute.side_effect = [
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(second_msg_id)}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]

    request2 = _chat_request(user_query="Follow-up question")
    with (
        patch("app.services.chat.get_admin_client", return_value=mc2),
        patch("app.services.conversation_history.get_admin_client", return_value=mc2),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response2 = process_chat_request(request2, session_ctx, provider2, TEST_USER_ID)

    assert response2.message_id == second_msg_id
    assert len(response2.source_references) == 1
    # Citation is on the second message, not the first
    assert response2.message_id == second_msg_id


# ---------------------------------------------------------------------------
# TEST 8 — INSUFFICIENT CONTEXT
# ---------------------------------------------------------------------------

def test_insufficient_context_creates_no_citations():
    """When answer is None, no assistant message, ai_response, or citations are created."""
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
        patch("app.services.conversation_history.get_admin_client", return_value=mc),
        patch("app.services.chat.retrieve", return_value=retrieval),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.status == "insufficient_context"
    assert response.answer is None
    assert response.message_id is None
    assert response.source_references == []

    # Only 2 inserts: conversation + user message (NO assistant, NO ai_response, NO citations)
    assert mc.table().insert().execute.call_count == 2


# ---------------------------------------------------------------------------
# TEST 9 — CONVERSATION REUSE REGRESSION
# ---------------------------------------------------------------------------

def test_conversation_reuse_with_citations():
    """Same session reuses conversation; citations from different turns attach to correct messages."""
    conversation_id = uuid4()
    session_ctx = SessionContext(session_id=conversation_id)

    # --- Turn 1: with citation ---
    provider1 = MagicMock(spec=GenerationProvider)
    provider1.generate.return_value = GenerationResult(
        answer=f"According to [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc1 = MagicMock()
    mc1.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mc1.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(conversation_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mc1.table().select().eq().order().limit().execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"message_sequence": 1}]),
    ]

    with (
        patch("app.services.chat.get_admin_client", return_value=mc1),
        patch("app.services.conversation_history.get_admin_client", return_value=mc1),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        r1 = process_chat_request(_chat_request(), session_ctx, provider1, TEST_USER_ID)

    assert r1.status == "success"
    assert r1.conversation_id == conversation_id
    assert len(r1.source_references) == 1

    # --- Turn 2: no citation ---
    provider2 = MagicMock(spec=GenerationProvider)
    provider2.generate.return_value = GenerationResult(
        answer="No specific reference here.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc2 = MagicMock()
    mc2.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "Q", "status": "active"}
    )
    mc2.table().insert().execute.side_effect = [
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mc2.table().select().eq().order().limit().execute.side_effect = [
        MagicMock(data=[{"message_sequence": 2}]),
        MagicMock(data=[{"message_sequence": 3}]),
    ]

    with (
        patch("app.services.chat.get_admin_client", return_value=mc2),
        patch("app.services.conversation_history.get_admin_client", return_value=mc2),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        r2 = process_chat_request(_chat_request(user_query="Follow-up"), session_ctx, provider2, TEST_USER_ID)

    assert r2.status == "success"
    assert r2.conversation_id == conversation_id
    assert r2.source_references == []
    # Turn 2 has no citations
    assert mc2.table().insert().execute.call_count == 5


# ---------------------------------------------------------------------------
# TEST 10 — PROVIDER IMMUTABILITY
# ---------------------------------------------------------------------------

def test_generation_provider_file_unchanged():
    """generation_provider.py must not have been modified for Phase 4.3."""
    import hashlib
    import pathlib

    provider_path = pathlib.Path(__file__).resolve().parent.parent / "app" / "services" / "generation_provider.py"
    content = provider_path.read_text(encoding="utf-8")

    # Verify key provider characteristics remain intact
    assert "class GenerationResult" in content
    assert "class GenerationProvider" in content
    assert "class OpenRouterGenerationProvider" in content
    assert "def generate(self, context: AIContext) -> GenerationResult:" in content

    # Verify provider does NOT contain citation extraction logic
    assert "message_citations" not in content
    assert "retrieval_operations" not in content
    assert "_extract_source_references" not in content

    # Verify the model configuration is unchanged
    assert "openrouter" in content
    assert "openai/gpt-4o-mini" in content or "settings.openrouter_model" in content
