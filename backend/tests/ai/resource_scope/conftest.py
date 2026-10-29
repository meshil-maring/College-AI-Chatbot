"""Scoped-chat orchestration fixtures; SQL authorization has disposable tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.schemas.ai.chat import ChatRequest
from app.schemas.ai.session import SessionContext
from app.schemas.knowledge.retrieval import RetrievalResponse, RetrievalResult
from app.services.ai import chat
from app.services.ai.chat_support import resource_scope
from app.services.ai.generation_provider import GenerationResult

ACTOR = '10000000-0000-0000-0000-000000000001'
TENANT = '20000000-0000-0000-0000-000000000001'
SOURCE = '30000000-0000-0000-0000-000000000001'
OTHER = '30000000-0000-0000-0000-000000000002'
CONVERSATION = '40000000-0000-0000-0000-000000000001'
CHUNK = '50000000-0000-0000-0000-000000000001'


@pytest.fixture
def flow(monkeypatch):
    client = MagicMock()
    context = {'knowledge_source_id': SOURCE, 'institution_id': TENANT,
               'title': 'Library handbook', 'available': True, 'policy_version': 3}
    state = SimpleNamespace(conversation=None, messages=[], policy={
        'institution_id': TENANT, 'sources': {SOURCE: 3}, 'versions': {}})
    read = MagicMock(return_value=context)
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(answer='Borrowing is limited to two books.', status='success')
    retrieve = MagicMock(return_value=RetrievalResponse(results=[RetrievalResult(
        chunk_id=CHUNK, text='Students may borrow two books.', similarity_score=0.9)]))

    def create(_client, data, *, conversation_id):
        state.conversation = {'conversation_id': str(conversation_id), 'user_id': str(data.user_id),
            'knowledge_source_id': str(data.knowledge_source_id) if data.knowledge_source_id else None,
            'resource_institution_id': str(data.resource_institution_id) if data.resource_institution_id else None}
        return state.conversation

    def message(_client, data):
        state.messages.append(data)
        return {'message_id': CHUNK}

    monkeypatch.setattr(chat, 'get_admin_client', lambda: client)
    monkeypatch.setattr(chat, 'get_conversation', lambda *_: state.conversation)
    monkeypatch.setattr(chat, 'create_conversation', create)
    monkeypatch.setattr(chat, 'create_message', message)
    monkeypatch.setattr(chat, 'get_next_message_sequence', lambda *_: len(state.messages) + 1)
    monkeypatch.setattr(chat, 'get_conversation_messages', lambda *_args, **_kwargs: [])
    monkeypatch.setattr(chat, '_start_background_persistence', MagicMock())
    monkeypatch.setattr(chat, 'rewrite_query', lambda query, *_: query)
    monkeypatch.setattr(chat, 'retrieve', retrieve)
    monkeypatch.setattr(chat, 'snapshot', lambda *_: state.policy)
    current = MagicMock()
    monkeypatch.setattr(chat, 'require_current', current)
    monkeypatch.setattr(resource_scope, 'read_context', read)

    def run(question='Summarize this resource', selected=SOURCE, tenant=TENANT):
        request = ChatRequest(user_query=question, institution_id=tenant, resource_id=selected)
        response = chat.process_chat_request(request, SessionContext(session_id=CONVERSATION), provider, UUID(ACTOR))
        return response

    return SimpleNamespace(state=state, read=read, provider=provider, retrieve=retrieve,
        current=current, run=run, context=context)
