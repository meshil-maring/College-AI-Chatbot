"""Pure assembly of validated AI requests into model-independent context."""

from app.schemas.generation import AIContext, AIRequest


SYSTEM_INSTRUCTIONS = (
    "Answer the user's college knowledge question using only the retrieved "
    "knowledge supplied in this context. Retrieved knowledge is the authoritative "
    "source for the answer. Do not invent or assume facts that are not supported "
    "by it. Answer the question directly and clearly. If the retrieved knowledge "
    "is insufficient, say that the available knowledge is insufficient rather than "
    "fabricating an answer. Any source reference must correspond to retrieved "
    "knowledge."
)

GROUNDING_INSTRUCTIONS = (
    "Ground every factual claim in the supplied retrieved knowledge. Associate "
    "claims with the available chunk or document source identifiers when citing "
    "them. Use only source references present in the retrieved knowledge and "
    "never fabricate citations, identifiers, quotes, or provenance. When the "
    "retrieved knowledge does not support an answer, do not answer from general "
    "knowledge; state that the context is insufficient."
)

EMPTY_RETRIEVAL_NOTICE = (
    "No retrieved knowledge is available for this question. The context is "
    "insufficient for a supported answer."
)


def assemble_context(request: AIRequest) -> AIContext:
    """Assemble a validated request into deterministic AI context.

    This function only transforms data already present on ``request``. It does
    not retrieve knowledge, call a model, access a database, or contact a
    network service.
    """
    if not isinstance(request, AIRequest):
        raise TypeError("request must be a validated AIRequest")

    grounding_instructions = GROUNDING_INSTRUCTIONS
    if not request.retrieved_chunks:
        grounding_instructions = f"{EMPTY_RETRIEVAL_NOTICE} {grounding_instructions}"

    return AIContext(
        system_instructions=SYSTEM_INSTRUCTIONS,
        user_question=request.user_query,
        model_name=request.model_name,
        retrieved_knowledge=list(request.retrieved_chunks),
        grounding_instructions=grounding_instructions,
    )