"""Conversational query interpretation for retrieval (query rewriting).

A follow-up such as "what about for girl?" is rewritten into a standalone
retrieval question using only a small, recent slice of the conversation.
Rewriting is deliberately cheap:

  * it only runs when the conversation already contains a completed
    user/assistant exchange (a fresh first message is never rewritten),
  * it sends only the most recent ``rewrite_history_exchanges`` turns,
  * the total history excerpt is capped at ``rewrite_max_history_chars``,
  * the system instruction is a single concise sentence,
  * failures fall back to the original query so the chat request never
    depends on rewriting working.
"""

from app.config import settings
from app.schemas.generation import AIContext, ConversationTurn

REWRITE_SYSTEM_INSTRUCTIONS = (
    "Rewrite the user's follow-up message into a single standalone question "
    "that can be answered from a college knowledge base. Resolve references "
    "using only the conversation history. If the message is already a "
    "standalone question, return it unchanged. Output only the rewritten "
    "question, with no prefix, label, or explanation."
)


def should_rewrite(history: list[ConversationTurn]) -> bool:
    """Rewrite only when at least one completed exchange exists."""
    return any(turn.role == "assistant" for turn in history)


def compact_history(
    history: list[ConversationTurn],
    exchanges: int | None = None,
    max_chars: int | None = None,
) -> list[ConversationTurn]:
    """Keep only the most recent ``exchanges`` user/assistant pairs.

    A trailing orphaned assistant turn is dropped so the excerpt starts on a
    user message. Per-turn content is additionally truncated so the whole
    excerpt stays within ``max_chars`` characters.
    """
    exchanges = exchanges if exchanges is not None else settings.rewrite_history_exchanges
    max_chars = max_chars if max_chars is not None else settings.rewrite_max_history_chars

    if exchanges <= 0 or not history:
        return []

    turns = history[-exchanges * 2 :]
    if turns and turns[0].role == "assistant":
        turns = turns[1:]

    compact: list[ConversationTurn] = []
    budget = max_chars
    for turn in reversed(turns):
        if budget <= 0:
            break
        content = turn.content
        if len(content) > budget:
            content = content[:budget]
        compact.append(ConversationTurn(role=turn.role, content=content))
        budget -= len(content)
    compact.reverse()
    return compact


def build_rewrite_context(
    user_query: str,
    history: list[ConversationTurn],
) -> AIContext:
    """Build the minimal generation context used for query interpretation."""
    return AIContext(
        system_instructions=REWRITE_SYSTEM_INSTRUCTIONS,
        user_question=user_query,
        model_name=None,
        retrieved_knowledge=[],
        conversation_history=compact_history(history),
    )


def rewrite_query(
    user_query: str,
    history: list[ConversationTurn],
    provider,
) -> str:
    """Interpret ``user_query`` into a standalone retrieval query.

    Returns the rewritten question when interpretation happens, otherwise the
    original ``user_query``. Never raises: any provider failure falls back to
    the original question.
    """
    if not should_rewrite(history):
        return user_query

    try:
        result = provider.generate(build_rewrite_context(user_query, history))
    except Exception:
        return user_query

    if result is None or not isinstance(getattr(result, "answer", None), str):
        return user_query
    rewritten = result.answer.strip()
    if not rewritten or rewritten.lower() == user_query.lower():
        return user_query
    return rewritten