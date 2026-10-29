"""The keyed path reuses its saved question and commits the answer atomically."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.schemas.ai.chat import ChatRequest
from app.services.ai import chat
from .conftest import ACTOR, CONVERSATION, TENANT, TURN
from ..resource_scope.conftest import SOURCE


def test_keyed_turn_never_duplicates_the_user_message_or_starts_background_storage(flow, monkeypatch, session):
    request = ChatRequest(user_query='Summarize this resource', institution_id=TENANT,
        session_id=CONVERSATION, conversation_id=CONVERSATION, resource_id=SOURCE, turn_id=TURN)
    pending = SimpleNamespace(message_type='user', content_text=request.user_query, message_sequence=1, knowledge_policy=None)
    monkeypatch.setattr(chat, 'get_conversation_messages', lambda *_args, **_kwargs: [pending])
    complete = MagicMock(side_effect=lambda _client, _request, _actor, _turn, response, *_args, **_kwargs: response)
    monkeypatch.setattr(chat, 'complete_turn', complete)

    result = chat.process_chat_request(request, session, flow.provider, ACTOR,
        turn={'worker_token': 'fictional', 'user_sequence': 1})

    assert result.answer == 'Borrowing is limited to two books.'
    assert flow.state.messages == []
    chat._start_background_persistence.assert_not_called()
    complete.assert_called_once()
    assert flow.provider.generate.call_args.args[0].conversation_history == []
    assert complete.call_args.kwargs['chunks']
    assert flow.current.call_count == 2
