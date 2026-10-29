"""Unavailable resource context redacts titles, questions and dependent answers."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.services.ai import conversation_history as history
from app.services.ai.chat_support import resource_scope
from app.services.knowledge.resources.policy import REDACTED_MESSAGE
from .conftest import ACTOR, TENANT, SOURCE, OTHER, CONVERSATION, CHUNK


@pytest.fixture
def stored(monkeypatch):
    conversation = {'conversation_id': CONVERSATION, 'user_id': ACTOR, 'knowledge_source_id': SOURCE,
        'resource_institution_id': TENANT, 'title': 'Private handbook question', 'status': 'active',
        'created_at': '2026-10-29T00:00:00Z', 'updated_at': '2026-10-29T00:00:00Z'}
    rows = [{'message_id': CHUNK, 'conversation_id': CONVERSATION, 'message_sequence': 1,
        'message_type': 'user', 'content_text': 'Private question', 'created_at': '2026-10-29T00:00:00Z'},
        {'message_id': OTHER, 'conversation_id': CONVERSATION, 'message_sequence': 2,
        'message_type': 'assistant', 'content_text': 'Private answer', 'created_at': '2026-10-29T00:00:01Z',
        'knowledge_policy': {'institution_id': TENANT, 'sources': {SOURCE: 3}, 'versions': {}}}]
    monkeypatch.setattr(history, 'get_admin_client', MagicMock())
    monkeypatch.setattr(history, 'get_conversation', lambda *_: conversation)
    monkeypatch.setattr(history, 'list_conversations_for_user', lambda *_: [conversation])
    monkeypatch.setattr(history, 'list_messages_for_conversation', lambda *_: rows)
    monkeypatch.setattr(history, 'allowed', lambda *_: True)
    return conversation, rows


def test_available_history_restores_reader_safe_context(stored, monkeypatch):
    monkeypatch.setattr(resource_scope, 'read_context', lambda *_: {
        'knowledge_source_id': SOURCE, 'institution_id': TENANT, 'title': 'Handbook', 'policy_version': 3, 'available': True})
    summary = history.get_user_conversations(UUID(ACTOR))[0]
    assert summary.resource_context.title == 'Handbook'
    assert len(history.get_conversation_messages(UUID(CONVERSATION), UUID(ACTOR))) == 2


def test_revocation_redacts_entire_resource_history_and_summary(stored, monkeypatch):
    monkeypatch.setattr(resource_scope, 'read_context', MagicMock(side_effect=AppError('Denied', 404)))
    summary = history.get_user_conversations(UUID(ACTOR))[0]
    assert summary.title == 'Resource conversation unavailable'
    assert summary.resource_context.title is None and not summary.resource_context.available
    messages = history.get_conversation_messages(UUID(CONVERSATION), UUID(ACTOR))
    assert len(messages) == 1 and messages[0].content_text == REDACTED_MESSAGE
    assert 'Private' not in summary.model_dump_json() + messages[0].model_dump_json()


def test_mixed_resource_provenance_cannot_restore_even_if_each_source_is_readable(stored, monkeypatch):
    monkeypatch.setattr(resource_scope, 'read_context', lambda *_: {'knowledge_source_id': SOURCE, 'available': True})
    stored[1][1]['knowledge_policy']['sources'][OTHER] = 4
    messages = history.get_conversation_messages(UUID(CONVERSATION), UUID(ACTOR))
    assert messages[-1].content_text == REDACTED_MESSAGE


def test_context_transport_failure_does_not_silently_downgrade_to_general_chat(stored, monkeypatch):
    monkeypatch.setattr(resource_scope, 'read_context', MagicMock(side_effect=AppError('Unavailable', 503)))
    with pytest.raises(AppError) as failure:
        history.get_user_conversations(UUID(ACTOR))
    assert failure.value.status_code == 503
