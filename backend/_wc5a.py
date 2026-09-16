"""
Append the main process_chat_request function to public_chat.py.
Split into two parts due to size.
Part A: function signature through step 2.
"""

import os
os.chdir('F:\\Git Project\\CollegeAIChatbot\\backend')

part_a = r'''
# ============================================================================
# Main entry point
# ============================================================================


def process_chat_request(
    request: ChatRequest,
    context: SessionContext,
    provider: GenerationProvider,
) -> ChatResponse:
    """Public-path equivalent of app.services.chat.process_chat_request.

    Ownership model is identical to the authenticated path - same
    ConversationCreate shape, same background persistence, same bounded
    turn history - but every public conversation is owned by PUBLIC_USER_ID
    so the public endpoint cannot read or write into any authenticated
    user's conversation or message rows.
    """
    if not isinstance(request, ChatRequest):
        raise TypeError("request must be a ChatRequest")
    if not isinstance(context, SessionContext):
        raise TypeError("context must be a SessionContext")

    timings: dict = {}
    request_start = time.perf_counter()
    client = get_admin_client()

    # Step 1: Resolve or create conversation (owned by PUBLIC_USER_ID)
    conversation_start = time.perf_counter()
    user_id = PUBLIC_USER_ID
    conversation_id = (
        request.conversation_id
        or request.session_id
        or context.session_id
    )
    conversation = get_conversation(client, conversation_id)

    if conversation is None:
        title = (
            request.user_query[:60]
            if len(request.user_query) > 60
            else request.user_query
        )
        conversation = create_conversation(
            client,
            ConversationCreate(
                user_id=user_id,
                title=title,
                status="active",
            ),
            conversation_id=conversation_id,
        )
        conversation_id = UUID(conversation["conversation_id"])
    else:
        conversation_id = UUID(conversation["conversation_id"])
    timings["conversation_resolution_ms"] = int(
        (time.perf_counter() - conversation_start) * 1000
    )

    # Step 1.5: Bounded conversation history (copy of chat.py logic)
    history_start = time.perf_counter()
    message_summaries = get_conversation_messages(
        conversation_id,
        user_id,
        conversation=conversation,
    )
    timings["history_latency_ms"] = int(
        (time.perf_counter() - history_start) * 1000
    )
    turns = [
        ConversationTurn(role=s.role, content=s.content)
        for s in message_summaries
    ]
    conversation_history = turns[-20:] if len(turns) > 20 else turns

    # Step 2: Persist user message
    user_sequence = get_next_message_sequence(client, conversation_id)
    create_message(
        client,
        MessageCreate(
            conversation_id=conversation_id,
            message_sequence=user_sequence,
            message_type="user",
            content_text=request.user_query,
        ),
    )
'''

with open('app/services/public_chat.py', 'a') as f:
    f.write('\n' + part_a.lstrip('\n'))

print('Part A appended')
