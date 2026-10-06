"""HTTP contracts for the application chat boundary."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.chat_response import ChatUsage, StructuredSource
from app.schemas.generation import AIResponse, RetrievedChunk
from app.config import settings


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


class AuthenticatedChatRequest(BaseModel):
    """Narrow HTTP contract for authenticated chat.

    Retrieval candidates, filters, provider/model choice, and output budgets
    are deliberately absent. They are internal controls and are reconstructed
    by the server after authentication and tenant resolution.
    """

    model_config = ConfigDict(extra="forbid")

    user_query: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None
    conversation_id: UUID | None = None
    institution_id: UUID

    @field_validator("user_query")
    @classmethod
    def normalize_user_query(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("user_query must not be empty")
        return normalized


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

    institution_code: str = Field(
        min_length=1,
        max_length=32,
        description="Public institution code (not an internal database ID).",
        examples=["COLLEGE001"],
    )
    message: str = Field(
        min_length=1,
        max_length=4000,
        description="One public, stateless chat message (maximum 4,000 characters).",
        examples=["What courses does the college offer?"],
    )

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
        if len(normalized) > settings.public_max_message_chars:
            raise ValueError("message exceeds the configured public limit")
        return normalized


class PublicSource(BaseModel):
    """Citation metadata safe for an anonymous user."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    section: str | None = None
    quote: str


class PublicChatResponse(BaseModel):
    """Public projection without IDs, model data, usage, or diagnostics."""

    model_config = ConfigDict(extra="forbid")

    answer: str | None = None
    status: Literal["success", "insufficient_context"]
    sources: list[PublicSource] = Field(default_factory=list)


class PublicAPIErrorDetail(BaseModel):
    """Sanitized request-validation detail exposed by the API error envelope."""

    loc: list[str | int]
    msg: str
    type: str


class PublicAPIErrorBody(BaseModel):
    """Stable, safe error body for the public endpoint."""

    code: str
    message: str
    details: list[PublicAPIErrorDetail] | None = None


class PublicAPIErrorResponse(BaseModel):
    """Documented public error envelope; never includes exception internals."""

    error: PublicAPIErrorBody
