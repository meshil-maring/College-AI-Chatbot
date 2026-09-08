"""Phase 5.6 — Conversation history retrieval service."""

from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.conversation import get_conversation, list_conversations_for_user
from app.repositories.message import list_messages_for_conversation
from app.schemas.conversation import ConversationSummary, MessageSummary


def get_user_conversations(user_id: UUID) -> list[ConversationSummary]:
    """Return all conversations belonging to the authenticated user.

    Conversations are ordered newest-first by ``updated_at``.
    """
    client = get_admin_client()
    rows = list_conversations_for_user(client, user_id)
    return [ConversationSummary(**row) for row in rows]


def get_conversation_messages(
    conversation_id: UUID, user_id: UUID
) -> list[MessageSummary]:
    """Return chronological messages for one authenticated user's conversation.

    Ownership is verified before any messages are returned: a conversation that
    does not exist or does not belong to the authenticated user produces a
    ``404`` so the existence of other users' conversations is never confirmed.

    Messages are ordered by ``message_sequence`` ascending.
    """
    client = get_admin_client()
    conversation = get_conversation(client, conversation_id)

    if conversation is None or str(conversation.get("user_id")) != str(user_id):
        raise AppError(
            "Conversation not found",
            status_code=404,
            code="CONVERSATION_NOT_FOUND",
        )

    rows = list_messages_for_conversation(client, conversation_id)
    return [MessageSummary(**row) for row in rows]