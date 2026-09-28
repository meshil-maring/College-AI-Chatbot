"""HTTP contracts for the application chat boundary."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.chat_response import ChatUsage, StructuredSource
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
    sources: list[StructuredSource] = Field(default_factory=list)
    usage: ChatUsage | None = None


class PublicChatRequest(BaseModel):
    """Strict anonymous contract; no internal retrieval controls are accepted."""

    model_config = ConfigDict(extra="forbid")

    institution_code: str = Field(min_length=1, max_length=32)
    message: str = Field(min_length=1, max_length=4000)

    @field_validator("institution_code")
    @classmethod
    def normalize_institution_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("institution_code must not be empty")
        return normalized

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("message must not be empty")
        return normalized


class PublicSource(BaseModel):
    """Citation metadata safe for an anonymous user."""

    title: str | None = None
    section: str | None = None
    quote: str


class PublicChatResponse(BaseModel):
    """Public projection without IDs, model data, usage, or diagnostics."""

    answer: str | None = None
    status: str
    sources: list[PublicSource] = Field(default_factory=list)
