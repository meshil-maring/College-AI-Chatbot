"""Claim before doing provider work; replay completed turns without regeneration."""

import logging
from uuid import UUID

from app.core.errors import AppError
from app.schemas.ai.chat import ChatResponse
from .operations import execute

logger = logging.getLogger(__name__)


def run(request, session_context, provider, user_id, *, current_user, process):
    if request.turn_id is None:
        return process(request, session_context, provider, user_id=user_id, current_user=current_user)
    conversation = request.conversation_id or request.session_id
    session_context = session_context.model_copy(update={'session_id': request.session_id or conversation})
    parameters = {'actor': str(user_id), 'tenant': str(request.institution_id), 'selected_turn': str(request.turn_id)}
    turn = execute('claim_chat_turn', **parameters, selected_conversation=str(conversation),
        selected_session=str(session_context.session_id), query=request.user_query,
        resource_id=str(request.resource_id) if request.resource_id else None)
    if turn['state'] == 'completed':
        return ChatResponse.model_validate(turn['response'])
    if turn['state'] != 'claimed':
        raise AppError('Your reply is still being prepared. Check its status before retrying.',
            409, 'CHAT_TURN_PENDING', headers={'Retry-After': '2'})
    request.conversation_id = UUID(turn['conversation_id'])
    try:
        return process(request, session_context, provider, user_id=user_id, current_user=current_user, turn=turn)
    except Exception:
        try:
            execute('fail_chat_turn', **parameters, token=turn['worker_token'])
        except Exception:
            # An uncertain completion can already be committed. Status recovery
            # remains authoritative; never regenerate or overwrite a receipt here.
            logger.warning('event=chat_turn_failure_unconfirmed')
        raise
