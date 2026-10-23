"""Mocked institutional RAG conversation fixtures shared by integration tests."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

from app.schemas.ai.chat import ChatRequest
from app.schemas.ai.conversation import MessageSummary
from app.schemas.ai.session import SessionContext
from app.schemas.knowledge.retrieval import RetrievalResponse, RetrievalResult
from app.services.ai.chat import process_chat_request

TEST_USER_ID = uuid4()


INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"


CHUNK_A_ID = "40000000-0000-0000-0000-000000000701"


CHUNK_A_TEXT = (
    "Hostel Fee Structure: Boys Hostel - Standard Room 48000/year. "
    "Girls Hostel - Standard Room 48000/year. Security Deposit 5000 refundable."
)


REWRITTEN_FOLLOW_UP = (
    "What is the hostel annual fee and security deposit for girls' standard room?"
)


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
        patch("app.services.ai.chat.get_admin_client", return_value=_mock_client()),
        patch(
            "app.services.ai.conversation_history.get_admin_client",
            return_value=MagicMock(),
        ),
        patch("app.services.ai.chat.get_conversation_messages", return_value=history),
    ):
        return process_chat_request(
            request, session_context, provider, TEST_USER_ID
        ), session_context
