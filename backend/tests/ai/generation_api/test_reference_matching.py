from .support import (
    CHUNK_A_ID,
    CHUNK_B_ID,
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
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
        patch("app.services.ai.chat.get_admin_client", return_value=mock_client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mock_client),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response = process_chat_request(
            _chat_request(), SessionContext(session_id=uuid4()), mock_provider, TEST_USER_ID
        )

    assert response.source_references == []
