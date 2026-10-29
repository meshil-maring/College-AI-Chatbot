"""Scoped knowledge and conversation inputs used to assemble model context."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator



class RetrievalScope(BaseModel):
    """
    Scope guard for AI generation context.
    Ensures retrieved chunks are constrained to a specific domain.
    At least one scope filter is required.
    """

    institution_id: UUID | None = None
    knowledge_source_id: UUID | None = None
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    processing_run_id: UUID | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "RetrievalScope":
        """Enforce at least one scope filter is specified."""
        if not any(
            value is not None
            for value in (
                self.institution_id,
                self.knowledge_source_id,
                self.document_id,
                self.document_version_id,
                self.processing_run_id,
            )
        ):
            raise ValueError("at least one retrieval scope filter is required")
        return self


class RetrievedChunk(BaseModel):
    """
    Retrieved knowledge chunk from Phase 3 retrieval layer.
    Reuses the RetrievalResult structure.
    """

    chunk_id: UUID
    document_id: UUID | None = None
    document_version_id: UUID | None = None
    text: str = Field(..., description="Chunk content text")
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        """Ensure chunk text is not empty after normalization."""
        if not isinstance(value, str):
            raise ValueError("chunk text must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("chunk text must not be empty")
        return normalized


class ConversationTurn(BaseModel):
    """One persisted message from the conversation history.

    Used to inject bounded conversational context into the LLM prompt.
    This is an internal type; it is not exposed in the public API response.
    """

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content text")

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("content must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("content must not be empty")
        return normalized


class AIContext(BaseModel):
    """
    Internal AI context representation.
    Used for prompt construction and grounding.

    Contains:
    - System instructions for model behavior
    - User question (normalized)
    - Retrieved knowledge/context
    - Grounding/citation instructions
    """

    system_instructions: str = Field(
        ..., description="System prompt guiding model behavior"
    )
    user_question: str = Field(..., description="User's question in normalized form")
    model_name: str | None = Field(
        default=None, description="Optional AI model identifier requested for generation"
    )
    retrieved_knowledge: list[RetrievedChunk] = Field(
        default_factory=list, description="Retrieved context chunks"
    )
    grounding_instructions: str = Field(
        default="",
        description="Instructions for grounding answer in source material and citations",
    )
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list,
        description="Bounded prior conversation turns for multi-turn context",
    )
    retrieval_query: str | None = Field(
        default=None,
        description=(
            "Standalone retrieval query from conversational query interpretation. "
            "Internal only; never serialized to API responses."
        ),
    )
    student_context: str | None = Field(
        default=None,
        description=(
            "Rendered authorized student data (delimited data-only block). "
            "Internal only; derived server-side from the authenticated JWT and "
            "never serialized to API responses."
        ),
    )
    public: bool = Field(
        default=False,
        description=(
            "Internal trust-boundary marker. True only after the public chat "
            "orchestrator has completed tenant and canonical provenance checks."
        ),
    )
    institution_id: UUID | None = Field(
        default=None,
        description="Server-resolved institution for an internal public context.",
    )
    max_output_tokens: int | None = Field(
        default=None,
        gt=0,
        le=4096,
        description="Server-controlled provider output budget; never client supplied.",
    )

    @field_validator("system_instructions", "user_question", "grounding_instructions")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        """Ensure non-empty strings after normalization."""
        if not isinstance(value, str):
            raise ValueError("must be a string")
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("must not be empty after normalization")
        return normalized

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, value: str | None) -> str | None:
        """Validate model name if provided."""
        if value is not None and not value:
            raise ValueError("model_name must not be empty")
        return value

    @model_validator(mode="after")
    def validate_public_boundary(self) -> "AIContext":
        """Keep public contexts stateless, non-personalized, and server-owned.

        The marker does not authorize chunks by itself. Only the public
        orchestrator may set it, after PublicKnowledgePolicy has replaced
        retrieval candidates with canonical verified chunks.
        """
        if not self.public:
            return self
        if self.institution_id is None:
            raise ValueError("public AI context requires a resolved institution")
        if self.student_context is not None:
            raise ValueError("public AI context cannot contain student data")
        if self.conversation_history:
            raise ValueError("public AI context must be stateless")
        if self.model_name is not None:
            raise ValueError("public AI context model is server controlled")
        if self.max_output_tokens is None:
            raise ValueError("public AI context requires a server output limit")
        return self
