"""Deterministic intent hints for selecting the existing chat knowledge path."""

import re
from enum import StrEnum
from uuid import UUID

from app.schemas.ai.generation import AIContext, ConversationTurn
from app.services.ai.personalization import classify_personalization_question
from app.services.ai.chat_support.intent_patterns import (
    _IDENTITY_PATTERN,
    _HIDDEN_INSTRUCTIONS_PATTERN,
    _CASUAL_PATTERN,
    _GENERAL_KNOWLEDGE_PATTERN,
    _FOLLOW_UP_PATTERN,
    _PERSONAL_CONTEXT_ONLY_PATTERN,
    _PERSONAL_SELECTOR_PATTERN,
    _ADDITIONAL_PERSONAL_TOPIC_PATTERN,
    _PROCEDURE_PATTERN,
    _PRIVATE_OTHER_PERSON_PATTERN,
    _PRIVATE_TOPIC_PATTERN,
    _RESTRICTED_ACTION_PATTERN,
    _RESTRICTED_TARGET_PATTERN,
    _COLLEGE_TOPIC_PATTERN,
    _COLLEGE_POLICY_CUE_PATTERN,
    _COLLEGE_OWNERSHIP_PATTERN,
    _BARE_INSTITUTIONAL_TOPIC_PATTERN,
    DIRECT_SYSTEM_INSTRUCTIONS,
    DIRECT_GROUNDING_INSTRUCTIONS,
)


class ConversationIntent(StrEnum):
    CASUAL = "casual"
    GENERAL_KNOWLEDGE = "general_knowledge"
    AI_IDENTITY = "ai_identity"
    PUBLIC_COLLEGE_KNOWLEDGE = "public_college_knowledge"
    AUTHENTICATED_COLLEGE_KNOWLEDGE = "authenticated_college_knowledge"
    PERSONAL_DATA = "personal_data"
    RESTRICTED_ACTION = "restricted_action"
    AMBIGUOUS = "ambiguous"


def is_personal_data_request(message: str) -> bool:
    """Recognize personal data requests without granting access to that data."""
    if classify_personalization_question(message) is not None:
        return True
    return bool(
        _PERSONAL_SELECTOR_PATTERN.search(message)
        and _ADDITIONAL_PERSONAL_TOPIC_PATTERN.search(message)
        and not _PROCEDURE_PATTERN.search(message)
    )


def contextual_personalization_query(
    message: str, history: list[ConversationTurn]
) -> str | None:
    """Resolve an elliptical personal-data follow-up to a supported query."""
    if is_personal_data_request(message):
        return message
    if not _FOLLOW_UP_PATTERN.search(message):
        return None

    previous_user_message = next(
        (turn.content for turn in reversed(history) if turn.role == "user"),
        None,
    )
    if not previous_user_message or not is_personal_data_request(previous_user_message):
        return None

    candidate = f"my {message}"
    if is_personal_data_request(candidate):
        return candidate
    if _PERSONAL_CONTEXT_ONLY_PATTERN.search(message):
        return previous_user_message
    return None


def classify_conversation_intent(
    message: str,
    history: list[ConversationTurn] | None = None,
    *,
    authenticated: bool,
) -> ConversationIntent:
    """Return a conservative route hint; this function never authorizes access."""
    prior_turns = history or []
    if is_personal_data_request(message):
        return ConversationIntent.PERSONAL_DATA
    if _IDENTITY_PATTERN.search(message):
        return ConversationIntent.AI_IDENTITY
    if (
        _PRIVATE_OTHER_PERSON_PATTERN.search(message)
        and _PRIVATE_TOPIC_PATTERN.search(message)
    ) or (
        _RESTRICTED_ACTION_PATTERN.search(message)
        and _RESTRICTED_TARGET_PATTERN.search(message)
    ):
        return ConversationIntent.RESTRICTED_ACTION
    if _CASUAL_PATTERN.search(message):
        return ConversationIntent.CASUAL

    if _FOLLOW_UP_PATTERN.search(message):
        previous_user_message = next(
            (turn.content for turn in reversed(prior_turns) if turn.role == "user"),
            None,
        )
        if previous_user_message:
            previous_intent = classify_conversation_intent(
                previous_user_message,
                authenticated=authenticated,
            )
            if previous_intent in {
                ConversationIntent.PUBLIC_COLLEGE_KNOWLEDGE,
                ConversationIntent.AUTHENTICATED_COLLEGE_KNOWLEDGE,
            }:
                return (
                    ConversationIntent.AUTHENTICATED_COLLEGE_KNOWLEDGE
                    if authenticated
                    else ConversationIntent.PUBLIC_COLLEGE_KNOWLEDGE
                )
            if previous_intent == ConversationIntent.PERSONAL_DATA:
                if contextual_personalization_query(message, prior_turns) is not None:
                    return ConversationIntent.PERSONAL_DATA
                return ConversationIntent.AMBIGUOUS
            if previous_intent in {
                ConversationIntent.CASUAL,
                ConversationIntent.GENERAL_KNOWLEDGE,
                ConversationIntent.AI_IDENTITY,
            }:
                return ConversationIntent.GENERAL_KNOWLEDGE
        return ConversationIntent.AMBIGUOUS

    if _BARE_INSTITUTIONAL_TOPIC_PATTERN.search(message):
        return ConversationIntent.AMBIGUOUS
    if (
        _COLLEGE_TOPIC_PATTERN.search(message)
        or _COLLEGE_OWNERSHIP_PATTERN.search(message)
        or _COLLEGE_POLICY_CUE_PATTERN.search(message)
    ):
        return (
            ConversationIntent.AUTHENTICATED_COLLEGE_KNOWLEDGE
            if authenticated
            else ConversationIntent.PUBLIC_COLLEGE_KNOWLEDGE
        )
    if _GENERAL_KNOWLEDGE_PATTERN.search(message):
        return ConversationIntent.GENERAL_KNOWLEDGE
    return (
        ConversationIntent.AUTHENTICATED_COLLEGE_KNOWLEDGE
        if authenticated
        else ConversationIntent.PUBLIC_COLLEGE_KNOWLEDGE
    )


def direct_identity_response(message: str) -> str:
    """Give a safe role-based identity response without model/provider disclosure."""
    if _HIDDEN_INSTRUCTIONS_PATTERN.search(message):
        return (
            "I can’t provide hidden system or developer instructions. I can still "
            "explain what I can help with."
        )
    if re.search(r"(?i)\b(what can you do|how can you help)\b", message):
        return (
            "I’m the AI assistant built into this college chatbot. I can help "
            "with college information, learning, and general questions."
        )
    return (
        "I’m the AI assistant built into this college chatbot. I can help with "
        "college information, learning, and general questions."
    )


def direct_route_response(intent: ConversationIntent) -> str | None:
    """Return a deterministic response when generation or retrieval is unnecessary."""
    if intent == ConversationIntent.AMBIGUOUS:
        return (
            "Are you asking about the college’s public information or your own "
            "personal record?"
        )
    if intent == ConversationIntent.RESTRICTED_ACTION:
        return (
            "I can’t perform administrative changes through chat. Please use the "
            "appropriate authorized workflow; access is checked by the server."
        )
    if intent == ConversationIntent.PERSONAL_DATA:
        return (
            "I can’t access that personal record through this chat. Please use "
            "your account profile for identity details. Academic record services have been removed."
        )
    return None


def build_direct_context(
    message: str,
    history: list[ConversationTurn] | None = None,
    *,
    public: bool = False,
    institution_id: UUID | None = None,
    max_output_tokens: int | None = None,
) -> AIContext:
    """Build a provider context for a turn that deliberately skips college RAG."""
    return AIContext(
        system_instructions=DIRECT_SYSTEM_INSTRUCTIONS,
        user_question=message,
        model_name=None,
        retrieved_knowledge=[],
        grounding_instructions=DIRECT_GROUNDING_INSTRUCTIONS,
        conversation_history=history or [],
        public=public,
        institution_id=institution_id,
        max_output_tokens=max_output_tokens,
    )
