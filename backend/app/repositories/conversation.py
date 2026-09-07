"""Repository layer for conversation persistence."""

from uuid import UUID
from supabase import Client

from app.schemas.conversation import ConversationCreate


def get_conversation(client: Client, conversation_id: UUID | str) -> dict | None:
    """Retrieve a conversation by its ID."""
    response = (
        client.table("conversations")
        .select("conversation_id, user_id, title, status, created_at, updated_at")
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
