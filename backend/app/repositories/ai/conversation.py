"""Repository layer for conversation persistence."""

from uuid import UUID
from supabase import Client

from app.schemas.ai.conversation import ConversationCreate


def get_conversation(client: Client, conversation_id: UUID | str) -> dict | None:
    """Retrieve a conversation by its ID."""
    response = (
        client.table("conversations")
        .select("conversation_id, user_id, title, status, created_at, updated_at, knowledge_source_id, resource_institution_id, chat_institution_id")
        .eq("conversation_id", str(conversation_id))
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    return response.data


def create_conversation(client: Client, data: ConversationCreate, conversation_id: UUID | str | None = None) -> dict:
    """Create a new conversation record."""
    payload = {
        "user_id": str(data.user_id),
        "status": data.status,
    }
    if conversation_id is not None:
        payload["conversation_id"] = str(conversation_id)
    if data.title is not None:
        payload["title"] = data.title
    if data.knowledge_source_id is not None:
        payload["knowledge_source_id"] = str(data.knowledge_source_id)
        payload["resource_institution_id"] = str(data.resource_institution_id)

    response = (
        client.table("conversations")
        .insert(payload)
        .execute()
    )
    return response.data[0]


def update_conversation_timestamp(client: Client, conversation_id: UUID | str) -> None:
    """Update the updated_at timestamp of a conversation."""
    from datetime import datetime, timezone
    client.table("conversations").update({
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("conversation_id", str(conversation_id)).execute()


def list_conversations_for_user(client: Client, user_id: UUID | str) -> list[dict]:
    """Retrieve all conversations belonging to a user, newest first."""
    response = (
        client.table("conversations")
        .select("conversation_id, user_id, title, status, created_at, updated_at, knowledge_source_id, resource_institution_id, chat_institution_id")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    if not response.data:
        return []
    return response.data


def pending_turns_for_user(client: Client, user_id: UUID | str) -> dict:
    rows = (
        client.table('chat_turns').select('client_turn_id,conversation_id,institution_id')
        .eq('actor_id', str(user_id)).in_('state', ['processing', 'failed']).execute().data
    )
    return {row['conversation_id']: row['client_turn_id'] for row in rows or []}
