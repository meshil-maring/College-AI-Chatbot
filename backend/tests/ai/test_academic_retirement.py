"""Retired academic readers cannot be reached through authenticated chat."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
from tests.ai.policy_fixtures import isolated_policy

from app.schemas.ai.chat import ChatRequest
from app.schemas.ai.session import SessionContext
from app.services.ai import chat
from app.services.ai.personalization import classify_personalization_question


@pytest.mark.parametrize(
    "question",
    ["What is my attendance?", "Show my exam results", "What are my courses?"],
)
def test_personal_academic_queries_never_call_retrieval_or_generation(
    monkeypatch, question
):
    user_id, conversation_id, message_id = uuid4(), uuid4(), uuid4()
    monkeypatch.setattr(chat, "get_admin_client", lambda: object())
    monkeypatch.setattr(
        chat,
        "get_conversation",
        lambda *_: {
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
        },
    )
    monkeypatch.setattr(chat, "get_conversation_messages", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(chat, "get_next_message_sequence", lambda *_: 1)
    save = Mock(return_value={"message_id": str(message_id)})
    monkeypatch.setattr(chat, "create_message", save)
    monkeypatch.setattr(chat, "_start_background_persistence", Mock())
    retrieve, generate = Mock(), Mock()
    monkeypatch.setattr(chat, "retrieve", retrieve)
    monkeypatch.setattr(chat, "AIGenerationService", generate)
    response = chat.process_chat_request(
        ChatRequest(user_query=question, institution_id=uuid4()),
        SessionContext(session_id=conversation_id),
        Mock(),
        user_id,
        current_user={"user_id": str(user_id), "roles": ["student"]},
    )
    assert "Academic record services have been removed" in response.answer
    assert save.call_count == 2
    retrieve.assert_not_called()
    generate.assert_not_called()


def test_college_policy_questions_remain_general_knowledge():
    assert (
        classify_personalization_question("What attendance do I need for exams?")
        is None
    )
