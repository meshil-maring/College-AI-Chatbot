from .support import (
    ATTENDANCE_CHUNK_ID,
    ATTENDANCE_TEXT,
    ChatRequest,
    GenerationProvider,
    GenerationResult,
    INSTITUTION_ID,
    MagicMock,
    RetrievalResponse,
    RetrievalResult,
    SessionContext,
    TEST_USER_ID,
    UUID,
    override_auth_dependency,
    patch,
    process_chat_request,
    uuid4,
)

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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=mock_retrieval_response) as mock_retrieve,
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=mock_retrieval_response) as mock_retrieve,
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    mock_retrieve.assert_called_once()
    mock_provider.generate.assert_called_once()
    assert response.status == "success"
    assert response.answer == "A minimum attendance of 75% is mandatory for end-semester exams."
    assert response.session_id == session_context.session_id
