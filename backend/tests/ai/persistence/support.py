"""Shared fixtures for persistence regression checks."""

from uuid import UUID, uuid4

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.ai.chat import ChatRequest, ChatResponse

from app.schemas.knowledge.retrieval import RetrievalResponse, RetrievalResult

from app.schemas.ai.session import SessionContext

from app.services.ai.chat import _persist_in_background, process_chat_request

from app.services.ai.generation_provider import GenerationProvider, GenerationResult

@pytest.fixture(autouse=True)
def _sync_background_persistence(monkeypatch):
    """Run post-generation persistence synchronously for deterministic asserts.

    ``process_chat_request`` fires the AI-response / retrieval / citation
    writes on a daemon thread so live requests do not block on DB writes.
    These Phase 4.2 tests assert exact insert counts and row authorship
    immediately after the request returns, so the thread launch is replaced
    with a direct call to the same worker function (which resolves its own
    client via the patched ``get_admin_client``).
    """
    monkeypatch.setattr(
        "app.services.ai.chat._start_background_persistence",
        lambda **kwargs: _persist_in_background(**kwargs),
    )

INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"

CHUNK_ID = "30000000-0000-0000-0000-000000000151"

TEST_USER_ID = uuid4()

def _mock_retrieval_response() -> RetrievalResponse:
    return RetrievalResponse(
        results=[
            RetrievalResult(
                chunk_id=UUID(CHUNK_ID),
                text="Mandatory attendance is 75%.",
                similarity_score=0.9,
            )
        ]
    )

def _mock_generation_result(answer: str = "Test answer") -> GenerationResult:
    """Create a mock generation result with usage metadata."""
    return GenerationResult(
        answer=answer,
        source_references=[],
        status="success",
        model_used="openai/gpt-4o-mini",
        metadata={
            "provider": "openrouter",
            "usage": {
                "prompt_tokens": 150,
                "completion_tokens": 50,
            },
        },
    )
