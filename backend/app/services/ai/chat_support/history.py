"""Bounded conversation history and follow-up detection."""

import re
from app.schemas.ai.generation import ConversationTurn

_FOLLOW_UP_PATTERN = re.compile(
    r"(?i)\b(it|its|this|that|these|those|they|them|their|he|she|him|her|"
    r"same|also|else|other|another|above|former|latter|previous|"
    r"first|second|third|cheaper|bigger|smaller|higher|lower|better|more|less)\b"
    r"|\bwhat\s+about\b|\bhow\s+about\b|^\s*and\b|^\s*or\b|\bfor\s+(it|that|those|them)\b"
)

_NOUNISH_PATTERN = re.compile(r"[A-Za-z]{4,}")
_QUESTION_WORD_PATTERN = re.compile(
    r"(?i)\b(what|how|when|where|which|who|whom|whose|why|is|are|do|does|did|"
    r"can|could|should|will|would|have|has|had|may|might|shall)\b"
)


def _bounded_conversation_history(
    turns: list[ConversationTurn], max_messages: int
) -> list[ConversationTurn]:
    """Select the most recent bounded window of conversation turns.

    Keeps recent messages (never the oldest), caps total message count at
    ``max_messages``, and — when the budget forces trimming — starts the window
    at a user turn where practical so a user/assistant exchange is not split
    unnecessarily. Ordering stays chronological (message_sequence ASC).

    Fallback behavior: if ``max_messages <= 0`` or no messages exist, an empty
    list is returned (first-message / no-history behavior).
    """
    if max_messages <= 0 or not turns:
        return []
    if len(turns) <= max_messages:
        return turns
    window = turns[-max_messages:]
    if window and window[0].role == "assistant":
        # Trimming to the most recent max_messages would start mid-exchange;
        # drop the orphaned assistant turn so the window starts at a user turn.
        window = window[1:]
    return window


def _is_self_contained_question(user_query: str, history: list) -> bool:
    """Return True when the rewrite LLM call can be safely skipped.

    Skip conditions (all must hold):
      * there is prior conversation (otherwise ``rewrite_query`` already skips),
      * the message is at least 40 characters (elliptical fragments are short),
      * it contains a question word or verb signal AND noun-like content,
      * it carries no anaphoric / elliptical follow-up signals.

    The higher 40-char floor matters because a *new* topic question in an
    existing conversation (e.g. "How much is the hostel security deposit?"
    asked after an attendance question, 38 chars) still benefits from the
    rewriter confirming it is standalone. Short or reference-laden messages
    always go through the rewriter, preserving follow-up behavior exactly.
    """
    if not history:
        return True
    text = (user_query or "").strip()
    if len(text) < 40:
        return False
    if _FOLLOW_UP_PATTERN.search(text):
        return False
    if not _QUESTION_WORD_PATTERN.search(text):
        return False
    if not _NOUNISH_PATTERN.search(text):
        return False
    return True
