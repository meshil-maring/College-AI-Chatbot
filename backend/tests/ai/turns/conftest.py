"""Fictional recoverable requests and receipts."""

from uuid import UUID

import pytest

from app.schemas.ai.chat import ChatRequest, ChatResponse
from app.schemas.ai.session import SessionContext
from ..resource_scope.conftest import flow

ACTOR = '10000000-0000-0000-0000-000000000001'
TENANT = '20000000-0000-0000-0000-000000000001'
TURN = '30000000-0000-0000-0000-000000000009'
CONVERSATION = '40000000-0000-0000-0000-000000000001'
TOKEN = '50000000-0000-0000-0000-000000000009'


@pytest.fixture
def turn_request():
    return ChatRequest(user_query='Explain the hostel rules', institution_id=TENANT,
        turn_id=TURN, session_id=CONVERSATION)


@pytest.fixture
def session():
    return SessionContext(session_id=CONVERSATION)


@pytest.fixture
def reply():
    return ChatResponse(answer='A supported answer.', status='success', session_id=CONVERSATION,
        conversation_id=CONVERSATION, message_id=TOKEN, model_used=None, metadata={})


def receipt(state, reply=None):
    return {'turn_id': TURN, 'conversation_id': CONVERSATION, 'state': state,
        'retryable': state == 'failed', 'retry_after_seconds': 0,
        'request': {'turn_id': TURN, 'user_query': 'Explain the hostel rules',
            'institution_id': TENANT, 'session_id': CONVERSATION, 'conversation_id': CONVERSATION},
        'response': reply.model_dump(mode='json') if reply else None,
        **({'worker_token': TOKEN, 'user_sequence': 1} if state == 'claimed' else {})}
