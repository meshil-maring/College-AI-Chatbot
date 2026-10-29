"""Assemble ordinary chat context without private academic readers."""

from app.schemas.ai.generation import AIRequest, RetrievalScope
from app.schemas.knowledge.retrieval import RetrievalRequest
from app.services.ai.context import assemble_context
from app.services.ai.conversation_intent import ConversationIntent, build_direct_context


def build_retrieval_request(request, query, top_k, actor_user_id=None):
    return RetrievalRequest(
        query=query,
        top_k=top_k,
        institution_id=request.institution_id,
        knowledge_source_id=request.knowledge_source_id,
        document_id=request.document_id,
        document_version_id=request.document_version_id,
        processing_run_id=request.processing_run_id,
        model_name=request.model_name,
        actor_user_id=actor_user_id,
    )


def build_chat_context(
    *, request, retrieval_query, conversation_history, retrieved_chunks, intent
):
    if intent in {ConversationIntent.CASUAL, ConversationIntent.GENERAL_KNOWLEDGE}:
        return build_direct_context(request.user_query, conversation_history)
    if intent in {
        ConversationIntent.AI_IDENTITY,
        ConversationIntent.AMBIGUOUS,
        ConversationIntent.RESTRICTED_ACTION,
        ConversationIntent.PERSONAL_DATA,
    }:
        return None
    return assemble_context(
        AIRequest(
            user_query=request.user_query,
            retrieval_query=retrieval_query
            if retrieval_query != request.user_query
            else None,
            retrieval_scope=RetrievalScope(
                institution_id=request.institution_id,
                knowledge_source_id=request.knowledge_source_id,
                document_id=request.document_id,
                document_version_id=request.document_version_id,
                processing_run_id=request.processing_run_id,
            ),
            retrieved_chunks=retrieved_chunks,
            model_name=request.model_name,
            conversation_history=conversation_history,
        ),
        conversation_history=conversation_history,
    )
