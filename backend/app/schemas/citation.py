"""Schemas for citation and retrieval-operation persistence (Phase 4.3)."""

from uuid import UUID

from pydantic import BaseModel


class RetrievalOperationCreate(BaseModel):
    """Schema for creating a retrieval_operations record."""

    ai_response_id: UUID
    query_text: str
    status: str = "completed"
    result_count: int | None = None


class RetrievedChunkCreate(BaseModel):
    """Schema for creating a retrieved_chunks record."""

    retrieval_operation_id: UUID
    chunk_id: UUID
    retrieval_rank: int
    relevance_score: float | None = None
    selected_for_context: bool = True


class MessageCitationCreate(BaseModel):
    """Schema for creating a message_citations record."""

    message_id: UUID
    retrieval_operation_id: UUID
    chunk_id: UUID
    display_order: int
    citation_label: str | None = None
