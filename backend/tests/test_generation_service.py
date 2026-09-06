from uuid import UUID, uuid4

import httpx
import pytest

from app.core.errors import AppError
from app.schemas.generation import AIContext, AIResponse, RetrievedChunk, SourceReference
from app.services.context import assemble_context
from app.services.generation import AIGenerationService, generate_response
from app.services.generation_provider import GenerationProvider, GenerationResult
from app.schemas.generation import AIRequest, RetrievalScope


class DeterministicProvider:
    def __init__(self, result: GenerationResult | None = None) -> None:
        self.contexts: list[AIContext] = []
        self._result = result

    def generate(self, context: AIContext) -> GenerationResult:
        self.contexts.append(context)
        if self._result is not None:
            return self._result
        chunk = context.retrieved_knowledge[0]
        return GenerationResult(
            answer=f"Answer for: {context.user_question}",
            source_references=[
                SourceReference(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_version_id=chunk.document_version_id,
                    quote=chunk.text,
                    similarity_score=chunk.similarity_score,
                )
            ],
            model_used=context.model_name,
            metadata={"provider": "deterministic-test"},
        )


def valid_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=UUID("00000000-0000-0000-0000-000000000001"),
        document_id=UUID("10000000-0000-0000-0000-000000000001"),
        document_version_id=UUID("20000000-0000-0000-0000-000000000001"),
        text="Admissions require a completed application.",
        similarity_score=0.91,
        metadata={"section": "Admissions"},
    )


def valid_context(chunks: list[RetrievedChunk] | None = None) -> AIContext:
    return AIContext(
        system_instructions="Use only supplied knowledge.",
        user_question="What are the admissions requirements?",
        model_name="test/model",
        retrieved_knowledge=chunks if chunks is not None else [valid_chunk()],
        grounding_instructions="Ground every claim in supplied knowledge.",
    )


def assembled_context() -> AIContext:
    request = AIRequest(
        user_query="What are the admissions requirements?",
        retrieval_scope=RetrievalScope(institution_id=uuid4()),
        retrieved_chunks=[valid_chunk()],
        model_name="test/model",
    )
    return assemble_context(request)


def test_valid_context_reaches_provider_and_all_fields_are_preserved() -> None:
    context = assembled_context()
    provider = DeterministicProvider()

    response = AIGenerationService(provider).generate(context)

    assert provider.contexts == [context]
    received = provider.contexts[0]
    assert received.system_instructions == context.system_instructions
    assert received.user_question == context.user_question
    assert received.retrieved_knowledge == context.retrieved_knowledge
    assert received.grounding_instructions == context.grounding_instructions
    assert received.model_name == context.model_name
    assert response.model_used == "test/model"


def test_provider_output_maps_to_ai_response_without_inventing_sources() -> None:
    context = valid_context()
    chunk = context.retrieved_knowledge[0]
    expected_reference = SourceReference(
        chunk_id=chunk.chunk_id,
        quote=chunk.text,
    )
    provider = DeterministicProvider(
        GenerationResult(
            answer="The application is required.",
            source_references=[expected_reference],
            status="success",
            model_used="provider/model",
            metadata={"trace": "test"},
        )
    )

    response = generate_response(context, provider)

    assert response == AIResponse(
        answer="The application is required.",
        source_references=[expected_reference],
        status="success",
        model_used="provider/model",
        metadata={"trace": "test"},
    )
    assert response.source_references == [expected_reference]


def test_unscoped_provider_reference_is_rejected() -> None:
    context = valid_context()
    provider = DeterministicProvider(
        GenerationResult(
            answer="Unsupported.",
            source_references=[SourceReference(chunk_id=uuid4(), quote="Fabricated")],
        )
    )

    with pytest.raises(AppError, match="ungrounded source reference"):
        generate_response(context, provider)


def test_empty_context_preserves_insufficient_context_and_skips_provider() -> None:
    context = valid_context([])

    class FailingProvider:
        def generate(self, _context: AIContext) -> GenerationResult:
            raise AssertionError("provider must not be called for empty context")

    response = generate_response(context, FailingProvider())

    assert response.status == "insufficient_context"
    assert response.answer is None
    assert response.source_references == []
    assert response.model_used == "test/model"


def test_provider_failure_is_surfaced_as_app_error() -> None:
    class FailingProvider:
        def generate(self, _context: AIContext) -> GenerationResult:
            raise RuntimeError("provider failure")

    with pytest.raises(AppError) as error:
        generate_response(valid_context(), FailingProvider())

    assert error.value.code == "GENERATION_FAILED"
    assert error.value.status_code == 500
    assert error.value.__cause__ is not None


def test_invalid_provider_result_is_surfaced_as_app_error() -> None:
    class InvalidProvider:
        def generate(self, _context: AIContext) -> object:
            return object()

    with pytest.raises(AppError, match="invalid result"):
        generate_response(valid_context(), InvalidProvider())


def test_service_does_not_call_retrieval_database_or_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("external dependency was called")

    monkeypatch.setattr("app.db.supabase.get_admin_client", fail)
    monkeypatch.setattr("app.services.retrieval.retrieve", fail, raising=False)
    monkeypatch.setattr(httpx.Client, "post", fail)

    response = generate_response(valid_context(), DeterministicProvider())

    assert response.status == "success"


def test_deterministic_provider_behavior_is_repeatable() -> None:
    first = generate_response(valid_context(), DeterministicProvider())
    second = generate_response(valid_context(), DeterministicProvider())

    assert first == second


def test_service_accepts_provider_abstraction_without_production_provider() -> None:
    provider: GenerationProvider = DeterministicProvider()

    response = AIGenerationService(provider).generate(valid_context())

    assert response.status == "success"
    assert not hasattr(provider, "post")


def test_non_context_input_is_rejected() -> None:
    with pytest.raises(TypeError, match="validated AIContext"):
        generate_response({"user_question": "question"}, DeterministicProvider())  # type: ignore[arg-type]
