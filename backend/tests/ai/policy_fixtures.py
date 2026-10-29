"""Isolate policy transport in legacy generation/persistence unit tests.

These suites exercise generation and persistence rather than authentication.
The resource API/policy suite and real PostgreSQL runner cover authorization.
"""

import pytest


@pytest.fixture(autouse=True)
def isolated_policy(monkeypatch):
    from app.services.ai import chat, conversation_history

    monkeypatch.setattr(chat, 'snapshot', lambda _client, _user, institution, _chunks, _messages: {
        'institution_id': str(institution), 'sources': {}, 'versions': {},
    })
    monkeypatch.setattr(chat, 'require_current', lambda *_: None)
    monkeypatch.setattr(chat, 'require_usable_history', lambda *_: None)
    monkeypatch.setattr(conversation_history, 'allowed', lambda *_: True)
