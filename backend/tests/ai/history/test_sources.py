"""History citation restoration preserves ownership and current-policy redaction."""

from copy import deepcopy
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.core.errors import AppError
from app.services.ai import conversation_history as history
from app.services.ai.chat_support import history_sources
from app.services.knowledge.resources.policy import REDACTED_MESSAGE
from .support import FAKE_USER_A, FAKE_CLAIMS_A, _auth_header, _patch_auth, client

CONVERSATION = '20000000-0000-0000-0000-000000000001'
SOURCE = '40000000-0000-0000-0000-000000000001'
VERSION = '50000000-0000-0000-0000-000000000001'
CHUNK = '60000000-0000-0000-0000-000000000001'
CARD = {'chunk_id': CHUNK, 'quote': 'Fictional quoted evidence.', 'source_title': 'Handbook',
    'section': 'Library', 'relevance_score': 0.85}


@pytest.fixture
def stored(monkeypatch):
    conversation = {'conversation_id': CONVERSATION, 'user_id': FAKE_USER_A['user_id']}
    policy = {'institution_id': FAKE_USER_A['institution_id'], 'sources': {SOURCE: 2}, 'versions': {VERSION: SOURCE}}
    rows = [{'message_id': f'30000000-0000-0000-0000-{index:012}', 'conversation_id': CONVERSATION,
        'message_sequence': index, 'message_type': role, 'content_text': text,
        'created_at': '2026-10-29T00:00:00Z', 'knowledge_policy': deepcopy(policy) if role == 'assistant' else None}
        for index, (role, text) in enumerate([('user', 'Question'), ('assistant', 'Answer'),
            ('user', 'Follow-up'), ('assistant', 'Later answer')], 1)]
    reader = MagicMock(return_value={row['message_id']: {'available': True, 'sources': [CARD]}
        for row in rows if row['message_type'] == 'assistant'})
    monkeypatch.setattr(history_sources, 'read_history_sources', reader)
    monkeypatch.setattr(history, 'get_admin_client', MagicMock())
    monkeypatch.setattr(history, 'get_conversation', lambda *_: conversation)
    monkeypatch.setattr(history, 'list_messages_for_conversation', lambda *_: rows)
    monkeypatch.setattr(history, 'allowed', lambda *_: True)
    return conversation, rows, reader


def load():
    return history.get_conversation_messages(UUID(CONVERSATION), UUID(FAKE_USER_A['user_id']), include_sources=True)


def test_owner_gets_batched_typed_sources_without_internal_policy(stored):
    messages = load()
    assert messages[0].sources == []
    assert messages[1].model_dump(mode='json')['sources'] == [CARD]
    assert messages[3].model_dump(mode='json')['sources'] == [CARD]
    assert 'knowledge_policy' not in messages[1].model_dump()
    assert stored[2].call_count == 1
    assert [str(value) for value in stored[2].call_args.args[3]] == [stored[1][1]['message_id'], stored[1][3]['message_id']]


def test_http_history_projects_sources_and_keeps_provenance_private(stored):
    jwt_patch, db_patch = _patch_auth()
    with jwt_patch, db_patch:
        response = client.get(f'/api/v1/conversations/{CONVERSATION}/messages', headers=_auth_header(FAKE_CLAIMS_A))
    assert response.status_code == 200
    assert response.json()[1]['sources'] == [CARD]
    assert 'knowledge_policy' not in response.text
    assert 'provider' not in response.text and 'storage' not in response.text


def test_internal_generation_history_does_not_fetch_presentation_cards(stored):
    messages = history.get_conversation_messages(UUID(CONVERSATION), UUID(FAKE_USER_A['user_id']))
    assert len(messages) == 4 and all(message.sources == [] for message in messages)
    stored[2].assert_not_called()


def test_answers_without_saved_citations_get_no_invented_cards(stored):
    for projection in stored[2].return_value.values():
        projection['sources'] = []
    assert all(message.sources == [] for message in load())


def test_legacy_direct_answers_skip_the_citation_reader(stored):
    for row in stored[1]:
        if row['knowledge_policy']:
            row['knowledge_policy'].update(sources={}, versions={})
    assert len(load()) == 4
    stored[2].assert_not_called()


def test_wrong_owner_cannot_query_citations(stored):
    stored[0]['user_id'] = '10000000-0000-0000-0000-000000000099'
    with pytest.raises(AppError) as failure:
        load()
    assert failure.value.status_code == 404
    stored[2].assert_not_called()


def test_revoked_answer_and_dependent_tail_have_no_sources(stored, monkeypatch):
    monkeypatch.setattr(history, 'allowed', lambda *_: False)
    messages = load()
    assert len(messages) == 2 and messages[-1].content_text == REDACTED_MESSAGE
    assert messages[-1].sources == []
    stored[2].assert_not_called()


@pytest.mark.parametrize('scoped', [False, True])
def test_policy_change_during_citation_read_redacts_the_dependent_history(stored, monkeypatch, scoped):
    if scoped:
        stored[0].update(knowledge_source_id=SOURCE, resource_institution_id=FAKE_USER_A['institution_id'])
        monkeypatch.setattr(history, 'restored_context', lambda *_: {'available': True})
    stored[2].return_value[stored[1][1]['message_id']] = {'available': False, 'sources': []}
    messages = load()
    assert len(messages) == (1 if scoped else 2)
    assert messages[-1].content_text == REDACTED_MESSAGE and messages[-1].sources == []
    assert 'Handbook' not in ''.join(message.model_dump_json() for message in messages)


@pytest.mark.parametrize('failure', [RuntimeError('private database details'), None])
def test_failed_or_incomplete_citation_read_fails_closed(stored, failure):
    if failure:
        stored[2].side_effect = failure
    else:
        stored[2].return_value = {}
    with pytest.raises(AppError) as caught:
        load()
    assert caught.value.status_code == 503
    assert caught.value.code == 'HISTORY_SOURCES_UNAVAILABLE'
    assert 'private' not in caught.value.message
