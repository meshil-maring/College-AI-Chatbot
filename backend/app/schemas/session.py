"""Contracts for request-scoped chatbot session identity."""

from uuid import UUID

from pydantic import BaseModel, Field


class SessionContextRequest(BaseModel):
    """Optional session identity supplied with a chat request."""

    session_id: UUID | None = Field(
        default=None,
        description="Existing chat session identifier, when continuing a session",
    )


class SessionContext(BaseModel):
    """Validated session identity carried through request processing."""

    session_id: UUID


class SessionContextResponse(BaseModel):
    """Session identity returned to the caller for request correlation."""

    session_id: UUID