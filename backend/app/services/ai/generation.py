import logging

from app.core.errors import AppError
from app.schemas.ai.generation import AIContext, AIResponse
from app.services.ai.generation_provider import GenerationProvider, GenerationResult
from app.services.ai.generation_qualification import qualified_answer

logger = logging.getLogger(__name__)


class AIGenerationService:
    """Generate an AI response from an already assembled context."""

    def __init__(self, provider: GenerationProvider) -> None:
        self._provider = provider

    def generate(
        self, context: AIContext, *, allow_empty_context: bool = False
    ) -> AIResponse:
        if not isinstance(context, AIContext):
            raise TypeError("context must be a validated AIContext")

        if not context.retrieved_knowledge and not allow_empty_context:
            return AIResponse(
                status="insufficient_context",
                model_used=context.model_name,
            )

        try:
            result = self._provider.generate(context)
        except AppError as exc:
            logger.warning("event=generation_dependency_failed code=%s public=%s", exc.code, context.public)
            if context.public:
                if exc.code == "AI_PROVIDER_TIMEOUT":
                    raise AppError(
                        "Public AI generation timed out. Please try again later.",
                        status_code=504,
                        code="PUBLIC_GENERATION_TIMEOUT",
                    ) from exc
                raise AppError(
                    "Public AI generation is temporarily unavailable.",
                    status_code=503,
                    code="PUBLIC_GENERATION_UNAVAILABLE",
                ) from exc
            raise AppError(
                "AI generation failed",
                status_code=500,
                code="GENERATION_FAILED",
            ) from exc
        except Exception as exc:
            if context.public:
                raise AppError(
                    "Public AI generation is temporarily unavailable.",
                    status_code=503,
                    code="PUBLIC_GENERATION_UNAVAILABLE",
                ) from exc
            raise AppError(
                "AI generation failed",
                status_code=500,
                code="GENERATION_FAILED",
            ) from exc

        if not isinstance(result, GenerationResult):
            if context.public:
                raise AppError(
                    "Public AI generation is temporarily unavailable.",
                    status_code=503,
                    code="PUBLIC_GENERATION_UNAVAILABLE",
                )
            raise AppError(
                "AI provider returned an invalid result",
                status_code=500,
                code="INVALID_GENERATION_RESULT",
            )

        chunk_ids = {chunk.chunk_id for chunk in context.retrieved_knowledge}
        if any(reference.chunk_id not in chunk_ids for reference in result.source_references):
            if context.public:
                raise AppError(
                    "Public AI generation returned an invalid response.",
                    status_code=502,
                    code="PUBLIC_GENERATION_INVALID_RESPONSE",
                )
            raise AppError(
                "AI provider returned an ungrounded source reference",
                status_code=500,
                code="UNGROUNDED_SOURCE_REFERENCE",
            )

        try:
            answer, references = qualified_answer(result.answer, result.source_references, context)
            if context.public and answer and references:
                # The existing public projector extracts these internal markers,
                # then removes them before returning any text to the visitor.
                # Build them from validated selections, never model-written IDs.
                markers = " ".join(
                    f"[Retrieved chunk {reference.chunk_id}]"
                    for reference in references
                )
                answer = f"{answer}\n\n{markers}"
            return AIResponse(
                answer=answer,
                source_references=references,
                status=result.status,
                model_used=result.model_used or context.model_name,
                metadata=result.metadata,
            )
        except ValueError as exc:
            if context.public:
                raise AppError(
                    "Public AI generation returned an invalid response.",
                    status_code=502,
                    code="PUBLIC_GENERATION_INVALID_RESPONSE",
                ) from exc
            raise AppError(
                "AI provider returned an invalid response",
                status_code=500,
                code="INVALID_GENERATION_RESULT",
            ) from exc


def generate_response(context: AIContext, provider: GenerationProvider) -> AIResponse:
    """Generate an AI response through the provider abstraction."""
    return AIGenerationService(provider).generate(context)
