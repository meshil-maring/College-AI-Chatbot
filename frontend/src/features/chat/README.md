# Shared chat

`ChatShell` and `session/ChatSession` compose the same conversation, input, history and citation UI for
all roles. Its session component is keyed by authenticated identity, institution,
generation, effective grants and initial resource. `ResourceChatBanner` identifies
scoped conversations and marks unavailable context without retaining its title.

`content/AnswerContent` renders assistant Markdown in public and signed-in chat:
paragraphs, emphasis, lists, headings, code and tables share token-based styles.
HTML remains escaped, images are omitted, and user messages remain plain text.
The presentation helper also restores clear numbered bold sections in older
single-line replies without changing stored messages or new multiline Markdown.

`resource/AskResourceAi` confirms server eligibility before entry;
`resource/ResourceChatView` supplies the shared return-to-resources flow for
management and student resources. No draft-preview or storage link is implied.

`hooks/useChat` owns guarded sends and resource selection. `state/chatMessages`
owns presentation/error mapping. `hooks/useConversationHistory` uses the shared
`state/conversationQueries` options, cancellation and navigation-cache policy.
Tokens stay outside keys. Late replies and selections cannot change a retired
identity or a newly selected conversation. Renewal retains current context.

Restored messages retain the history API's `sources`, using the same `SourceCard`
as live replies. User messages ignore source fields. Source order, quotes, titles,
sections and scores remain server-authoritative; missing legacy citations stay empty.

Only the server can establish a conversation's immutable resource scope.
Restoration uses its returned context; a response with missing/mismatched scope
is never displayed as a resource answer. Source revocation clears current
messages and disables continuation. Unknown resource-send outcomes are not
automatically retried.

`recovery/` owns status queries, recovery state and shared Check reply/Retry reply
controls. The transport deadline does not retry writes. Stable turn IDs recover
committed answers and explicitly retry failed work without adding another question.
Unfinished turns restore from history after reload. See the
[recovery contract](../../../../docs/architecture/ai-chatbot/CHAT_RECOVERY.md).

See the [resource-chat contract](../../../../docs/architecture/ai-chatbot/RESOURCE_CHAT.md).
Tests live in `__tests__/`; keep the chat root within 15 files and each maintained
code/test file within 250 lines. Browser evidence belongs under `logs/frontend/`.
