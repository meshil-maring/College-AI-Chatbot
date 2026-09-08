"""Phase 5.6 — Conversation history API router."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas.conversation import ConversationSummary, MessageSummary
from app.services.conversation_history import (
    get_conversation_messages,
    get_user_conversations,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    current_user: dict = Depends(get_current_user),
) -> list[ConversationSummary]:
    """List conversations belonging to the authenticated user."""
    return get_user_conversations(UUID(current_user["user_id"]))


@router.get("/{conversation_id}/messages", response_model=list[MessageSummary])
def get_messages(
    conversation_id: UUID,
    current_user: dict = Depends(get_current_user),
) -> list[MessageSummary]:
    """Retrieve messages for one of the authenticated user's conversations."""
    return get_conversation_messages(conversation_id, UUID(current_user["user_id"]))