"""Keep legacy provider fakes independent of the new corpus snapshot RPC."""

import pytest


@pytest.fixture(autouse=True)
def isolated_corpus_snapshot(monkeypatch):
    from app.services.knowledge.resources import public_chat

    monkeypatch.setattr(public_chat, 'execute', lambda *_args, **_kwargs: {
        'institution_id': 'fixture', 'fingerprint': 'unchanged',
    })
