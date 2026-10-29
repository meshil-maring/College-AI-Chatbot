from .support import (
    AIContext,
    ATTENDANCE_CHUNK_ID,
    ATTENDANCE_TEXT,
    ChatRequest,
    GenerationProvider,
    GenerationResult,
    INSTITUTION_ID,
    MagicMock,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievedChunk,
    SessionContext,
    TEST_USER_ID,
    UUID,
    override_auth_dependency,
    patch,
    process_chat_request,
    uuid4,
)

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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=mock_retrieval_response) as mock_retrieve,
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
