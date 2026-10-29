"""Persistence: conversations."""

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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    assert response.conversation_id == conversation_id


def test_conversation_ownership_verification_rejects_unauthorized() -> None:
    """Another user's conversation is indistinguishable from a missing one."""
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        try:
            process_chat_request(request, session_context, mock_provider, TEST_USER_ID)
            assert False, "Expected AppError with 404"
        except Exception as e:
            assert str(e) == "Conversation not found"
            assert hasattr(e, "status_code") and e.status_code == 404


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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_mock_retrieval_response()),
    ):
        response = process_chat_request(request, session_context, mock_provider, TEST_USER_ID)

    # Both session_id and conversation_id should match
    assert response.session_id == session_id
    assert response.conversation_id == session_id
