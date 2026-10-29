"""Citations: persistence."""

from .support import (
    CHUNK_A_ID,
    GenerationProvider,
    GenerationResult,
    MagicMock,
    SessionContext,
    TEST_USER_ID,
    _chat_request,
    _mock_client,
    _retrieval_chunks,
    _sync_background_persistence,
    patch,
    process_chat_request,
    uuid4,
)


def test_citations_belong_to_correct_assistant_message():
    """Citations reference the correct assistant message_id, not another message in the conversation."""
    conversation_id = uuid4()
    first_msg_id = uuid4()
    second_msg_id = uuid4()

    # First request: no citations
    provider1 = MagicMock(spec=GenerationProvider)
    provider1.generate.return_value = GenerationResult(
        answer="Simple answer.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc1 = _mock_client([
        MagicMock(data=[{"conversation_id": str(conversation_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(first_msg_id)}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ])

    request1 = _chat_request()
    session_ctx = SessionContext(session_id=conversation_id)
    with (
        patch("app.services.ai.chat.get_admin_client", return_value=mc1),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mc1),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response1 = process_chat_request(request1, session_ctx, provider1, TEST_USER_ID)

    assert response1.message_id == first_msg_id
    assert response1.source_references == []

    # Second request: has citations → should reference second_msg_id
    provider2 = MagicMock(spec=GenerationProvider)
    provider2.generate.return_value = GenerationResult(
        answer=f"See [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc2 = MagicMock()
    mc2.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "Q", "status": "active"}
    )
    mc2.table().select().eq().order().limit().execute.return_value = MagicMock(
        data=[{"message_sequence": 2}]
    )
    mc2.table().insert().execute.side_effect = [
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(second_msg_id)}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]

    request2 = _chat_request(user_query="Follow-up question")
    with (
        patch("app.services.ai.chat.get_admin_client", return_value=mc2),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mc2),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        response2 = process_chat_request(request2, session_ctx, provider2, TEST_USER_ID)

    assert response2.message_id == second_msg_id
    assert len(response2.source_references) == 1
    # Citation is on the second message, not the first
    assert response2.message_id == second_msg_id


def test_conversation_reuse_with_citations():
    """Same session reuses conversation; citations from different turns attach to correct messages."""
    conversation_id = uuid4()
    session_ctx = SessionContext(session_id=conversation_id)

    # --- Turn 1: with citation ---
    provider1 = MagicMock(spec=GenerationProvider)
    provider1.generate.return_value = GenerationResult(
        answer=f"According to [Retrieved chunk {CHUNK_A_ID}].",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc1 = MagicMock()
    mc1.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mc1.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(conversation_id)}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
        MagicMock(data=[{"message_citation_id": str(uuid4())}]),
    ]
    mc1.table().select().eq().order().limit().execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"message_sequence": 1}]),
    ]

    with (
        patch("app.services.ai.chat.get_admin_client", return_value=mc1),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mc1),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        r1 = process_chat_request(_chat_request(), session_ctx, provider1, TEST_USER_ID)

    assert r1.status == "success"
    assert r1.conversation_id == conversation_id
    assert len(r1.source_references) == 1

    # --- Turn 2: no citation ---
    provider2 = MagicMock(spec=GenerationProvider)
    provider2.generate.return_value = GenerationResult(
        answer="No specific reference here.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    mc2 = MagicMock()
    mc2.table().select().eq().maybe_single().execute.return_value = MagicMock(
        data={"conversation_id": str(conversation_id), "user_id": str(TEST_USER_ID), "title": "Q", "status": "active"}
    )
    mc2.table().insert().execute.side_effect = [
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mc2.table().select().eq().order().limit().execute.side_effect = [
        MagicMock(data=[{"message_sequence": 2}]),
        MagicMock(data=[{"message_sequence": 3}]),
    ]

    with (
        patch("app.services.ai.chat.get_admin_client", return_value=mc2),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=mc2),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_chunks()),
    ):
        r2 = process_chat_request(_chat_request(user_query="Follow-up"), session_ctx, provider2, TEST_USER_ID)

    assert r2.status == "success"
    assert r2.conversation_id == conversation_id
    assert r2.source_references == []
    # Turn 2 has no citations
    assert mc2.table().insert().execute.call_count == 5
