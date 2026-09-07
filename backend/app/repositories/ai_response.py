"""Repository layer for AI response metadata persistence."""

from uuid import UUID
from supabase import Client

from app.schemas.conversation import AIResponseCreate


def create_ai_response(client: Client, data: AIResponseCreate) -> dict:
    """Create a new AI response metadata record."""
    payload = {
        "message_id": str(data.message_id),
        "provider_name": data.provider_name,
        "model_name": data.model_name,
        "validation_status": data.validation_status,
    }
    if data.input_token_count is not None:
        payload["input_token_count"] = data.input_token_count
    if data.output_token_count is not None:
        payload["output_token_count"] = data.output_token_count
    if data.latency_ms is not None:
        payload["latency_ms"] = data.latency_ms

    response = (
        client.table("ai_responses")
        .insert(payload)
        .execute()
    )
    return response.data[0]


def get_ai_response(client: Client, ai_response_id: UUID | str) -> dict | None:
    """Retrieve an AI response record by its ID."""
    response = (
        client.table("ai_responses")
        .select(
            "ai_response_id, message_id, provider_name, model_name, "
            "validation_status, input_token_count, output_token_count, latency_ms, created_at"
        )
        .eq("ai_response_id", str(ai_response_id))
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    return response.data


def get_ai_response_by_message_id(client: Client, message_id: UUID | str) -> dict | None:
    """Retrieve an AI response record by its message_id."""
    response = (
        client.table("ai_responses")
        .select(
            "ai_response_id, message_id, provider_name, model_name, "
            "validation_status, input_token_count, output_token_count, latency_ms, created_at"
        )
        .eq("message_id", str(message_id))
        .maybe_single()
        .execute()
    )
    if response is None:
        return None
    return response.data
