"""Persistence: messages."""

from .support import (
    ChatRequest,
    GenerationProvider,
    INSTITUTION_ID,
    MagicMock,
    SessionContext,
    TEST_USER_ID,
    UUID,
    _mock_generation_result,
    _mock_retrieval_response,
    _sync_background_persistence,
    patch,
    process_chat_request,
    uuid4,
)


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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.message_id is not None
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client_turn_1),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client_turn_1),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client_turn_2),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client_turn_2),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response_2 = process_chat_request(request_turn_2, session_context, mock_provider, TEST_USER_ID)

    assert response_2.conversation_id == conversation_id
    assert response_2.status == "success"
    # Ensure insert was called exactly 5 times in turn 2 (messages + ai_response + retrieval_op + chunks, NO conversation insert, NO citations since source_references=[])
    assert mock_client_turn_2.table().insert().execute.call_count == 5
