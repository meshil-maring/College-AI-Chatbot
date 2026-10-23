"""Choose safe deterministic replies or the ordinary generation service."""

from app.services.ai.conversation_intent import (
    ConversationIntent,
    direct_identity_response,
    direct_route_response,
)
from app.services.ai.generation_provider import GenerationResult


def generate_chat_response(*, query, intent, context, provider, service_factory):
    answer = (
        direct_identity_response(query)
        if intent == ConversationIntent.AI_IDENTITY
        else direct_route_response(intent)
    )
    if answer is not None:
        return GenerationResult(answer=answer, source_references=[], status="success")
    return service_factory(provider).generate(
        context,
        allow_empty_context=intent
        in {ConversationIntent.CASUAL, ConversationIntent.GENERAL_KNOWLEDGE},
    )
