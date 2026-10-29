# Resource-scoped conversations

Maintained sources for `20261029000000_resource_scoped_conversations.sql`.
Generate with `python scripts/maintenance/migrations/build_resource_chat.py`;
check parity with the same command plus `--check`.

`context.sql` resolves indexed, published, audience-authorized resource metadata
through a service-only function with active `ai.chat` grants and a source share
lock. `conversations.sql` stores immutable source/institution context, enforces a
composite tenant FK and checks scope eligibility when creating a conversation.
Existing ordinary conversations remain unscoped and cannot be rebound.

Deploy after the audience/revision migration and before its matching backend.
No credentials, external calls or project migration application occur during
generation. The [SQL runner](../../../scripts/validation/knowledge_revisions/README.md)
checks actual service-role operations, audience denial and immutable context.
See the [feature contract](../../../docs/architecture/ai-chatbot/RESOURCE_CHAT.md).
