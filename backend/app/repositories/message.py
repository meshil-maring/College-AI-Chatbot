"""Repository layer for message persistence."""

from uuid import UUID
from supabase import Client

from app.schemas.conversation import MessageCreate


def get_next_message_sequence(client: Client, conversation_id: UUID | str) -> int:
    """Determine the next valid message sequence for a conversation."""
    response = (
        client.table("messages")
        .select("message_sequence")
        .eq("conversation_id", str(conversation_id))
        .order("message_sequence", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return 1

    return response.data[0]["message_sequence"] + 1


def create_message(client: Client, data: MessageCreate) -> dict:
    """Create a new message record."""
    payload = {
        "conversation_id": str(data.conversation_id),
        "message_sequence": data.message_sequence,
        "message_type": data.message_type,
        "content_text": data.content_text,
    }

    response = (
        client.table("messages")
        .insert(payload)
        .execute()
    )
    return response.data[0]


def get_message(client: Client, message_id: UUID | str) -> dict | None:
    """Retrieve a message by its ID."""
    response = (
        client.table("messages")
        .select("message_id, conversation_id, message_sequence, message_type, content_text, created_at")
        .eq("message_id", str(message_id))
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    return response.data
