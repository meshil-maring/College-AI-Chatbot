from uuid import UUID, uuid4

from unittest.mock import MagicMock, patch

import pytest

from fastapi.testclient import TestClient

from app.main import app

from app.core.security import get_current_user

from app.schemas.ai.chat import ChatRequest, ChatResponse

from app.schemas.ai.generation import AIContext, RetrievedChunk

from app.schemas.knowledge.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult

from app.schemas.ai.session import SessionContext

from app.services.ai.chat import process_chat_request

from app.services.ai.generation_provider import GenerationProvider, GenerationResult

client = TestClient(app, raise_server_exceptions=False)

INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"

ATTENDANCE_CHUNK_ID = "30000000-0000-0000-0000-000000001510"

ATTENDANCE_TEXT = (
    "A minimum attendance of 75% is mandatory for eligibility to take the regular end-semester examination."
)

TEST_USER_ID = uuid4()

def _mock_get_current_user():
    """Mock authentication to return a test user."""
    return {
        "user_id": str(TEST_USER_ID),
        "auth_user_id": str(uuid4()),
        "email": "test@example.com",
        "roles": ["student"],
        "status": "active",
        "institution_id": INSTITUTION_ID,
        "role_assignments": [
            {
                "role": "student",
                "scope_type": "institution",
                "scope_id": INSTITUTION_ID,
                "scope_organization_id": None,
                "is_active": True,
            }
        ],
    }

@pytest.fixture(autouse=True)
def override_auth_dependency():
    """Override get_current_user dependency for generation API tests, clean up after."""
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    with patch(
        "app.services.auth.authorization.tenancy_repo.get_institution_by_id",
        return_value={
            "institution_id": INSTITUTION_ID,
            "status": "active",
            "is_active": True,
        },
    ):
        yield
    app.dependency_overrides.pop(get_current_user, None)

def _payload(**overrides: object) -> dict:
    payload = {
        "user_query": "What are the admissions requirements?",
        "institution_id": INSTITUTION_ID,
    }
    payload.update(overrides)
    return payload

def _response(session_id: UUID, conversation_id: UUID | None = None, message_id: UUID | None = None) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        conversation_id=conversation_id or session_id,
        message_id=message_id or uuid4(),
        status="insufficient_context",
        model_used="test/model",
    )

CHUNK_A_ID = "40000000-0000-0000-0000-000000000001"

CHUNK_B_ID = "40000000-0000-0000-0000-000000000002"

CHUNK_A_TEXT = "Admission requires a completed application form."

CHUNK_B_TEXT = "The deadline is June 30th."

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
