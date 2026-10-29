"""Restore verified citation cards without trusting stored browser-facing receipts."""

from app.core.errors import AppError
from app.repositories.ai.message_citation import read_history_sources
from app.services.knowledge.resources.policy import REDACTED_MESSAGE


def restore_sources(client, actor, conversation, messages):
    candidates = [message for message in messages if message.message_type == 'assistant'
        and message.knowledge_policy and message.knowledge_policy.get('versions')]
    if not candidates:
        return messages
    candidate_ids = {message.message_id for message in candidates}
    try:
        restored = read_history_sources(client, actor, conversation['conversation_id'],
            [message.message_id for message in candidates])
        if not isinstance(restored, dict):
            raise ValueError('Invalid citation projection')
        result = []
        for message in messages:
            if message.message_id not in candidate_ids:
                result.append(message)
                continue
            item = restored.get(str(message.message_id))
            if not isinstance(item, dict) or not isinstance(item.get('sources'), list):
                raise ValueError('Missing citation projection')
            if item.get('available') is not True:
                redacted = message.model_copy(update={'content_text': REDACTED_MESSAGE,
                    'knowledge_policy': None, 'sources': []})
                # Resource questions can reveal restricted context as well.
                return [redacted] if conversation.get('knowledge_source_id') else [*result, redacted]
            result.append(type(message).model_validate({**message.model_dump(),
                'knowledge_policy': message.knowledge_policy, 'sources': item['sources']}))
        return result
    except AppError:
        raise
    except Exception as failure:
        code = str(getattr(failure, 'code', ''))
        if code == 'P0002':
            raise AppError('Conversation not found', 404, 'CONVERSATION_NOT_FOUND') from failure
        if code == '42501':
            raise AppError('Conversation access changed.', 403, 'FORBIDDEN') from failure
        raise AppError('Conversation sources are temporarily unavailable.', 503, 'HISTORY_SOURCES_UNAVAILABLE') from failure
