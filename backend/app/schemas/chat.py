"""HTTP contracts for the application chat boundary."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.generation import AIResponse, RetrievedChunk


class ChatRequest(BaseModel):
    """Request accepted by the real chat endpoint."""

    user_query: str
    session_id: UUID | None = None
    conversation_id: UUID | None = None
    institution_id: UUID
    knowledge_source_id: UUID | None = None
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    processing_run_id: UUID | None = None
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    model_name: str | None = None


class ChatResponse(AIResponse):
    """Generation response carrying the request-scoped session identity."""

    session_id: UUID
    conversation_id: UUID
    message_id: UUID | None