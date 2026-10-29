"""Shared fixtures for citations regression checks."""

from uuid import UUID, uuid4

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.ai.chat import ChatRequest, ChatResponse

from app.schemas.ai.generation import SourceReference

from app.schemas.knowledge.retrieval import RetrievalResponse, RetrievalResult

from app.schemas.ai.session import SessionContext

from app.services.ai.chat import _persist_in_background, process_chat_request

from app.services.ai.generation_provider import GenerationProvider, GenerationResult

@pytest.fixture(autouse=True)
def _sync_background_persistence(monkeypatch):
    """Run post-generation persistence synchronously for deterministic asserts.

    ``process_chat_request`` fires the AI-response / retrieval / citation
    writes on a daemon thread so live requests do not block on DB writes.
    These tests assert exact insert call counts immediately after the request
    returns, so the thread launch is replaced with a direct call to the same
    worker function (which resolves its own client via the patched
    ``get_admin_client``).
    """
    monkeypatch.setattr(
        "app.services.ai.chat._start_background_persistence",
        lambda **kwargs: _persist_in_background(**kwargs),
    )

INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"

CHUNK_A_ID = "40000000-0000-0000-0000-000000000001"

CHUNK_B_ID = "40000000-0000-0000-0000-000000000002"

CHUNK_A_TEXT = "Admission requires a completed application form."

CHUNK_B_TEXT = "The deadline is June 30th."

TEST_USER_ID = uuid4()

def _retrieval_chunks():
    return RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=UUID(CHUNK_A_ID),
                text=CHUNK_A_TEXT,
                similarity_score=0.91,
                metadata={"section": "Admissions"},
            ),
            RetrievalResult(
                chunk_id=UUID(CHUNK_B_ID),
                text=CHUNK_B_TEXT,
                similarity_score=0.85,
                metadata={"section": "Deadlines"},
            ),
        ]
    )

def _chat_request(**overrides):
    base = {
        "user_query": "What are the admission requirements?",
        "institution_id": UUID(INSTITUTION_ID),
    }
    base.update(overrides)
    return ChatRequest(**base)

def _mock_client(insert_side_effects=None):
    """Build a mock Supabase client with standard lookup behavior."""
    mc = MagicMock()
    mc.table().select().eq().maybe_single().execute.side_effect = [
        MagicMock(data=None),
        MagicMock(data={"conversation_id": str(uuid4()), "user_id": str(TEST_USER_ID), "title": "Test", "status": "active"}),
    ]
    mc.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

    if insert_side_effects is not None:
        mc.table().insert().execute.side_effect = insert_side_effects
    else:
        mc.table().insert().execute.side_effect = [
            MagicMock(data=[{"conversation_id": str(uuid4())}]),
            MagicMock(data=[{"message_id": str(uuid4())}]),
            MagicMock(data=[{"message_id": str(uuid4())}]),
            MagicMock(data=[{"ai_response_id": str(uuid4())}]),
            MagicMock(data=[{"retrieval_operation_id": str(uuid4())}]),
            MagicMock(data=[{"chunk_id": str(uuid4())}]),
            MagicMock(data=[{"message_citation_id": str(uuid4())}]),
        ]
    return mc

def _process(request, provider, client, retrieval=None):
    """Run process_chat_request with mocked dependencies."""
    session_context = SessionContext(session_id=uuid4())
    with (
        patch("app.services.ai.chat.get_admin_client", return_value=client),
        patch("app.services.ai.conversation_history.get_admin_client", return_value=client),
        patch("app.services.ai.chat.retrieve", return_value=retrieval or _retrieval_chunks()),
    ):
        return process_chat_request(request, session_context, provider, TEST_USER_ID), session_context
