"""The narrow recovery boundary pins actor and tenant and omits worker tokens."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app import main
from app.api.ai import chat_turns
from app.core.security import get_current_user
from .conftest import ACTOR, TENANT, TURN, receipt


def test_recovery_uses_the_authorized_identity_and_safe_projection(monkeypatch, reply):
    status = {**receipt('completed', reply), 'worker_token': 'must-stay-private', 'attempts': 2}
    read = MagicMock(return_value=status)
    user = {'user_id': ACTOR, 'institution_id': TENANT, 'roles': ['admin']}
    main.app.dependency_overrides[get_current_user] = lambda: user
    main.app.dependency_overrides[chat_turns._CHAT] = lambda: user
    monkeypatch.setattr(chat_turns, 'read', read)
    try:
        response = TestClient(main.app).get('/api/v1/generation/turns/' + TURN)
    finally:
        main.app.dependency_overrides.clear()
    assert response.status_code == 200
    assert read.call_args.args[0] is user
    assert str(read.call_args.args[1]) == TURN
    assert 'worker_token' not in response.text
    assert 'attempts' not in response.json()


def test_turn_ids_require_a_stable_conversation_and_no_internal_controls():
    from pydantic import ValidationError
    from app.schemas.ai.chat import AuthenticatedChatRequest
    import pytest

    with pytest.raises(ValidationError, match='stable session'):
        AuthenticatedChatRequest(user_query='Hello', institution_id=TENANT, turn_id=TURN)
    with pytest.raises(ValidationError, match='Extra inputs'):
        AuthenticatedChatRequest(user_query='Hello', institution_id=TENANT, session_id=TURN,
            turn_id=TURN, worker_token='forged')
