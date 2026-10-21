"""Domain schemas for conversation persistence."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""

    user_id: UUID
    title: str | None = None
    status: str = "active"


class Conversation(BaseModel):
    """Schema representing a persisted conversation."""

    conversation_id: UUID
    user_id: UUID
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    """Schema for creating a new message."""

    conversation_id: UUID
    message_sequence: int
    message_type: str  # 'user' | 'assistant'
    content_text: str


class Message(BaseModel):
    """Schema representing a persisted message."""

    message_id: UUID
    conversation_id: UUID
    message_sequence: int
    message_type: str
    content_text: str
    created_at: datetime


class AIResponseCreate(BaseModel):
    """Schema for creating an AI response record."""

    message_id: UUID
    provider_name: str
    model_name: str
    validation_status: str = "pending"
    input_token_count: int | None = None
    output_token_count: int | None = None
    latency_ms: int | None = None


class AIResponse(BaseModel):
    """Schema representing a persisted AI response."""

    ai_response_id: UUID
    message_id: UUID
    provider_name: str
    model_name: str
    validation_status: str
    input_token_count: int | None
    output_token_count: int | None
    latency_ms: int | None
    created_at: datetime


# ============================================================================
# Phase 5.6 — Conversation history API response schemas
# ============================================================================


class ConversationSummary(BaseModel):
    """One conversation in the authenticated user's conversation list."""

    conversation_id: UUID
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class MessageSummary(BaseModel):
    """One persisted message returned by the conversation history API."""

    message_id: UUID
    conversation_id: UUID
    message_sequence: int
    message_type: str
    content_text: str
    created_at: datetime
