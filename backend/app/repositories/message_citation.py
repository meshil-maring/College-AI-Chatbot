"""Repository layer for message-citation persistence (Phase 4.3)."""

from supabase import Client

from app.schemas.citation import MessageCitationCreate


def create_message_citations(client: Client, citations: list[MessageCitationCreate]) -> list[dict]:
    """Batch-insert message_citations records and return the created rows."""
    if not citations:
        return []

    payloads = [
        {
            "message_id": str(citation.message_id),
            "retrieval_operation_id": str(citation.retrieval_operation_id),
            "chunk_id": str(citation.chunk_id),
            "display_order": citation.display_order,
            **(
                {"citation_label": citation.citation_label}
                if citation.citation_label is not None
                else {}
            ),
        }
        for citation in citations
    ]

    response = (
        client.table("message_citations")
        .insert(payloads)
        .execute()
    )
    return response.data
