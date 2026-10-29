# Resource-specific Ask AI

Implemented 29 October 2026. The prepared additive migration is
`20261029000000_resource_scoped_conversations.sql`; it follows the audience and
revision migration. Neither migration is applied to an existing project by the
verification runners.

## Conversation contract

`GET /api/v1/knowledge/resources/{source_id}/chat-context` confirms current
institution, active `ai.chat` grants, audience, publication, effective dates and
an indexed manifest with embedded chunks. It returns only `knowledge_source_id`,
`title` and `available`. Unavailable or unauthorized resources return 404;
missing schema remains an explicit 503.

`POST /api/v1/generation/chat` accepts optional `resource_id`. A first question
creates an owned conversation with an immutable source and institution. Existing
scoped conversations inherit their stored resource even when a follow-up omits
the selector. Switching source/institution or attaching a resource to an existing
ordinary conversation returns 409 before saving a turn or calling a provider.
Internal document/version filters, retrieved chunks and provider settings remain
outside the HTTP request contract.

`ChatResponse.resource_context` and `ConversationSummary.resource_context` carry
the safe context; ordinary chats return null. History restoration uses the
server's stored context. A resource conversation cannot silently become ordinary
institution chat. New chat from an available resource starts another conversation
for that resource; choosing an ordinary history item restores ordinary chat.

## Retrieval and revocation

Questions classified as general or ambiguous use resource retrieval when scoped.
Casual replies, AI identity and private-data/action refusals retain existing safe
handling. Resource questions without evidence return insufficient context rather
than falling back to general knowledge. Query rewriting and follow-ups retain
the exact source filter.

Every resource response carries its selected source policy, including responses
with no retrieved chunks. Unexpected sources, versions or policy changes abort
the answer. Existing delivery checks reject in-flight revocation. Resource
context is rechecked before every turn and history read. Unavailable history
loses its resource title, replaces its contents with an access-change message
and cannot continue. Mixed-resource provenance is also rejected.

Database triggers enforce immutable conversation source, institution and owner.
A composite FK prevents source/tenant mismatches. Only the trusted backend can
resolve context; the function holds a source share lock while authorizing and
reading its metadata. Browser grants do not expose the context helper directly.

## Shared interface and state

The shared resource details expose Ask AI for permitted readers; drafts have no
entry. Student resource cards use the same eligibility button without adding
file or storage data to their existing metadata contract. All roles enter the
same ChatShell, with a visible resource banner and a route back to resources.

Chat and history state use identity/grant boundaries. Tokens do not enter query
keys, reads consume cancellation signals, and selection/operation guards reject
late callbacks after identity replacement, history selection or new chat.
Renewal preserves the conversation. Unknown resource-chat outcomes offer explicit
[status recovery and safe retry](CHAT_RECOVERY.md); there is no automatic write retry.

## Verification and rollout

Backend tests cover context binding, scope tampering, wrong-source retrieval,
empty evidence, delivery revocation and history redaction. Frontend tests cover
entry permissions, student metadata, restored scope, credential renewal,
duplicate sends and late response/selection retirement. The disposable SQL
runner verifies actual role/audience checks and immutable storage.

The loopback browser runner exercises the real generation API, audience-filtered
SQL retrieval, atomic message/answer/retrieval/citation persistence and history restoration in
temporary PostgreSQL. Identity, object storage and model providers use fictional
local substitutes. Lost-response replay and retry after reload exercise the
durable turn protocol against the same real API and database.

Apply the audience/revision and resource-chat migrations before enabling the
matching backend/frontend. The [configured-service acceptance runner](../../../scripts/validation/chat_live/README.md)
checks actual password authentication, object storage, embeddings and generation,
admin publication, role audiences, history revocation and durable replay. Its
real browser journeys cover all four roles and public chat, source-card reload
and 320px layout. Run-owned accounts are disabled and resource fixtures unpublished
afterward; manifests and screenshots stay in the repository logs folders. Public timeout and
explicit retry handling are documented in [chat recovery](CHAT_RECOVERY.md).
File delivery remains separate work.
