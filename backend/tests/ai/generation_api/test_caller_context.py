from .support import (
    ChatRequest,
    GenerationProvider,
    GenerationResult,
    INSTITUTION_ID,
    MagicMock,
    RetrievedChunk,
    SessionContext,
    TEST_USER_ID,
    UUID,
    override_auth_dependency,
    patch,
    process_chat_request,
    uuid4,
)

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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve") as mock_retrieve,
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    mock_retrieve.assert_not_called()
    mock_provider.generate.assert_called_once()
    assert response.status == "success"


# ---------------------------------------------------------------------------
# Source-reference extraction tests — chat orchestration layer
# ---------------------------------------------------------------------------
