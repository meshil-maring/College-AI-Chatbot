"""Phase 5.6 — Conversation history retrieval service."""

from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.ai.conversation import get_conversation, list_conversations_for_user, pending_turns_for_user
from app.repositories.ai.message import list_messages_for_conversation
from app.schemas.ai.conversation import ConversationSummary, MessageSummary
from app.services.knowledge.resources.policy import allowed, REDACTED_MESSAGE
from .chat_support.resource_scope import restored_context, history_matches
from .chat_support.history_sources import restore_sources


def get_user_conversations(user_id: UUID) -> list[ConversationSummary]:
    """Return all conversations belonging to the authenticated user.

    Conversations are ordered newest-first by ``updated_at``.
    """
    client = get_admin_client()
    rows = list_conversations_for_user(client, user_id)
    pending = pending_turns_for_user(client, user_id) if any(row.get('chat_institution_id') for row in rows) else {}
    result = []
    for row in rows:
        context = restored_context(client, user_id, row)
        if context and not context['available']:
            row = {**row, 'title': 'Resource conversation unavailable'}
        result.append(ConversationSummary(**row, resource_context=context,
            pending_turn_id=pending.get(row['conversation_id']) if not context or context['available'] else None))
    return result


def get_conversation_messages(
    conversation_id: UUID,
    user_id: UUID,
    conversation: dict | None = None,
    *,
    include_sources: bool = False,
) -> list[MessageSummary]:
    """Return chronological messages for one authenticated user's conversation.

    Ownership is verified before any messages are returned: a conversation that
    does not exist or does not belong to the authenticated user produces a
    ``404`` so the existence of other users' conversations is never confirmed.

    Messages are ordered by ``message_sequence`` ascending.

    ``conversation`` may supply an already-fetched conversation row (e.g. the
    chat boundary resolves the conversation for ownership verification anyway).
    When supplied WITH a ``user_id`` (a fully resolved row), the duplicate
    conversation lookup is skipped and ownership is verified against it; rows
    without a ``user_id`` (partial/partially mocked rows) trigger the normal
    lookup so ownership data is always authoritative.
    """
    client = get_admin_client()
    if conversation is None or not conversation.get("user_id"):
        conversation = get_conversation(client, conversation_id)

    if conversation is None or str(conversation.get("user_id")) != str(user_id):
        raise AppError(
            "Conversation not found",
            status_code=404,
            code="CONVERSATION_NOT_FOUND",
        )

    rows = list_messages_for_conversation(client, conversation_id)
    context = restored_context(client, user_id, conversation)
    if context and not context['available']:
        return [MessageSummary(**{**rows[0], 'message_type': 'assistant',
            'content_text': REDACTED_MESSAGE, 'knowledge_policy': None})] if rows else []
    visible = []
    for row in rows:
        if row['message_type'] == 'assistant' and (
            not history_matches(row.get('knowledge_policy'), conversation)
            or not allowed(client, user_id, row.get('knowledge_policy'))
        ):
            visible.append(MessageSummary(**{**row, 'content_text': REDACTED_MESSAGE, 'knowledge_policy': None}))
            break
        visible.append(MessageSummary(**row))
    return restore_sources(client, user_id, conversation, visible) if include_sources else visible
