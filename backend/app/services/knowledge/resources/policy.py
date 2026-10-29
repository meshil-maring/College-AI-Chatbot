"""Persist and revalidate source policy provenance for every generated turn."""

from app.core.errors import AppError
from .operations import execute

REDACTED_MESSAGE = 'This part of the conversation is unavailable because source access changed. Start a new chat.'


def allowed(client, user_id, policy):
    if not isinstance(policy, dict):
        return False
    return execute('check_knowledge_policy', client=client, actor=str(user_id) if user_id else None, policy=policy) is True


def snapshot(client, user_id, institution_id, chunks, messages):
    inherited = {'sources': {}, 'versions': {}}
    for message in messages:
        policy = message.knowledge_policy
        if isinstance(policy, dict):
            if policy.get('institution_id') != str(institution_id):
                raise AppError('Conversation scope changed. Start a new chat.', 409, 'RESOURCE_CHANGED')
            for key in inherited:
                inherited[key].update(policy.get(key, {}))
    return execute('snapshot_knowledge_policy', client=client, actor=str(user_id) if user_id else None, tenant=str(institution_id),
        chunks=[str(chunk.chunk_id) for chunk in chunks], inherited=inherited)


def require_current(client, user_id, policy):
    if not allowed(client, user_id, policy):
        raise AppError('Source access changed while preparing the answer. Please ask again.', 409, 'RESOURCE_CHANGED')


def require_usable_history(messages):
    if any(message.content_text == REDACTED_MESSAGE and message.knowledge_policy is None for message in messages):
        raise AppError('Source access changed for this conversation. Start a new chat.', 409, 'CONVERSATION_ACCESS_CHANGED')
