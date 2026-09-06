"""
Tests for Phase 4.1 — AI Request/Response Contract.

Covers:
  - Valid AIRequest is accepted
  - Empty/invalid user query is rejected
  - Missing retrieval scope is rejected
  - Invalid retrieval scope (no filters) is rejected
  - Invalid retrieved chunk structure is rejected
  - Response can represent a grounded answer with source references
  - Response can represent an insufficient-context/no-answer state
  - AIRequest/AIResponse consistency validation
  - RetrievalScope scope guard enforcement
"""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.generation import (
    AIContext,
    AIRequest,
    AIResponse,
    RetrievalScope,
    RetrievedChunk,
    SourceReference,
)


# ============================================================================
# Fixtures and Helpers
# ============================================================================


def valid_uuid() -> UUID:
    """Generate a valid UUID."""
    return uuid4()


def valid_chunk() -> RetrievedChunk:
    """Create a valid retrieved chunk."""
    return RetrievedChunk(
        chunk_id=valid_uuid(),
        document_id=valid_uuid(),
        document_version_id=valid_uuid(),
        text="Sample knowledge chunk about admissions requirements.",
        similarity_score=0.85,
        metadata={"section": "Admissions", "page": 1},
    )


def valid_scope() -> RetrievalScope:
    """Create a valid retrieval scope."""
    return RetrievalScope(institution_id=valid_uuid())


def valid_request() -> AIRequest:
    """Create a valid AI request."""
    return AIRequest(
        user_query="What are the admissions requirements?",
        retrieval_scope=valid_scope(),
        retrieved_chunks=[valid_chunk()],
        model_name="openai/gpt-4",
    )


# ============================================================================
# RetrievalScope Tests
# ============================================================================


class TestRetrievalScope:
    """Test retrieval scope guard validation."""

    def test_scope_with_single_filter_is_valid(self):
        """Scope with one filter is valid."""
        scope = RetrievalScope(institution_id=valid_uuid())
        assert scope.institution_id is not None

    def test_scope_with_multiple_filters_is_valid(self):
        """Scope with multiple filters is valid."""
        scope = RetrievalScope(
            institution_id=valid_uuid(),
            knowledge_source_id=valid_uuid(),
        )
        assert scope.institution_id is not None
        assert scope.knowledge_source_id is not None

    def test_scope_without_filters_is_rejected(self):
        """Scope with no filters is rejected (prevents unscoped retrieval)."""
        with pytest.raises(ValidationError, match="at least one retrieval scope filter"):
            RetrievalScope()

    def test_scope_with_all_none_is_rejected(self):
        """Scope with all fields explicitly None is rejected."""
        with pytest.raises(ValidationError, match="at least one retrieval scope filter"):
            RetrievalScope(
                institution_id=None,
                knowledge_source_id=None,
                document_id=None,
                document_version_id=None,
                processing_run_id=None,
            )


# ============================================================================
# RetrievedChunk Tests
# ============================================================================


class TestRetrievedChunk:
    """Test retrieved chunk validation."""

    def test_valid_chunk_is_accepted(self):
        """Valid chunk with all required fields is accepted."""
        chunk = valid_chunk()
        assert chunk.chunk_id is not None
        assert chunk.text is not None
        assert chunk.similarity_score == 0.85

    def test_chunk_with_empty_text_is_rejected(self):
        """Chunk with empty text is rejected."""
        with pytest.raises(ValidationError, match="chunk text must not be empty"):
            RetrievedChunk(
                chunk_id=valid_uuid(),
                text="",
                similarity_score=0.8,
            )

    def test_chunk_with_whitespace_only_is_rejected(self):
        """Chunk with whitespace-only text is rejected."""
        with pytest.raises(ValidationError, match="chunk text must not be empty"):
            RetrievedChunk(
                chunk_id=valid_uuid(),
                text="   \n  \t  ",
                similarity_score=0.8,
            )

    def test_chunk_text_is_normalized(self):
        """Chunk text with extra whitespace is normalized."""
        chunk = RetrievedChunk(
            chunk_id=valid_uuid(),
            text="  Multiple   spaces  between   words  ",
            similarity_score=0.8,
        )
        assert chunk.text == "Multiple spaces between words"

    def test_chunk_with_non_string_text_is_rejected(self):
        """Chunk with non-string text is rejected."""
        with pytest.raises(ValidationError):
            RetrievedChunk(
                chunk_id=valid_uuid(),
                text=123,
                similarity_score=0.8,
            )

    def test_chunk_similarity_score_bounds(self):
        """Similarity score must be between 0.0 and 1.0."""
        with pytest.raises(ValidationError):
            RetrievedChunk(
                chunk_id=valid_uuid(),
                text="Valid text",
                similarity_score=1.5,
            )

        with pytest.raises(ValidationError):
            RetrievedChunk(
                chunk_id=valid_uuid(),
                text="Valid text",
                similarity_score=-0.1,
            )

    def test_chunk_with_optional_document_fields(self):
        """Chunk can omit optional document reference fields."""
        chunk = RetrievedChunk(
            chunk_id=valid_uuid(),
            text="Content",
            similarity_score=0.8,
        )
        assert chunk.document_id is None
        assert chunk.document_version_id is None


# ============================================================================
# AIRequest Tests
# ============================================================================


class TestAIRequest:
    """Test AI request validation."""

    def test_valid_request_is_accepted(self):
        """Valid AIRequest with all required fields is accepted."""
        request = valid_request()
        assert request.user_query is not None
        assert request.retrieval_scope is not None
        assert len(request.retrieved_chunks) > 0

    def test_request_without_query_is_rejected(self):
        """AIRequest without user_query is rejected."""
        with pytest.raises(ValidationError, match="user_query"):
            AIRequest(
                retrieval_scope=valid_scope(),
                retrieved_chunks=[valid_chunk()],
            )

    def test_request_with_empty_query_is_rejected(self):
        """AIRequest with empty user_query is rejected."""
        with pytest.raises(ValidationError, match="user_query must not be empty"):
            AIRequest(
                user_query="",
                retrieval_scope=valid_scope(),
                retrieved_chunks=[valid_chunk()],
            )

    def test_request_with_whitespace_only_query_is_rejected(self):
        """AIRequest with whitespace-only user_query is rejected."""
        with pytest.raises(ValidationError, match="user_query must not be empty"):
            AIRequest(
                user_query="   \n  \t  ",
                retrieval_scope=valid_scope(),
                retrieved_chunks=[valid_chunk()],
            )

    def test_request_query_is_normalized(self):
        """AIRequest user_query is normalized."""
        request = AIRequest(
            user_query="  What are   the   requirements?  ",
            retrieval_scope=valid_scope(),
            retrieved_chunks=[valid_chunk()],
        )
        assert request.user_query == "What are the requirements?"

    def test_request_with_non_string_query_is_rejected(self):
        """AIRequest with non-string query is rejected."""
        with pytest.raises(ValidationError):
            AIRequest(
                user_query=123,
                retrieval_scope=valid_scope(),
                retrieved_chunks=[valid_chunk()],
            )

    def test_request_without_scope_is_rejected(self):
        """AIRequest without retrieval_scope is rejected."""
        with pytest.raises(ValidationError, match="retrieval_scope"):
            AIRequest(
                user_query="What are the requirements?",
                retrieved_chunks=[valid_chunk()],
            )

    def test_request_with_unscoped_retrieval_is_rejected(self):
        """AIRequest with unscoped retrieval (no scope filters) is rejected."""
        with pytest.raises(ValidationError, match="at least one retrieval scope filter"):
            AIRequest(
                user_query="What are the requirements?",
                retrieval_scope=RetrievalScope(),
                retrieved_chunks=[valid_chunk()],
            )

    def test_request_with_empty_chunks_list_is_valid(self):
        """AIRequest can have empty retrieved_chunks (insufficient context case)."""
        request = AIRequest(
            user_query="What are the requirements?",
            retrieval_scope=valid_scope(),
            retrieved_chunks=[],
        )
        assert len(request.retrieved_chunks) == 0

    def test_request_with_invalid_chunk_is_rejected(self):
        """AIRequest with invalid chunk structure is rejected."""
        with pytest.raises(ValidationError, match="chunk text must not be empty"):
            AIRequest(
                user_query="What are the requirements?",
                retrieval_scope=valid_scope(),
                retrieved_chunks=[
                    RetrievedChunk(
                        chunk_id=valid_uuid(),
                        text="",  # Invalid: empty
                        similarity_score=0.8,
                    )
                ],
            )

    def test_request_model_name_is_optional(self):
        """AIRequest model_name is optional."""
        request = AIRequest(
            user_query="What are the requirements?",
            retrieval_scope=valid_scope(),
            retrieved_chunks=[valid_chunk()],
        )
        assert request.model_name is None

    def test_request_model_name_can_be_provided(self):
        """AIRequest model_name can be specified."""
        request = AIRequest(
            user_query="What are the requirements?",
            retrieval_scope=valid_scope(),
            retrieved_chunks=[valid_chunk()],
            model_name="anthropic/claude-3-opus",
        )
        assert request.model_name == "anthropic/claude-3-opus"

    def test_request_with_empty_model_name_is_rejected(self):
        """AIRequest with empty model_name string is rejected."""
        with pytest.raises(ValidationError, match="model_name must not be empty"):
            AIRequest(
                user_query="What are the requirements?",
                retrieval_scope=valid_scope(),
                retrieved_chunks=[valid_chunk()],
                model_name="",
            )


# ============================================================================
# AIContext Tests
# ============================================================================


class TestAIContext:
    """Test AI context validation."""

    def test_valid_context_is_accepted(self):
        """Valid AIContext with required fields is accepted."""
        context = AIContext(
            system_instructions="You are a helpful college admissions assistant.",
            user_question="What are the admissions requirements?",
            retrieved_knowledge=[valid_chunk()],
            grounding_instructions="Ground your answer in the provided context.",
        )
        assert context.system_instructions is not None
        assert context.user_question is not None

    def test_context_with_empty_system_instructions_is_rejected(self):
        """AIContext with empty system_instructions is rejected."""
        with pytest.raises(ValidationError, match="must not be empty"):
            AIContext(
                system_instructions="",
                user_question="What are the requirements?",
            )

    def test_context_with_empty_user_question_is_rejected(self):
        """AIContext with empty user_question is rejected."""
        with pytest.raises(ValidationError, match="must not be empty"):
            AIContext(
                system_instructions="You are helpful.",
                user_question="",
            )

    def test_context_strings_are_normalized(self):
        """AIContext strings are normalized."""
        context = AIContext(
            system_instructions="  You   are   helpful  ",
            user_question="  What  is  this?  ",
            grounding_instructions="  Ground   answer  ",
        )
        assert context.system_instructions == "You are helpful"
        assert context.user_question == "What is this?"
        assert context.grounding_instructions == "Ground answer"

    def test_context_with_empty_knowledge_list_is_valid(self):
        """AIContext can have empty retrieved_knowledge."""
        context = AIContext(
            system_instructions="You are helpful.",
            user_question="What is this?",
            retrieved_knowledge=[],
        )
        assert len(context.retrieved_knowledge) == 0


# ============================================================================
# SourceReference Tests
# ============================================================================


class TestSourceReference:
    """Test source reference validation."""

    def test_valid_reference_is_accepted(self):
        """Valid SourceReference is accepted."""
        ref = SourceReference(
            chunk_id=valid_uuid(),
            document_id=valid_uuid(),
            quote="Admissions requires a completed application.",
        )
        assert ref.chunk_id is not None
        assert ref.quote is not None

    def test_reference_with_empty_quote_is_rejected(self):
        """SourceReference with empty quote is rejected."""
        with pytest.raises(ValidationError, match="quote must not be empty"):
            SourceReference(
                chunk_id=valid_uuid(),
                quote="",
            )

    def test_reference_quote_is_normalized(self):
        """SourceReference quote is normalized."""
        ref = SourceReference(
            chunk_id=valid_uuid(),
            quote="  Multiple   spaces   in   quote  ",
        )
        assert ref.quote == "Multiple spaces in quote"

    def test_reference_similarity_score_bounds(self):
        """SourceReference similarity_score must be 0.0-1.0 if provided."""
        with pytest.raises(ValidationError):
            SourceReference(
                chunk_id=valid_uuid(),
                quote="Quote",
                similarity_score=1.5,
            )


# ============================================================================
# AIResponse Tests
# ============================================================================


class TestAIResponse:
    """Test AI response validation."""

    def test_successful_response_with_answer_is_valid(self):
        """Successful response with answer and sources is valid."""
        response = AIResponse(
            status="success",
            answer="The admissions requirements include a completed application form and test scores.",
            source_references=[
                SourceReference(
                    chunk_id=valid_uuid(),
                    document_id=valid_uuid(),
                    quote="admissions requires completed application",
                )
            ],
        )
        assert response.status == "success"
        assert response.answer is not None
        assert len(response.source_references) > 0

    def test_insufficient_context_response_is_valid(self):
        """Insufficient context response without answer is valid."""
        response = AIResponse(
            status="insufficient_context",
            answer=None,
            source_references=[],
        )
        assert response.status == "insufficient_context"
        assert response.answer is None

    def test_response_default_status_is_success(self):
        """Response defaults to status='success'."""
        response = AIResponse(
            answer="Sample answer.",
            source_references=[],
        )
        assert response.status == "success"

    def test_success_response_without_answer_is_rejected(self):
        """Success response without answer is rejected."""
        with pytest.raises(ValidationError, match="status='success' requires non-empty answer"):
            AIResponse(
                status="success",
                answer=None,
                source_references=[],
            )

    def test_success_response_with_empty_answer_is_rejected(self):
        """Success response with empty answer is rejected."""
        with pytest.raises(ValidationError, match="answer must not be empty"):
            AIResponse(
                status="success",
                answer="",
                source_references=[],
            )

    def test_insufficient_context_response_with_answer_is_rejected(self):
        """Insufficient context response cannot have an answer."""
        with pytest.raises(ValidationError, match="status='insufficient_context' cannot have"):
            AIResponse(
                status="insufficient_context",
                answer="Some answer",
                source_references=[],
            )

    def test_response_answer_is_normalized(self):
        """Response answer is normalized."""
        response = AIResponse(
            status="success",
            answer="  Answer   with   extra   spaces  ",
            source_references=[],
        )
        assert response.answer == "Answer with extra spaces"

    def test_response_with_empty_answer_string_is_rejected(self):
        """Response with whitespace-only answer is rejected."""
        with pytest.raises(ValidationError, match="answer must not be empty"):
            AIResponse(
                status="success",
                answer="   \n  \t  ",
                source_references=[],
            )

    def test_response_with_invalid_status_is_rejected(self):
        """Response with invalid status is rejected."""
        with pytest.raises(ValidationError, match="status must be"):
            AIResponse(
                status="error",
                answer="Answer",
                source_references=[],
            )

    def test_response_with_multiple_references_is_valid(self):
        """Response with multiple source references is valid."""
        response = AIResponse(
            status="success",
            answer="The admissions process involves multiple steps.",
            source_references=[
                SourceReference(
                    chunk_id=valid_uuid(),
                    quote="First step: application",
                ),
                SourceReference(
                    chunk_id=valid_uuid(),
                    quote="Second step: testing",
                ),
            ],
        )
        assert len(response.source_references) == 2

    def test_response_can_omit_model_used(self):
        """Response model_used is optional."""
        response = AIResponse(
            status="success",
            answer="Answer",
            source_references=[],
        )
        assert response.model_used is None

    def test_response_can_specify_model_used(self):
        """Response can specify model_used."""
        response = AIResponse(
            status="success",
            answer="Answer",
            source_references=[],
            model_used="openai/gpt-4",
        )
        assert response.model_used == "openai/gpt-4"

    def test_response_can_have_metadata(self):
        """Response can include metadata."""
        response = AIResponse(
            status="success",
            answer="Answer",
            source_references=[],
            metadata={"tokens_used": 150, "latency_ms": 1200},
        )
        assert response.metadata["tokens_used"] == 150


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for the full Phase 4.1 contract."""

    def test_full_request_response_flow(self):
        """Full request-response flow is valid."""
        request = valid_request()
        response = AIResponse(
            status="success",
            answer="The admissions requirements include a completed application.",
            source_references=[
                SourceReference(
                    chunk_id=request.retrieved_chunks[0].chunk_id,
                    document_id=request.retrieved_chunks[0].document_id,
                    quote="admissions requirements",
                )
            ],
            model_used=request.model_name,
        )
        assert response.status == "success"
        assert len(response.source_references) > 0

    def test_insufficient_context_flow(self):
        """Request without chunks can receive insufficient-context response."""
        request = AIRequest(
            user_query="What is a very obscure policy?",
            retrieval_scope=valid_scope(),
            retrieved_chunks=[],
        )
        response = AIResponse(
            status="insufficient_context",
            answer=None,
            source_references=[],
        )
        assert len(request.retrieved_chunks) == 0
        assert response.answer is None

    def test_multiple_chunks_can_ground_answer(self):
        """Multiple retrieved chunks can ground a single answer."""
        chunks = [valid_chunk() for _ in range(3)]
        request = AIRequest(
            user_query="What is the complete admissions process?",
            retrieval_scope=valid_scope(),
            retrieved_chunks=chunks,
        )
        response = AIResponse(
            status="success",
            answer="The admissions process has three stages.",
            source_references=[
                SourceReference(
                    chunk_id=chunks[i].chunk_id,
                    quote=f"Stage {i+1} description",
                )
                for i in range(3)
            ],
        )
        assert len(request.retrieved_chunks) == 3
        assert len(response.source_references) == 3
