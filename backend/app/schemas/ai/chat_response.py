"""Phase 4.4 — Structured Chat Response models.

Frontend-friendly response representations derived from existing
Phase 4.3 data. These models are additive and do not replace or
modify any locked schema.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class StructuredSource(BaseModel):
    """Frontend-friendly citation derived from a Phase 4.3 SourceReference.

    Mapping from SourceReference:
        chunk_id       -> chunk_id
        quote          -> quote
        similarity_score -> relevance_score

    Additional enrichment fields (populated at response assembly time):
        source_title   -> knowledge_sources.title via provenance chain
        section        -> RetrievedChunk.metadata["section"] if present
    """

    chunk_id: UUID = Field(..., description="ID of the cited knowledge chunk")
    quote: str = Field(..., description="Relevant quote from the chunk")
    relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Retrieval similarity score",
    )
    source_title: str | None = Field(
        default=None,
        description="Human-readable source name from knowledge_sources.title",
    )
    section: str | None = Field(
        default=None,
        description="Section heading from chunk metadata, if available",
    )


class ChatUsage(BaseModel):
    """Structured token usage information from the generation provider.

    Derived from GenerationResult.metadata["usage"]:

        prompt_tokens     -> input_tokens
        completion_tokens -> output_tokens
    """

    input_tokens: int | None = Field(
        default=None,
        description="Number of prompt tokens used",
    )
    output_tokens: int | None = Field(
        default=None,
        description="Number of completion tokens generated",
    )
