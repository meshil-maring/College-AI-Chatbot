"""
Phase 4.1 — AI Request/Response Contract.

Represents the boundary between Phase 3 Retrieval and Phase 4 AI Generation.

Defines explicit contracts for:
1. AIRequest: AI generation request with user query, retrieval scope, and retrieved chunks
2. AIContext: Internal representation of context for prompt construction
3. AIResponse: AI generation response with answer and source references
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# Retrieval Scope
# ============================================================================
# Reuses the scope guard pattern from Phase 3 RetrievalRequest.
# At least one scope filter must be specified to ensure retrieval is scoped.


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


# ============================================================================
# Retrieved Chunk (reused from Phase 3)
# ============================================================================
# Reuses the structure from Phase 3 RetrievalResult to maintain contract consistency.


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


# ============================================================================
# Conversation Turn (Phase 5.7b)
# ============================================================================
# Bounded conversational history passed into the generation pipeline.


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


# ============================================================================
# AI Request
# ============================================================================
# Explicit contract for AI generation requests.
# Ensures all required context is present before AI processing.


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


# ============================================================================
# AI Context
# ============================================================================
# Internal representation for prompt construction (not serialized in API response).
# Groups system, user, and knowledge components.


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


# ============================================================================
# Source Reference
# ============================================================================
# Grounding for generated answers.


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


# ============================================================================
# AI Response
# ============================================================================
# Explicit response contract.
# Must represent either a grounded answer or insufficient-context state.


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
            normalized = " ".join(value.split())
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
