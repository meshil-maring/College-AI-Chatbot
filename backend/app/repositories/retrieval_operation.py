"""Repository layer for retrieval-operation and retrieved-chunk persistence (Phase 4.3)."""

from uuid import UUID
from supabase import Client

from app.schemas.citation import RetrievedChunkCreate, RetrievalOperationCreate


def create_retrieval_operation(client: Client, data: RetrievalOperationCreate) -> dict:
    """Create a new retrieval_operations record and return the created row."""
    payload = {
        "ai_response_id": str(data.ai_response_id),
        "query_text": data.query_text,
        "status": data.status,
    }
    if data.result_count is not None:
        payload["result_count"] = data.result_count

    response = (
        client.table("retrieval_operations")
        .insert(payload)
        .execute()
    )
    return response.data[0]


def create_retrieved_chunks(client: Client, chunks: list[RetrievedChunkCreate]) -> list[dict]:
    """Batch-insert retrieved_chunks records and return the created rows."""
    if not chunks:
        return []

    payloads = [
        {
            "retrieval_operation_id": str(chunk.retrieval_operation_id),
            "chunk_id": str(chunk.chunk_id),
            "retrieval_rank": chunk.retrieval_rank,
            "selected_for_context": chunk.selected_for_context,
            **(
                {"relevance_score": chunk.relevance_score}
                if chunk.relevance_score is not None
                else {}
            ),
        }
        for chunk in chunks
    ]

    response = (
        client.table("retrieved_chunks")
        .insert(payloads)
        .execute()
    )
    return response.data
