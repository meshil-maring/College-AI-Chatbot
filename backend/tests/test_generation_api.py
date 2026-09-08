"""Focused tests for the real chat request boundary."""

from uuid import UUID, uuid4
from unittest.mock import MagicMock, patch
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.generation import AIContext, RetrievedChunk
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.chat import process_chat_request
from app.services.generation_provider import GenerationProvider, GenerationResult


client = TestClient(app, raise_server_exceptions=False)
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
ATTENDANCE_CHUNK_ID = "30000000-0000-0000-0000-000000001510"
ATTENDANCE_TEXT = (
    "A minimum attendance of 75% is mandatory for eligibility to take the regular end-semester examination."
)
TEST_USER_ID = uuid4()


def _mock_get_current_user():
    """Mock authentication to return a test user."""
    return {"user_id": str(TEST_USER_ID), "auth_user_id": str(uuid4()), "email": "test@example.com"}


@pytest.fixture(autouse=True)
def override_auth_dependency():
    """Override get_current_user dependency for generation API tests, clean up after."""
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _payload(**overrides: object) -> dict:
    payload = {
        "user_query": "What are the admissions requirements?",
        "institution_id": INSTITUTION_ID,
    }
    payload.update(overrides)
    return payload


def _response(session_id: UUID, conversation_id: UUID | None = None, message_id: UUID | None = None) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        conversation_id=conversation_id or session_id,
        message_id=message_id or uuid4(),
        status="insufficient_context",
        model_used="test/model",
    )


def test_new_chat_generates_and_returns_uuid4() -> None:
    with patch(
        "app.main.process_chat_request",
        side_effect=lambda request, context, provider, user_id: _response(context.session_id),
    ):
        response = client.post("/api/v1/generation/chat", json=_payload())

    assert response.status_code == 200
    session_id = UUID(response.json()["session_id"])
    assert session_id.version == 4


def test_existing_session_id_is_preserved_and_propagated() -> None:
    session_id = uuid4()
    captured = {}

    def process(request, context, provider, user_id):
        captured["session_id"] = context.session_id
        return _response(context.session_id)

    with patch("app.main.process_chat_request", side_effect=process):
        response = client.post(
            "/api/v1/generation/chat",
            json=_payload(session_id=str(session_id)),
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == str(session_id)
    assert captured["session_id"] == session_id


def test_invalid_session_id_uses_fastapi_validation() -> None:
    with patch("app.main.process_chat_request") as process:
        response = client.post(
            "/api/v1/generation/chat",
            json=_payload(session_id="not-a-uuid"),
        )

    assert response.status_code == 422
    process.assert_not_called()


def test_chat_boundary_does_not_persist_records() -> None:
    with (
        patch(
            "app.main.process_chat_request",
            side_effect=lambda request, context, provider, user_id: _response(context.session_id),
        ),
        patch("app.db.supabase.get_admin_client") as get_admin_client,
    ):
        response = client.post("/api/v1/generation/chat", json=_payload())

    assert response.status_code == 200
    get_admin_client.assert_not_called()


def test_retrieval_invocation_propagates_query_and_scope() -> None:
    """Test 1: Mock retrieve(), send ChatRequest with query and scope, verify retrieve called with correct parameters."""
    knowledge_source_id = uuid4()
    document_id = uuid4()
    document_version_id = uuid4()
    processing_run_id = uuid4()

    request = ChatRequest(
        user_query="What is the attendance policy?",
        institution_id=UUID(INSTITUTION_ID),
        knowledge_source_id=knowledge_source_id,
        document_id=document_id,
        document_version_id=document_version_id,
        processing_run_id=processing_run_id,
        model_name="custom/model",
    )
    session_context = SessionContext(session_id=uuid4())

    retrieval_result = RetrievalResult(
        chunk_id=UUID(ATTENDANCE_CHUNK_ID),
        document_id=document_id,
        document_version_id=document_version_id,
        text=ATTENDANCE_TEXT,
        similarity_score=0.92,
        metadata={"section": "Attendance", "processing_run_id": str(processing_run_id)},
    )
    mock_retrieval_response = RetrievalResponse(results=[retrieval_result])

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="Attendance of 75% is required.",
        source_references=[],
        status="success",
        model_used="custom/model",
    )

    mock_client = MagicMock()
    # First call to get_conversation returns None (new conversation)
    # Second call to get_conversation (from get_conversation_messages) returns conversation data
    conversation_data = {
        "conversation_id": str(session_context.session_id),
        "user_id": str(TEST_USER_ID),
        "title": "Test conversation",
        "status": "active",
    }
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),  # First call: conversation doesn't exist
        MagicMock(data=conversation_data),  # Second call: get_conversation_messages
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=mock_retrieval_response) as mock_retrieve,
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    mock_retrieve.assert_called_once()
    called_request: RetrievalRequest = mock_retrieve.call_args[0][0]
    assert called_request.query == "What is the attendance policy?"
    assert called_request.institution_id == UUID(INSTITUTION_ID)
    assert called_request.knowledge_source_id == knowledge_source_id
    assert called_request.document_id == document_id
    assert called_request.document_version_id == document_version_id
    assert called_request.processing_run_id == processing_run_id
    assert called_request.model_name == "custom/model"

    # Verify chunks reached the generation provider
    mock_provider.generate.assert_called_once()
    called_context: AIContext = mock_provider.generate.call_args[0][0]
    assert len(called_context.retrieved_knowledge) == 1
    chunk = called_context.retrieved_knowledge[0]
    assert isinstance(chunk, RetrievedChunk)
    assert chunk.chunk_id == UUID(ATTENDANCE_CHUNK_ID)
    assert chunk.text == ATTENDANCE_TEXT
    assert chunk.similarity_score == 0.92
    assert chunk.metadata == {"section": "Attendance", "processing_run_id": str(processing_run_id)}

    assert response.status == "success"
    assert response.session_id == session_context.session_id


def test_empty_retrieval_returns_insufficient_context_without_calling_provider() -> None:
    """Test 2: Mock retrieval returning 0 results, verify provider.generate not called, status is insufficient_context."""
    request = ChatRequest(
        user_query="What is the quantum computing curriculum?",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    mock_retrieval_response = RetrievalResponse(results=[])
    mock_provider = MagicMock(spec=GenerationProvider)

    mock_client = MagicMock()
    # First call to get_conversation returns None (new conversation)
    # Second call to get_conversation (from get_conversation_messages) returns conversation data
    conversation_data = {
        "conversation_id": str(session_context.session_id),
        "user_id": str(TEST_USER_ID),
        "title": "Test conversation",
        "status": "active",
    }
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),  # First call: conversation doesn't exist
        MagicMock(data=conversation_data),  # Second call: get_conversation_messages
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=mock_retrieval_response) as mock_retrieve,
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    mock_retrieve.assert_called_once()
    mock_provider.generate.assert_not_called()
    assert response.status == "insufficient_context"
    assert response.answer is None
    assert response.session_id == session_context.session_id


def test_successful_retrieval_reaches_generation_with_known_attendance_chunk() -> None:
    """Test 3: Mock retrieval with known attendance chunk, verify chunk reaches generation and response is returned."""
    request = ChatRequest(
        user_query="What attendance is needed for exams?",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    retrieval_result = RetrievalResult(
        chunk_id=UUID(ATTENDANCE_CHUNK_ID),
        text=ATTENDANCE_TEXT,
        similarity_score=0.95,
        metadata={"section": "Academic Regulations"},
    )
    mock_retrieval_response = RetrievalResponse(results=[retrieval_result])

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="A minimum attendance of 75% is mandatory for end-semester exams.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mock_client = MagicMock()
    # First call to get_conversation returns None (new conversation)
    # Second call to get_conversation (from get_conversation_messages) returns conversation data
    conversation_data = {
        "conversation_id": str(session_context.session_id),
        "user_id": str(TEST_USER_ID),
        "title": "Test conversation",
        "status": "active",
    }
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),  # First call: conversation doesn't exist
        MagicMock(data=conversation_data),  # Second call: get_conversation_messages
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=mock_retrieval_response) as mock_retrieve,
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    mock_retrieve.assert_called_once()
    mock_provider.generate.assert_called_once()
    assert response.status == "success"
    assert response.answer == "A minimum attendance of 75% is mandatory for end-semester exams."
    assert response.session_id == session_context.session_id


def test_caller_provided_chunks_bypass_retrieval() -> None:
    """Test compatibility: When retrieved_chunks are provided in ChatRequest, retrieve() is not invoked."""
    caller_chunk = RetrievedChunk(
        chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
        text="Pre-retrieved text.",
        similarity_score=0.88,
    )
    request = ChatRequest(
        user_query="Tell me about pre-retrieved info",
        institution_id=UUID(INSTITUTION_ID),
        retrieved_chunks=[caller_chunk],
    )
    session_context = SessionContext(session_id=uuid4())

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="Here is the answer based on pre-retrieved text.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mock_client = MagicMock()
    # First call to get_conversation returns None (new conversation)
    # Second call to get_conversation (from get_conversation_messages) returns conversation data
    conversation_data = {
        "conversation_id": str(session_context.session_id),
        "user_id": str(TEST_USER_ID),
        "title": "Test conversation",
        "status": "active",
    }
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),  # First call: conversation doesn't exist
        MagicMock(data=conversation_data),  # Second call: get_conversation_messages
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve") as mock_retrieve,
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    mock_retrieve.assert_not_called()
    mock_provider.generate.assert_called_once()
    assert response.status == "success"


# ---------------------------------------------------------------------------
# Source-reference extraction tests — chat orchestration layer
# ---------------------------------------------------------------------------

CHUNK_A_ID = "40000000-0000-0000-0000-000000000001"
CHUNK_B_ID = "40000000-0000-0000-0000-000000000002"
CHUNK_A_TEXT = "Admission requires a completed application form."
CHUNK_B_TEXT = "The deadline is June 30th."


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


def test_provider_does_not_populate_source_references():
    """Provider always returns source_references=[]; extraction is a chat-layer concern."""
    mock_provider = MagicMock(spec=GenerationProvider)
    # Simulate provider returning an answer with an explicit chunk reference
    mock_provider.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],  # provider never populates this
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response = process_chat_request(
            _chat_request(), SessionContext(session_id=uuid4()), mock_provider, TEST_USER_ID
        )

    # The chat layer populates source_references from explicit chunk references
    assert len(response.source_references) == 1
    assert response.source_references[0].chunk_id == UUID(CHUNK_A_ID)


def test_unannotated_answer_produces_empty_source_references():
    """An answer without explicit chunk references yields source_references=[]."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="The admission process is straightforward.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response = process_chat_request(
            _chat_request(), SessionContext(session_id=uuid4()), mock_provider, TEST_USER_ID
        )

    assert response.source_references == []


def test_explicit_chunk_reference_maps_to_retrieved_chunk():
    """An answer containing [Retrieved chunk <UUID>] maps to the matching retrieved chunk."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"According to [Retrieved chunk {CHUNK_A_ID}], a completed application is required.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response = process_chat_request(
            _chat_request(), SessionContext(session_id=uuid4()), mock_provider, TEST_USER_ID
        )

    assert len(response.source_references) == 1
    ref = response.source_references[0]
    assert ref.chunk_id == UUID(CHUNK_A_ID)
    assert ref.quote == CHUNK_A_TEXT


def test_multiple_explicit_references_produce_multiple_source_references():
    """An answer referencing two retrieved chunks produces two source references."""
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=(
            f"See [Retrieved chunk {CHUNK_A_ID}] and [Retrieved chunk {CHUNK_B_ID}]."
        ),
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response = process_chat_request(
            _chat_request(), SessionContext(session_id=uuid4()), mock_provider, TEST_USER_ID
        )

    assert len(response.source_references) == 2
    ref_ids = {r.chunk_id for r in response.source_references}
    assert ref_ids == {UUID(CHUNK_A_ID), UUID(CHUNK_B_ID)}


def test_non_matching_uuid_in_answer_is_not_cited():
    """A UUID in the answer that does not match any retrieved chunk is ignored."""
    fake_id = "50000000-0000-0000-0000-000000000001"
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer=f"Reference [Retrieved chunk {fake_id}] is not a retrieved chunk.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response = process_chat_request(
            _chat_request(), SessionContext(session_id=uuid4()), mock_provider, TEST_USER_ID
        )

    assert response.source_references == []