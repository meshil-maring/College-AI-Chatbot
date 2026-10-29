"""Keep selected-resource conversations immutable and revalidate every boundary."""

from uuid import UUID

from app.core.errors import AppError
from app.schemas.ai.conversation import ConversationCreate
from app.services.knowledge.resources.operations import execute
from app.services.ai.conversation_intent import ConversationIntent


def read_context(client, actor, tenant, source):
    return execute('read_resource_chat_context', client=client,
        actor=str(actor), tenant=str(tenant), source_id=str(source))


def restored_context(client, actor, conversation):
    source = conversation.get('knowledge_source_id')
    if not source:
        return None
    try:
        return read_context(client, actor, conversation['resource_institution_id'], source)
    except AppError as failure:
        if failure.status_code not in {403, 404}:
            raise
        return {'knowledge_source_id': str(source), 'title': None, 'available': False}


def resolve_conversation(client, request, actor, session_id, *, get, create):
    conversation_id = request.conversation_id or request.session_id or session_id
    conversation = get(client, conversation_id)
    if conversation is not None and str(conversation['user_id']) != str(actor):
        raise AppError('Conversation not found', 404, 'CONVERSATION_NOT_FOUND')
    selected = request.resource_id
    if conversation is not None:
        source = conversation.get('knowledge_source_id')
        if selected and str(selected) != str(source):
            raise AppError('Start a new chat to choose another resource.', 409, 'CONVERSATION_SCOPE_CHANGED')
        if source and str(conversation.get('resource_institution_id')) != str(request.institution_id):
            raise AppError('Conversation scope changed. Start a new chat.', 409, 'CONVERSATION_SCOPE_CHANGED')
        selected = source
    context = None
    if selected:
        try:
            context = read_context(client, actor, request.institution_id, selected)
        except AppError as failure:
            if conversation is not None and failure.status_code in {403, 404}:
                raise AppError('Resource access changed. Start a new chat.', 409, 'CONVERSATION_ACCESS_CHANGED') from failure
            raise
        request.knowledge_source_id = UUID(str(selected))
    if conversation is None:
        conversation = create(client, ConversationCreate(user_id=UUID(str(actor)), title=request.user_query[:60],
            knowledge_source_id=selected, resource_institution_id=request.institution_id if selected else None),
            conversation_id=conversation_id)
    return conversation, context


def scoped_intent(intent, context):
    if context and intent in {ConversationIntent.GENERAL_KNOWLEDGE, ConversationIntent.AMBIGUOUS}:
        return ConversationIntent.AUTHENTICATED_COLLEGE_KNOWLEDGE
    return intent


def bind_policy(policy, context):
    if not context:
        return policy
    source = str(context['knowledge_source_id'])
    if (set(policy['sources']) - {source} or set(policy['versions'].values()) - {source}
            or policy['institution_id'] != str(context['institution_id'])
            or (source in policy['sources'] and str(policy['sources'][source]) != str(context['policy_version']))):
        raise AppError('Resource scope changed. Start a new chat.', 409, 'CONVERSATION_SCOPE_CHANGED')
    return {**policy, 'sources': {source: context['policy_version']}}


def history_matches(policy, conversation):
    source = conversation.get('knowledge_source_id')
    if not source:
        return True
    if not isinstance(policy, dict) or not isinstance(policy.get('sources'), dict) or not isinstance(policy.get('versions'), dict):
        return False
    return (isinstance(policy, dict) and policy.get('institution_id') == str(conversation['resource_institution_id'])
        and set(policy.get('sources', {})) == {str(source)}
        and set(policy.get('versions', {}).values()) <= {str(source)})
