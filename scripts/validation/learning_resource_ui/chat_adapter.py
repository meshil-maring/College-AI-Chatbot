"""Use real chat/retrieval/history with deterministic local provider boundaries."""

from unittest.mock import patch

from app import main
from app.config import settings
from app.core.security import get_current_user
from app.api.ai.conversations import router as conversations_router
from app.api.ai.chat_turns import router as turns_router
from app.api.ai import chat_turns as turns_api
from app.services.ai.turns import operations as turn_operations
from app.core.errors import AppError
from app.services.ai import chat, conversation_history
from app.services.ai.generation_provider import GenerationResult
from app.services.knowledge import retrieval


class FictionalProvider:
    failed_questions = set()
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, context):
        if (context.retrieved_knowledge and context.user_question.startswith('Fictional retry test')
                and context.user_question not in self.failed_questions):
            self.failed_questions.add(context.user_question)
            raise AppError('Fictional transient provider failure', 503, 'AI_PROVIDER_TIMEOUT')
        if not context.retrieved_knowledge:
            return GenerationResult(answer=context.user_question)
        chunk = context.retrieved_knowledge[0]
        return GenerationResult(answer=f'Fictional resource answer: {chunk.text} [chunk_{chunk.chunk_id}]')


def connect(app, stack, adapter, current_user):
    app.include_router(main.generation_router, prefix='/api/v1')
    app.include_router(conversations_router, prefix='/api/v1')
    app.include_router(turns_router, prefix='/api/v1')
    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[main._INSTITUTION_CHAT] = current_user
    app.dependency_overrides[turns_api._CHAT] = current_user
    for module in (chat, conversation_history, retrieval, turn_operations):
        stack.enter_context(patch.object(module, 'get_admin_client', return_value=adapter))
    stack.enter_context(patch.object(main, 'OpenRouterGenerationProvider', FictionalProvider))
    stack.enter_context(patch.object(retrieval, 'embed_query', return_value=[1.0] + [0.0] * 1535))
    stack.enter_context(patch.object(settings, 'embedding_model', 'fixture-only'))
    # Legacy requests keep their old background boundary. Keyed turns exercise
    # actual atomic message/answer/retrieval/citation persistence in PostgreSQL.
    stack.enter_context(patch.object(chat, '_start_background_persistence', return_value=None))
