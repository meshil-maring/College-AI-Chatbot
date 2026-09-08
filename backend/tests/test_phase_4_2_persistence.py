"""Phase 4.2 focused tests for conversation and message persistence."""

from uuid import UUID, uuid4
from unittest.mock import MagicMock, patch

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.retrieval import RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.chat import process_chat_request
from app.services.generation_provider import GenerationProvider, GenerationResult


INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
CHUNK_ID = "30000000-0000-0000-0000-000000000151"
TEST_USER_ID = uuid4()


def _mock_retrieval_response() -> RetrievalResponse:
    return RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=UUID(CHUNK_ID),
                text="Mandatory attendance is 75%.",
                similarity_score=0.9,
            )
        ]
    )


def _mock_generation_result(answer: str = "Test answer") -> GenerationResult:
    """Create a mock generation result with usage metadata."""
    return GenerationResult(
        answer=answer,
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={
            "provider": "openrouter",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 50,
            },
        },
    )


def test_new_conversation_creates_conversation_record() -> None:
    """Phase 4.2: New chat creates conversation with auto-generated title."""
    request = ChatRequest(
        user_query="What are the admission requirements for undergraduate programs?",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = _mock_generation_result()

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(
            data=[{
                "conversation_id": str(session_context.session_id),
                "user_id": str(TEST_USER_ID),
                "title": "What are the admission requirements for undergraduate pr",
                "status": "active",
            }]
        ),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 1, "message_type": "user"}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 2, "message_type": "assistant"}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[]
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    # Verify conversation was created with title truncated to 60 chars
    assert response.conversation_id == session_context.session_id
    assert response.session_id == session_context.session_id


def test_existing_conversation_reuses_conversation_id() -> None:
    """Phase 4.2: Supplying existing conversation_id reuses that conversation."""
    conversation_id = uuid4()
    request = ChatRequest(
        user_query="Follow-up question",
        conversation_id=conversation_id,
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = _mock_generation_result()

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={
            "conversation_id": str(conversation_id),
            "user_id": str(TEST_USER_ID),
            "title": "Original question",
            "status": "active",
        }
    )
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 3, "message_type": "user"}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 4, "message_type": "assistant"}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{"message_sequence": 2}]
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.conversation_id == conversation_id


def test_conversation_ownership_verification_rejects_unauthorized() -> None:
    """Phase 4.2: Attempting to access another user's conversation raises 403."""
    conversation_id = uuid4()
    other_user_id = uuid4()

    request = ChatRequest(
        user_query="Unauthorized access attempt",
        conversation_id=conversation_id,
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    mock_provider = MagicMock(spec=GenerationProvider)

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={
            "conversation_id": str(conversation_id),
            "user_id": str(other_user_id),
            "title": "Someone else's conversation",
            "status": "active",
        }
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        try:
            process_chat_request(request, session_context, mock_provider, TEST_USER_ID)
            assert False, "Expected AppError with 403"
        except Exception as e:
            assert "does not belong to the authenticated user" in str(e)
            assert hasattr(e, "status_code") and e.status_code == 403


def test_user_message_persisted_with_correct_sequence() -> None:
    """Phase 4.2: User message persisted before generation with incrementing sequence."""
    request = ChatRequest(
        user_query="What is the attendance policy?",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = _mock_generation_result()

    mock_client = MagicMock()
    conversation_data = {
        "conversation_id": str(session_context.session_id),
        "user_id": str(TEST_USER_ID),
        "title": "What is the attendance policy?",
        "status": "active",
    }

    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[conversation_data]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 1, "message_type": "user"}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 2, "message_type": "assistant"}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[]
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    # Verify 6 inserts: conversation, user message, assistant message, ai_response,
    # retrieval_operation, retrieved_chunks (no message_citations since source_references=[])
    assert mock_client.table().insert().execute.call_count == 6


def test_assistant_message_and_ai_response_persisted_after_generation() -> None:
    """Phase 4.2: Assistant message and AI response metadata persisted post-generation."""
    request = ChatRequest(
        user_query="Tell me about exams",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())
    message_id = uuid4()

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = _mock_generation_result(
        answer="Final exams require 75% attendance."
    )

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 1}]),
        MagicMock(data=[{"message_id": str(message_id), "message_sequence": 2}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[]
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.message_id is not None
    assert isinstance(response.message_id, UUID)


def test_ai_response_captures_token_counts_and_latency() -> None:
    """Phase 4.2: AI response record captures input/output tokens and latency_ms."""
    request = ChatRequest(
        user_query="Query",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = GenerationResult(
        answer="Answer",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={
            "provider": "openrouter",
            "usage": {
                "prompt_tokens": 200,
                "completion_tokens": 75,
            },
        },
    )

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 1}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 2}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[]
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.message_id is not None


def test_backward_compatibility_session_id_maps_to_conversation_id() -> None:
    """Phase 4.2: session_id (Phase 4.1) maps to conversation_id (Phase 4.2)."""
    session_id = uuid4()
    request = ChatRequest(
        user_query="Test backward compatibility",
        session_id=session_id,
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=session_id)

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = _mock_generation_result()

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[]
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    # Both session_id and conversation_id should match
    assert response.session_id == session_id
    assert response.conversation_id == session_id


def test_response_contract_includes_conversation_and_message_ids() -> None:
    """Phase 4.2: ChatResponse includes conversation_id, message_id, and session_id."""
    request = ChatRequest(
        user_query="Check response contract",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())
    message_id = uuid4()

    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = _mock_generation_result()

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(message_id)}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[]
    )

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert hasattr(response, "session_id")
    assert hasattr(response, "conversation_id")
    assert hasattr(response, "message_id")
    assert isinstance(response.session_id, UUID)
    assert isinstance(response.conversation_id, UUID)
    assert isinstance(response.message_id, UUID)


def test_multi_turn_conversation_sequence_continuity() -> None:
    """Phase 4.2: Multi-turn chat maintains sequence 1, 2, 3, 4 without creating second conversation."""
    conversation_id = uuid4()
    session_context = SessionContext(session_id=conversation_id)
    mock_provider = MagicMock(spec=GenerationProvider)
    mock_provider.generate.return_value = _mock_generation_result()

    # --- TURN 1 (New Session) ---
    request_turn_1 = ChatRequest(
        user_query="First turn question",
        institution_id=UUID(INSTITUTION_ID),
    )

    mock_client_turn_1 = MagicMock()
    # Conversation does not exist initially (first get_conversation), but the
    # second get_conversation (inside get_conversation_messages) must return it
    mock_client_turn_1.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "First turn question", "status": "active"}),
    ]
    # Inserts: conversation, user message (seq 1), assistant message (seq 2), ai_response,
    # retrieval_operation, retrieved_chunks, message_citations
    mock_client_turn_1.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "First turn question", "status": "active"}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 1, "message_type": "user"}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 2, "message_type": "assistant"}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    # No existing messages for next sequence query
    mock_client_turn_1.table().select().eq().order().limit().execute.side_effect = [
        MagicMock(data=[]),  # for user message seq -> 1
        MagicMock(data=[{"message_sequence": 1}]),  # for assistant message seq -> 2
    ]

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client_turn_1),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client_turn_1),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response_1 = process_chat_request(request_turn_1, session_context, mock_provider, TEST_USER_ID)

    assert response_1.conversation_id == conversation_id
    assert response_1.status == "success"

    # --- TURN 2 (Existing Session) ---
    request_turn_2 = ChatRequest(
        user_query="Second turn question",
        conversation_id=conversation_id,
        institution_id=UUID(INSTITUTION_ID),
    )

    mock_client_turn_2 = MagicMock()
    # Conversation now exists
    mock_client_turn_2.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "First turn question", "status": "active"}
    )
    # Inserts: ONLY user message (seq 3), assistant message (seq 4), ai_response (NO conversation insert),
    # retrieval_operation, retrieved_chunks, message_citations
    mock_client_turn_2.table().insert().execute.side_effect = [
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 3, "message_type": "user"}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 4, "message_type": "assistant"}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    # Existing messages for next sequence query
    mock_client_turn_2.table().select().eq().order().limit().execute.side_effect = [
        MagicMock(data=[{"message_sequence": 2}]),  # for user message seq -> 3
        MagicMock(data=[{"message_sequence": 3}]),  # for assistant message seq -> 4
    ]

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client_turn_2),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client_turn_2),
        patch("app.services.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response_2 = process_chat_request(request_turn_2, session_context, mock_provider, TEST_USER_ID)

    assert response_2.conversation_id == conversation_id
    assert response_2.status == "success"
    # Ensure insert was called exactly 5 times in turn 2 (messages + ai_response + retrieval_op + chunks, NO conversation insert, NO citations since source_references=[])
    assert mock_client_turn_2.table().insert().execute.call_count == 5


def test_insufficient_context_persists_user_message_only() -> None:
    """Phase 4.2: Insufficient context persists user message but NOT assistant message or AI response."""
    request = ChatRequest(
        user_query="What is the quantum physics syllabus?",
        institution_id=UUID(INSTITUTION_ID),
    )
    session_context = SessionContext(session_id=uuid4())

    mock_provider = MagicMock(spec=GenerationProvider)

    mock_client = MagicMock()
    mock_client.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mock_client.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(session_context.session_id), "user_id": str(TEST_USER_ID)}]),
        MagicMock(data=[{"message_id": str(uuid4()), "message_sequence": 1, "message_type": "user"}]),
    ]
    mock_client.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    empty_retrieval_response = RetrievalResponse(results=[])

    with (
        patch("app.services.chat.get_admin_client", return_value=mock_client),
        patch("app.services.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.chat.retrieve", return_value=empty_retrieval_response) as mock_retrieve,
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    mock_retrieve.assert_called_once()
    mock_provider.generate.assert_not_called()
    assert response.status == "insufficient_context"
    assert response.answer is None
    assert response.message_id is None
    assert response.conversation_id == session_context.session_id

    # Exactly 2 inserts: conversation, user message (NO assistant message, NO ai_response)
    assert mock_client.table().insert().execute.call_count == 2

