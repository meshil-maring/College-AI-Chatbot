"""History, in-flight changes and public corpus revalidation."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.services.ai import conversation_history
from app.services.knowledge.resources import policy, public_chat
from .conftest import ACTOR, TENANT, SOURCE, REVISION


def test_history_redacts_first_unauthorized_answer_and_its_followups(monkeypatch):
    rows = [
        {'message_id': REVISION, 'conversation_id': SOURCE, 'message_sequence': 1,
         'message_type': 'assistant', 'content_text': 'Private salary policy',
         'created_at': '2026-10-28T10:00:00Z', 'knowledge_policy': None},
        {'message_id': TENANT, 'conversation_id': SOURCE, 'message_sequence': 2,
         'message_type': 'user', 'content_text': 'Summarize that private policy', 'created_at': '2026-10-28T10:00:01Z'},
    ]
    monkeypatch.setattr(conversation_history, 'get_admin_client', MagicMock())
    monkeypatch.setattr(conversation_history, 'list_messages_for_conversation', lambda *_: rows)
    result = conversation_history.get_conversation_messages(UUID(SOURCE), UUID(ACTOR), {'user_id': ACTOR})
    assert len(result) == 1 and result[0].content_text == policy.REDACTED_MESSAGE
    assert 'salary' not in result[0].model_dump_json()
    with pytest.raises(AppError, match='Start a new chat'):
        policy.require_usable_history(result)


def test_snapshot_inherits_source_and_version_provenance(monkeypatch):
    execute = MagicMock(return_value={'sources': {}, 'versions': {}})
    monkeypatch.setattr(policy, 'execute', execute)
    previous = SimpleNamespace(knowledge_policy={'institution_id': TENANT,
        'sources': {SOURCE: 2}, 'versions': {REVISION: SOURCE}})
    policy.snapshot(object(), ACTOR, TENANT, [], [previous])
    assert execute.call_args.kwargs['inherited'] == {'sources': {SOURCE: 2}, 'versions': {REVISION: SOURCE}}


def test_inflight_revocation_prevents_delivery(monkeypatch):
    monkeypatch.setattr(policy, 'allowed', lambda *_: False)
    with pytest.raises(AppError) as failure:
        policy.require_current(object(), ACTOR, {'institution_id': TENANT, 'sources': {}, 'versions': {}})
    assert failure.value.status_code == 409


def test_public_corpus_change_prevents_delivery(monkeypatch):
    monkeypatch.setattr(public_chat, 'execute', MagicMock(side_effect=[{'fingerprint': 'before'}, {'fingerprint': 'after'}]))
    monkeypatch.setattr(public_chat.processor, 'process_public_request', lambda *_: object())
    with pytest.raises(AppError) as failure:
        public_chat.process_public_request(SimpleNamespace(institution_code='COLLEGE'), object(), object())
    assert failure.value.code == 'RESOURCE_CHANGED'


def test_public_adapter_preserves_the_generation_contract(monkeypatch):
    request = SimpleNamespace(institution_code='COLLEGE')
    context, provider, response = object(), object(), object()
    processor = MagicMock(return_value=response)
    monkeypatch.setattr(public_chat, 'execute', lambda *_args, **_kwargs: {'fingerprint': 'same'})
    monkeypatch.setattr(public_chat.processor, 'process_public_request', processor)
    assert public_chat.process_public_request(request, context, provider) is response
    processor.assert_called_once_with(request, context, provider)


def test_internal_policy_is_not_serialized_to_chat_history():
    from app.schemas.ai.conversation import MessageSummary

    message = MessageSummary(message_id=REVISION, conversation_id=SOURCE, message_sequence=1,
        message_type='assistant', content_text='Safe', created_at='2026-10-28T10:00:00Z',
        knowledge_policy={'institution_id': TENANT, 'sources': {SOURCE: 2}, 'versions': {}})
    assert 'knowledge_policy' not in message.model_dump()


def test_public_adapter_keeps_unknown_institution_error(monkeypatch):
    def missing(*_args, **_kwargs):
        raise AppError('Resource not found', 404, 'RESOURCE_NOT_FOUND')

    monkeypatch.setattr(public_chat, 'execute', missing)
    with pytest.raises(AppError) as failure:
        public_chat._snapshot('UNKNOWN')
    assert failure.value.code == 'INSTITUTION_NOT_FOUND'
