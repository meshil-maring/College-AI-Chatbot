"""Conversational RAG integration tests.

Verifies that a follow-up question is interpreted into a standalone retrieval
query, that the rewritten query reaches vector retrieval, that the final
generation prompt carries the interpreted intent (and no source metadata),
and that dev diagnostics are attached.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from unittest.mock import MagicMock, patch

from app.config import settings
from app.schemas.chat import ChatRequest
from app.schemas.conversation import MessageSummary
from app.schemas.generation import AIContext
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.chat import process_chat_request
from app.services.generation_provider import GenerationResult

TEST_USER_ID = uuid4()
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
CHUNK_A_ID = "40000000-0000-0000-0000-000000000701"
CHUNK_A_TEXT = (
    "Hostel Fee Structure: Boys Hostel - Standard Room 48000/year. "
    "Girls Hostel - Standard Room 48000/year. Security Deposit 5000 refundable."
)
REWRITTEN_FOLLOW_UP = "What is the hostel annual fee and security deposit for girls' standard room?"


def _summary(sequence: int, message_type: str, content: str) -> MessageSummary:
    return MessageSummary(
        message_id=uuid4(),
        conversation_id=uuid4(),
        message_sequence=sequence,
        message_type=message_type,
        content_text=content,
        created_at=datetime.now(timezone.utc),
    )


def _history() -> list[MessageSummary]:
    return [
        _summary(
            1,
            "user",
            "How much is the annual hostel fee for a standard room, and how much is the security deposit?",
        ),
        _summary(
            2,
            "assistant",
            "The annual hostel fee for a standard room is Rs. 48,000 and the security deposit is Rs. 5,000.",
        ),
    ]


def _mock_client() -> MagicMock:
    mc = MagicMock()
    mc.table().select().eq().maybe_single().execute.return_value = MagicMock(data=None)
    mc.table().insert().execute.side_effect = [
        MagicMock(data=[{"conversation_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"message_id": str(uuid4())}]),
        MagicMock(data=[{"ai_response_id": str(uuid4())}]),
        MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
        MagicMock(data=[{"chunk_id": str(uuid4())}]),
    ]
    mc.table().select().eq().order().limit().execute.side_effect = [
        MagicMock(data=[]),
        MagicMock(data=[{"message_sequence": 1}]),
    ]
    return mc


def _retrieval_response() -> RetrievalResponse:
    return RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=UUID(CHUNK_A_ID),
                text=CHUNK_A_TEXT,
                similarity_score=0.82,
                metadata={"section": "Hostel Fee Structure"},
            )
        ]
    )


def _chat_request(user_query: str = "what about for girl?") -> ChatRequest:
    return ChatRequest(user_query=user_query, institution_id=UUID(INSTITUTION_ID))


def _run(request: ChatRequest, history: list[MessageSummary], provider: MagicMock):
    session_context = SessionContext(session_id=uuid4())
    with (
        patch("app.services.chat.get_admin_client", return_value=_mock_client()),
        patch("app.services.conversation_history.get_admin_client", return_value=MagicMock()),
        patch("app.services.chat.get_conversation_messages", return_value=history),
    ):
        return process_chat_request(request, session_context, provider, TEST_USER_ID), session_context


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
        patch("app.services.chat.rewrite_query", return_value=REWRITTEN_FOLLOW_UP),
        patch("app.services.chat.retrieve", return_value=_retrieval_response()) as mock_retrieve,
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
    with patch("app.services.chat.retrieve", return_value=_retrieval_response()) as mock_retrieve:
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

    with patch("app.services.chat.retrieve", return_value=_retrieval_response()) as mock_retrieve:
        response, _ = _run(_chat_request(), _history(), provider)

    assert provider.generate.call_count == 2
    called_request: RetrievalRequest = mock_retrieve.call_args[0][0]
    assert called_request.query == REWRITTEN_FOLLOW_UP
    assert "Girls standard room" in response.answer


# ---------------------------------------------------------------------------
# Prompt construction: interpreted intent present, source metadata absent
# ---------------------------------------------------------------------------


def test_interpreted_question_appears_in_final_prompt_without_metadata():
    from app.services.generation_provider import _build_user_content

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
        patch("app.services.chat.rewrite_query", return_value=REWRITTEN_FOLLOW_UP),
        patch("app.services.chat.retrieve", return_value=_retrieval_response()),
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


def test_dev_diagnostics_attach_to_generation_metadata():
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(
        answer="Girls standard room: Rs. 48,000/year.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={"usage": {"prompt_tokens": 640, "completion_tokens": 30}},
    )
    with (
        patch("app.services.chat.rewrite_query", return_value=REWRITTEN_FOLLOW_UP),
        patch("app.services.chat.retrieve", return_value=_retrieval_response()),
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


def test_standalone_question_diagnostics_rewritten_query_is_none():
    provider = MagicMock()
    provider.generate.return_value = GenerationResult(
        answer="Rs. 48,000/year.",
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={"usage": {"prompt_tokens": 400, "completion_tokens": 20}},
    )
    query = "What is the annual hostel fee for a standard room?"
    with patch("app.services.chat.retrieve", return_value=_retrieval_response()):
        response, _ = _run(_chat_request(user_query=query), [], provider)

    diagnostics = response.metadata["diagnostics"]
    assert diagnostics["original_query"] == query
    assert diagnostics["rewritten_query"] is None
