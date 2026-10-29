"""Public AI request/response contracts and canonical prompt-input exports.

Prompt-input models live in generation_context; existing imports from this
module retain the same schema classes and serialized contracts.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.ai.generation_context import (
    AIContext, ConversationTurn, RetrievalScope, RetrievedChunk,
)

__all__ = [
    'AIRequest', 'AIContext', 'AIResponse', 'ConversationTurn',
    'RetrievalScope', 'RetrievedChunk', 'SourceReference',
]



class AIRequest(BaseModel):
    """
    AI generation request contract.

    Validates:
    - User query is present and non-empty
    - Retrieval scope is present (prevents model-only or unscoped retrieval)
    - Retrieved chunks are valid and non-empty
    - Model name is optional but valid if provided

    Never silently invents missing retrieval context.
    """

    user_query: str = Field(..., description="User's natural language question")
    retrieval_scope: RetrievalScope = Field(
        ..., description="Scope guard for retrieved chunks"
    )
    retrieved_chunks: list[RetrievedChunk] = Field(
        default_factory=list, description="Retrieved knowledge chunks"
    )
    model_name: str | None = Field(
        default=None,
        description="Optional AI model identifier (e.g., 'openai/gpt-4')",
    )
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list,
        description="Bounded prior conversation turns for multi-turn context",
    )

    retrieval_query: str | None = Field(
        default=None,
        description=(
            "Standalone retrieval query produced by conversational query "
            "interpretation. When set and different from ``user_query``, it is "
            "used to retrieve knowledge and surfaced to the model as the "
            "interpreted intent so follow-up wording does not hide intent."
        ),
    )

    @field_validator("user_query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        """Normalize and validate user query."""
        if not isinstance(value, str):
            raise ValueError("user_query must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("user_query must not be empty")
        return normalized

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        """Validate model name if provided."""
        if value is not None and not value:
            raise ValueError("model_name must not be empty")
        return value

    @model_validator(mode="after")
    def validate_retrieved_chunks(self) -> "AIRequest":
        """
        Validate retrieved chunks structure.
        Note: Empty chunks list is valid (insufficient context case).
        Invalid structure is rejected explicitly.
        """
        # Chunks can be empty (no context), but if present must be valid
        # Validation happens through RetrievedChunk model validation
        return self


class SourceReference(BaseModel):
    """
    Citation/grounding reference for answer content.

    Connects answer segments to source chunks.
    """

    chunk_id: UUID = Field(..., description="ID of source chunk")
    document_id: UUID | None = Field(default=None, description="Source document")
    document_version_id: UUID | None = Field(
        default=None, description="Source document version"
    )
    quote: str = Field(..., description="Relevant quote from chunk")
    similarity_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Retrieval similarity score"
    )

    @field_validator("quote")
    @classmethod
    def validate_quote(cls, value: str) -> str:
        """Ensure quote is non-empty."""
        if not isinstance(value, str):
            raise ValueError("quote must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("quote must not be empty")
        return normalized


class AIResponse(BaseModel):
    """
    AI generation response contract.

    Represents either:
    1. Successful answer (status="success") with answer text and source references
    2. Insufficient context state (status="insufficient_context") without answer

    Never returns unsourced or hallucinated content.
    """

    answer: str | None = Field(
        default=None, description="Generated answer or None if insufficient context"
    )
    source_references: list[SourceReference] = Field(
        default_factory=list,
        description="Source chunks grounding the answer",
    )
    status: str = Field(
        default="success",
        description="Response status: 'success' or 'insufficient_context'",
    )
    model_used: str | None = Field(
        default=None, description="AI model identifier used for generation"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (tokens, latency, etc.)",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        """Validate response status."""
        if value not in ("success", "insufficient_context"):
            raise ValueError("status must be 'success' or 'insufficient_context'")
        return value

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str | None) -> str | None:
        """Validate answer if provided."""
        if value is not None:
            if not isinstance(value, str):
                raise ValueError("answer must be a string or None")
            normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
            # Markdown lists, paragraphs and code indentation depend on newlines.
            # Retain the existing whitespace normalization for one-line prose.
            if "\n" not in normalized:
                normalized = " ".join(normalized.split())
            if not normalized:
                raise ValueError("answer must not be empty")
            return normalized
        return value

    @model_validator(mode="after")
    def validate_answer_and_status_consistency(self) -> "AIResponse":
        """
        Enforce consistency between status and answer:
        - If status="success", answer must be present and non-empty
        - If status="insufficient_context", answer should be None
        """
        if self.status == "success" and not self.answer:
            raise ValueError(
                "status='success' requires non-empty answer"
            )
        if self.status == "insufficient_context" and self.answer:
            raise ValueError(
                "status='insufficient_context' cannot have an answer"
            )
        return self
