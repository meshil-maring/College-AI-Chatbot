"""Pure assembly of validated AI requests into model-independent context."""

from app.schemas.generation import AIContext, AIRequest, ConversationTurn


SYSTEM_INSTRUCTIONS = (
    "Answer the user's college knowledge question using only the retrieved "
    "knowledge supplied in this context. Retrieved knowledge is the authoritative "
    "source for the answer. Do not invent or assume facts that are not supported "
    "by it. Answer the question directly and clearly. If the retrieved knowledge "
    "is insufficient, say that the available knowledge is insufficient rather than "
    "fabricating an answer. Any source reference must correspond to retrieved "
    "knowledge. Conversation history, when supplied, is conversational context, "
    "not institutional knowledge: use it to understand the user's intent, resolve "
    "references such as 'that' or 'the previous one', and answer questions about "
    "the conversation itself, such as identifying a previous user question or a "
    "previous assistant response. Never treat a previous assistant statement as "
    "verified institutional knowledge; factual college claims must still be "
    "supported by retrieved knowledge, and insufficiency still applies when "
    "retrieved knowledge does not support the factual claim being asked about."
)

GROUNDING_INSTRUCTIONS = (
    "Ground every factual claim about the college or institution in the supplied "
    "retrieved knowledge. Associate claims with the available chunk or document "
    "source identifiers when citing them. Use only source references present in "
    "the retrieved knowledge and never fabricate citations, identifiers, quotes, "
    "or provenance. When the retrieved knowledge does not support a factual "
    "college claim, do not answer from general knowledge and do not substitute "
    "conversation history for institutional knowledge; state that the context is "
    "insufficient. This grounding requirement applies to factual college claims "
    "only; questions about the conversation itself (for example, what was asked "
    "or said previously) may be answered directly from conversation history."
)

EMPTY_RETRIEVAL_NOTICE = (
    "No retrieved knowledge is available for this question. If the question "
    "requires institutional facts, the context is insufficient for a supported "
    "answer. If the question is only about the conversation itself, conversation "
    "history may still be used to answer it."
)


def assemble_context(request: AIRequest, conversation_history: list[ConversationTurn] = None) -> AIContext:
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
        conversation_history=conversation_history or request.conversation_history,
        retrieval_query=request.retrieval_query,
    )