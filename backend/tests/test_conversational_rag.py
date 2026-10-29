"""Conversational RAG integration tests.

Verifies that a follow-up question is interpreted into a standalone retrieval
query, that the rewritten query reaches vector retrieval, that the final
generation prompt carries the interpreted intent (and no source metadata),
and that dev diagnostics are attached.
"""

from unittest.mock import MagicMock, patch

import pytest
from tests.ai.policy_fixtures import isolated_policy

from app.config import settings
from app.schemas.ai.generation import AIContext
from app.schemas.knowledge.retrieval import RetrievalRequest
from app.services.ai.generation_provider import GenerationResult


from tests.ai.rag_support import (
    CHUNK_A_ID,
    REWRITTEN_FOLLOW_UP,
    _chat_request,
    _history,
    _retrieval_response,
    _run,
)


# ---------------------------------------------------------------------------
# Rewritten query reaches retrieval
# ---------------------------------------------------------------------------


def test_follow_up_uses_rewritten_query_for_retrieval():
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(
        answer="Girls standard room: Rs. 48,000/year.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )

    with (
        patch("app.services.ai.chat.rewrite_query", return_value=REWRITTEN_FOLLOW_UP),
        patch(
            "app.services.ai.chat.retrieve", return_value=_retrieval_response()
        ) as mock_retrieve,
    ):
        response, _ = _run(_chat_request(), _history(), provider)

    mock_retrieve.assert_called_once()
    called_request: RetrievalRequest = mock_retrieve.call_args[0][0]
    assert called_request.query == REWRITTEN_FOLLOW_UP
    assert called_request.top_k == settings.retrieval_top_k

    provider.generate.assert_called_once()
    called_context: AIContext = provider.generate.call_args[0][0]
    assert called_context.user_question == "what about for girl?"
    assert called_context.retrieval_query == REWRITTEN_FOLLOW_UP
    assert len(called_context.conversation_history) == 2
    assert response.answer == "Girls standard room: Rs. 48,000/year."


def test_first_question_uses_original_query_for_retrieval():
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(
        answer="Rs. 48,000/year.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
    )
    query = "What is the annual hostel fee for a standard room?"
    with patch(
        "app.services.ai.chat.retrieve", return_value=_retrieval_response()
    ) as mock_retrieve:
        response, _ = _run(_chat_request(user_query=query), [], provider)

    called_request: RetrievalRequest = mock_retrieve.call_args[0][0]
    assert called_request.query == query
    assert response.answer == "Rs. 48,000/year."


def test_real_rewriter_rewrites_follow_up_in_flow():
    def generate(context: AIContext):
        if not context.retrieved_knowledge:
            return GenerationResult(answer=REWRITTEN_FOLLOW_UP)
        return GenerationResult(
            answer="Girls standard room: Rs. 48,000/year. Security deposit: Rs. 5,000.",
            source_references=[],
            status="success",
            model_used="openai/gpt-4o-mini",
        )

    provider = MagicMock()
    provider.generate.side_effect = generate

    with patch(
        "app.services.ai.chat.retrieve", return_value=_retrieval_response()
    ) as mock_retrieve:
        response, _ = _run(_chat_request(), _history(), provider)

    assert provider.generate.call_count == 2
    called_request: RetrievalRequest = mock_retrieve.call_args[0][0]
    assert called_request.query == REWRITTEN_FOLLOW_UP
    assert "Girls standard room" in response.answer


# ---------------------------------------------------------------------------
# Prompt construction: interpreted intent present, source metadata absent
# ---------------------------------------------------------------------------


def test_interpreted_question_appears_in_final_prompt_without_metadata():
    from app.services.ai.generation_provider import _build_user_content

    provider = MagicMock()
    captured: dict = {}

    def generate(context: AIContext):
        captured["context"] = context
        return GenerationResult(
            answer="Girls standard room: Rs. 48,000/year.",
            source_references=[],
            status="success",
            model_used="openai/gpt-4o-mini",
        )

    provider.generate.side_effect = generate

    with (
        patch("app.services.ai.chat.rewrite_query", return_value=REWRITTEN_FOLLOW_UP),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_response()),
    ):
        _run(_chat_request(), _history(), provider)

    user_content = _build_user_content(captured["context"])
    assert "what about for girl?" in user_content
    assert "Interpreted question:" in user_content
    assert REWRITTEN_FOLLOW_UP in user_content
    # source metadata (uuids, scores, section labels) no longer reaches the LLM
    assert "Metadata:" not in user_content
    assert "similarity_score" not in user_content
    assert "section" not in user_content.lower()


# ---------------------------------------------------------------------------
# Diagnostics / observability
# ---------------------------------------------------------------------------


def test_dev_diagnostics_attach_to_generation_metadata(monkeypatch):
    monkeypatch.setattr(settings, "debug", True)
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(
        answer="Girls standard room: Rs. 48,000/year.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={"usage": {"prompt_tokens": 640, "completion_tokens": 30}},
    )
    with (
        patch("app.services.ai.chat.rewrite_query", return_value=REWRITTEN_FOLLOW_UP),
        patch("app.services.ai.chat.retrieve", return_value=_retrieval_response()),
    ):
        response, _ = _run(_chat_request(), _history(), provider)

    diagnostics = response.metadata["diagnostics"]
    assert diagnostics["original_query"] == "what about for girl?"
    assert diagnostics["rewritten_query"] == REWRITTEN_FOLLOW_UP
    assert diagnostics["retrieved_chunk_count"] == 1
    assert diagnostics["retrieved_chunk_ids"] == [CHUNK_A_ID]
    assert diagnostics["retrieved_scores"] == [0.82]
    assert diagnostics["final_input_token_count"] == 640
    assert diagnostics["output_token_count"] == 30
    assert diagnostics["final_context_token_count"] > 0


def test_standalone_question_diagnostics_rewritten_query_is_none(monkeypatch):
    monkeypatch.setattr(settings, "debug", True)
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(
        answer="Rs. 48,000/year.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={"usage": {"prompt_tokens": 400, "completion_tokens": 20}},
    )
    query = "What is the annual hostel fee for a standard room?"
    with patch("app.services.ai.chat.retrieve", return_value=_retrieval_response()):
        response, _ = _run(_chat_request(user_query=query), [], provider)

    diagnostics = response.metadata["diagnostics"]
    assert diagnostics["original_query"] == query
    assert diagnostics["rewritten_query"] is None


@pytest.mark.parametrize(
    "query",
    [
        "Hello",
        "How are you?",
        "Tell me a joke",
        "What is Python?",
        "Explain recursion.",
    ],
)
def test_casual_and_general_questions_skip_college_retrieval(query):
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(
        answer="A direct response.",
        source_references=[],
        status="success",
    )

    with patch("app.services.ai.chat.retrieve") as retrieve:
        response, _ = _run(_chat_request(user_query=query), [], provider)

    retrieve.assert_not_called()
    provider.generate.assert_called_once()
    context: AIContext = provider.generate.call_args.args[0]
    assert context.retrieved_knowledge == []
    assert response.answer == "A direct response."


def test_identity_and_ambiguous_questions_skip_retrieval_and_generation():
    for query, expected in (
        ("Which LLM are you using?", "college chatbot"),
        ("What about attendance?", "Are you asking"),
    ):
        provider = MagicMock()
        with patch("app.services.ai.chat.retrieve") as retrieve:
            response, _ = _run(_chat_request(user_query=query), [], provider)

        retrieve.assert_not_called()
        provider.generate.assert_not_called()
        assert response.status == "success"
        assert expected.casefold() in response.answer.casefold()
