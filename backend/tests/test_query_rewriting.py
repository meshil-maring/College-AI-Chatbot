"""Tests for token-efficient conversational query interpretation."""

from unittest.mock import MagicMock

from app.schemas.generation import AIContext, ConversationTurn
from app.services.generation_provider import GenerationResult
from app.services.chat import _is_self_contained_question
from app.services.query_rewriting import (
    REWRITE_SYSTEM_INSTRUCTIONS,
    build_rewrite_context,
    compact_history,
    rewrite_query,
    should_rewrite,
)


def turn(role: str, content: str) -> ConversationTurn:
    return ConversationTurn(role=role, content=content)


def _provider(answer: str | None = None) -> MagicMock:
    provider = MagicMock()
    if answer is not None:
        provider.generate.return_value = GenerationResult(answer=answer)
    return provider


# ---------------------------------------------------------------------------
# should_rewrite
# ---------------------------------------------------------------------------


def test_no_history_is_not_rewritten():
    assert should_rewrite([]) is False


def test_user_only_history_is_not_rewritten():
    assert should_rewrite([turn("user", "hi")]) is False


def test_completed_exchange_is_rewritten():
    history = [turn("user", "q1"), turn("assistant", "a1")]
    assert should_rewrite(history) is True


# ---------------------------------------------------------------------------
# compact_history
# ---------------------------------------------------------------------------


def test_compact_empty_history():
    assert compact_history([], exchanges=2, max_chars=1000) == []


def test_compact_keeps_only_recent_exchanges():
    history = [
        turn("user", "u1"),
        turn("assistant", "a1"),
        turn("user", "u2"),
        turn("assistant", "a2"),
        turn("user", "u3"),
        turn("assistant", "a3"),
    ]
    compact = compact_history(history, exchanges=2, max_chars=1000)
    assert len(compact) == 4
    # most recent exchange is kept, order is chronological
    assert compact[-2:] == [turn("user", "u3"), turn("assistant", "a3")]
    assert compact[0].role == "user"


def test_compact_drops_orphan_leading_assistant():
    history = [
        turn("assistant", "orphan"),
        turn("user", "u2"),
        turn("assistant", "a2"),
    ]
    compact = compact_history(history, exchanges=2, max_chars=1000)
    assert compact[0].role == "user"


def test_compact_respects_char_budget():
    history = [
        turn("user", "u" * 300),
        turn("assistant", "a" * 300),
        turn("user", "b" * 300),
        turn("assistant", "c" * 300),
    ]
    compact = compact_history(history, exchanges=2, max_chars=500)
    total = sum(len(t.content) for t in compact)
    assert total <= 500
    # newest turn is preserved first
    assert compact[-1].content == "c" * 300
# ---------------------------------------------------------------------------
# build_rewrite_context
# ---------------------------------------------------------------------------


def test_rewrite_context_is_minimal():
    history = [turn("user", "q1"), turn("assistant", "a1")]
    context = build_rewrite_context("what about for girl?", history)
    assert isinstance(context, AIContext)
    assert context.user_question == "what about for girl?"
    assert context.retrieved_knowledge == []
    assert context.system_instructions == REWRITE_SYSTEM_INSTRUCTIONS
    assert context.conversation_history == history
    # compact prompt: single-sentence instruction, no grounding block
    assert len(context.system_instructions) < 500
    assert "authoritative" not in context.system_instructions
    assert "fabricate citations" not in context.system_instructions


# ---------------------------------------------------------------------------
# _is_self_contained_question — cheap heuristic rewrite gate
# ---------------------------------------------------------------------------


def test_self_contained_standalone_question_skips_rewrite():
    turns = [
        ConversationTurn(role="user", content="What is the hostel fee?"),
        ConversationTurn(role="assistant", content="Rs. 48,000/year."),
    ]
    assert (
        _is_self_contained_question(
            "How much is the hostel security deposit?", turns
        )
        is True
    )


def test_short_follow_up_requires_rewriter():
    turns = [
        ConversationTurn(role="user", content="What is the hostel fee?"),
        ConversationTurn(role="assistant", content="Rs. 48,000/year."),
    ]
    assert _is_self_contained_question("What about for girls?", turns) is False


def test_pronoun_follow_up_requires_rewriter():
    turns = [
        ConversationTurn(
            role="user", content="How much is the annual hostel fee?"
        ),
        ConversationTurn(role="assistant", content="Rs. 48,000/year."),
    ]
    assert (
        _is_self_contained_question("Is it refundable?", turns) is False
    )


def test_first_message_skips_rewrite():
    assert (
        _is_self_contained_question(
            "What is the minimum attendance required?", []
        )
        is True
    )


# ---------------------------------------------------------------------------
# rewrite_query (LLM-backed behavior — unchanged)
# ---------------------------------------------------------------------------


def test_rewrite_skipped_without_history():
    provider = _provider(answer="SHOULD NOT BE USED")
    result = rewrite_query("What is the hostel fee?", [], provider)
    assert result == "What is the hostel fee?"
    provider.generate.assert_not_called()


def test_rewrite_uses_provider_only_for_follow_up():
    provider = _provider(answer="What is the hostel fee and security deposit for girls?")
    history = [turn("user", "q1"), turn("assistant", "a1")]
    result = rewrite_query("what about for girl?", history, provider)
    assert result == "What is the hostel fee and security deposit for girls?"
    assert provider.generate.call_count == 1


def test_rewrite_returns_original_when_provider_keeps_wording():
    provider = _provider(answer="What is the hostel fee?")
    history = [turn("user", "q1"), turn("assistant", "a1")]
    result = rewrite_query("What is the hostel fee?", history, provider)
    assert result == "What is the hostel fee?"


def test_rewrite_falls_back_on_exception():
    provider = MagicMock()
    provider.generate.side_effect = RuntimeError("provider down")
    history = [turn("user", "q1"), turn("assistant", "a1")]
    assert rewrite_query("what about for girl?", history, provider) == "what about for girl?"


def test_rewrite_falls_back_on_empty_answer():
    provider = _provider(answer="   ")
    history = [turn("user", "q1"), turn("assistant", "a1")]
    assert rewrite_query("what about for girl?", history, provider) == "what about for girl?"


def test_rewrite_falls_back_on_none_answer():
    provider = _provider(answer=None)
    history = [turn("user", "q1"), turn("assistant", "a1")]
    assert rewrite_query("what about for girl?", history, provider) == "what about for girl?"


def test_rewrite_falls_back_on_non_string_answer():
    provider = MagicMock()
    provider.generate.return_value = MagicMock()  # .answer is a MagicMock
    history = [turn("user", "q1"), turn("assistant", "a1")]
    assert rewrite_query("what about for girl?", history, provider) == "what about for girl?"


def test_rewrite_context_carries_only_compact_history():
    provider = _provider(answer="rewritten")
    history = [
        turn("user", "old1"),
        turn("assistant", "old1a"),
        turn("user", "old2"),
        turn("assistant", "old2a"),
        turn("user", "recent"),
        turn("assistant", "recenta"),
    ]
    rewrite_query("follow up?", history, provider)
    called: AIContext = provider.generate.call_args[0][0]
    # only the latest 2 exchanges (4 turns) reach the rewriter
    assert [t.content for t in called.conversation_history] == [
        "old2",
        "old2a",
        "recent",
        "recenta",
    ]