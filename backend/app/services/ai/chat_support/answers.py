"""Keep the legacy persistence path separate from atomic turn completion."""

from uuid import UUID

from app.schemas.ai.conversation import MessageCreate


def save_legacy_answer(client, conversation_id, result, policy, *, create, sequence, persist,
                       retrieval_query, retrieved_chunks, references, latency_ms):
    if result.answer is None:
        return None
    assistant = create(client, MessageCreate(conversation_id=conversation_id,
        message_sequence=sequence(client, conversation_id), message_type='assistant',
        content_text=result.answer, knowledge_policy=policy))
    message_id = UUID(assistant['message_id'])
    usage = result.metadata.get('usage', {}) if isinstance(result.metadata, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    persist(conversation_id=conversation_id, message_id=message_id, retrieval_query=retrieval_query,
        retrieved_chunks=retrieved_chunks, source_references=references, generation_result=result,
        input_tokens=usage.get('prompt_tokens'), output_tokens=usage.get('completion_tokens'), latency_ms=latency_ms)
    return message_id
