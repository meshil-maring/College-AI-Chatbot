from .support import (
    CHUNK_A_ID,
    CHUNK_A_TEXT,
    GenerationProvider,
    GenerationResult,
    MagicMock,
    SessionContext,
    TEST_USER_ID,
    UUID,
    _chat_request,
    _retrieval_chunks,
    override_auth_dependency,
    patch,
    process_chat_request,
    uuid4,
)

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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response = process_chat_request(
            _chat_request(), SessionContext(session_id=uuid4()), mock_provider, TEST_USER_ID
        )

    assert len(response.source_references) == 1
    ref = response.source_references[0]
    assert ref.chunk_id == UUID(CHUNK_A_ID)
    assert ref.quote == CHUNK_A_TEXT
