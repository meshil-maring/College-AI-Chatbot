from app.core.errors import AppError
from app.schemas.generation import AIContext, AIResponse
from app.services.generation_provider import GenerationProvider, GenerationResult


class AIGenerationService:
    """Generate an AI response from an already assembled context."""

    def __init__(self, provider: GenerationProvider) -> None:
        self._provider = provider

    def generate(self, context: AIContext) -> AIResponse:
        if not isinstance(context, AIContext):
            raise TypeError("context must be a validated AIContext")

        if not context.retrieved_knowledge:
            return AIResponse(
                status="insufficient_context",
                model_used=context.model_name,
            )

        try:
            result = self._provider.generate(context)
        except Exception as exc:
            raise AppError(
                "AI generation failed",
                status_code=500,
                code="GENERATION_FAILED",
            ) from exc

        if not isinstance(result, GenerationResult):
            raise AppError(
                "AI provider returned an invalid result",
                status_code=500,
                code="INVALID_GENERATION_RESULT",
            )

        chunk_ids = {chunk.chunk_id for chunk in context.retrieved_knowledge}
        if any(reference.chunk_id not in chunk_ids for reference in result.source_references):
            raise AppError(
                "AI provider returned an ungrounded source reference",
                status_code=500,
                code="UNGROUNDED_SOURCE_REFERENCE",
            )

        try:
            return AIResponse(
                answer=result.answer,
                source_references=result.source_references,
                status=result.status,
                model_used=result.model_used or context.model_name,
                metadata=result.metadata,
            )
        except ValueError as exc:
            raise AppError(
                "AI provider returned an invalid response",
                status_code=500,
                code="INVALID_GENERATION_RESULT",
            ) from exc


def generate_response(context: AIContext, provider: GenerationProvider) -> AIResponse:
    """Generate an AI response through the provider abstraction."""
    return AIGenerationService(provider).generate(context)