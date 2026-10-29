"""Safe errors and atomic storage for recoverable authenticated chat turns."""

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.ai import chat_turns
from app.schemas.ai.chat import ChatResponse


def execute(operation, *, client=None, **parameters):
    try:
        return chat_turns.call(client or get_admin_client(), operation, **parameters)
    except AppError:
        raise
    except Exception as failure:
        code = str(getattr(failure, 'code', ''))
        if code in {'42P01', '42703', '42883', 'PGRST202', 'PGRST204', 'PGRST205'}:
            raise AppError('Chat recovery is temporarily unavailable.', 503, 'CHAT_TURN_SCHEMA_UNAVAILABLE') from failure
        status, public_code, message = {
            'P0002': (404, 'CHAT_TURN_NOT_FOUND', 'Chat turn not found.'),
            '42501': (403, 'FORBIDDEN', 'Your access to this conversation changed.'),
            'PT409': (409, 'CHAT_TURN_BUSY', 'Recover the unfinished reply before sending another question.'),
            'PT410': (409, 'CHAT_TURN_REPLACED', 'A retry is already handling this reply. Check its status.'),
            '22023': (409, 'CHAT_TURN_CONFLICT', 'This turn identifier belongs to another request.'),
            '40001': (409, 'CHAT_TURN_CHANGED', 'This conversation changed. Check its saved reply.'),
        }.get(code, (500, 'CHAT_TURN_UNAVAILABLE', 'The chat request could not be confirmed.'))
        raise AppError(message, status, public_code) from failure


def read(user, turn_id):
    return execute('read_chat_turn', actor=str(user['user_id']), tenant=str(user['institution_id']), selected_turn=str(turn_id))


def complete(client, request, actor, turn, response, policy, *, chunks, retrieval_query, model_name, latency_ms):
    usage = response.usage
    result = execute('complete_chat_turn', client=client, actor=str(actor), tenant=str(request.institution_id),
        selected_turn=str(request.turn_id), token=turn['worker_token'],
        reply=response.model_dump(mode='json'), policy=policy,
        details={'retrieval_query': retrieval_query, 'model_name': model_name,
            'input_tokens': usage.input_tokens if usage else None, 'output_tokens': usage.output_tokens if usage else None,
            'latency_ms': latency_ms, 'chunks': [{'chunk_id': str(chunk.chunk_id), 'score': chunk.similarity_score} for chunk in chunks]})
    return ChatResponse.model_validate(result['response'])
