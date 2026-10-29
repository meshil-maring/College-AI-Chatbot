"""Safe owner-only status and retry contract for one durable chat turn."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.ai.chat import AuthenticatedChatRequest, ChatResponse


class ChatTurnStatus(BaseModel):
    turn_id: UUID
    conversation_id: UUID
    state: Literal['processing', 'failed', 'completed']
    retryable: bool
    retry_after_seconds: int = Field(ge=0)
    request: AuthenticatedChatRequest
    response: ChatResponse | None = None
