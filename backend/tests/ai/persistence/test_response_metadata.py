"""Persistence: response metadata."""

from .support import (
    ChatRequest,
    GenerationProvider,
    GenerationResult,
    INSTITUTION_ID,
    MagicMock,
    RetrievalResponse,
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.message_id is not None


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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert hasattr(response, "session_id")
    assert hasattr(response, "conversation_id")
    assert hasattr(response, "message_id")
    assert isinstance(response.session_id, UUID)
    assert isinstance(response.conversation_id, UUID)
    assert isinstance(response.message_id, UUID)


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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=empty_retrieval_response) as mock_retrieve,
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
