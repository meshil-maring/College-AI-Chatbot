# Durable signed-in chat recovery

Implemented 29 October 2026. Migration `20261029010000_chat_turn_recovery.sql`
follows the audience/revision and resource-conversation migrations. Deploy the
migration before enabling the matching backend and frontend.

## API and persistence

Signed-in `POST /api/v1/generation/chat` accepts optional UUID `turn_id` with a
stable `session_id` or `conversation_id`. The shared UI creates these before
sending. Repeated requests must match actor, institution, conversation, session,
question and resolved resource. A completed request returns its saved receipt
without calling a model. An active request returns `409 CHAT_TURN_PENDING`.

`GET /api/v1/generation/turns/{turn_id}` is an authenticated, read-only status
endpoint. It returns the authorized request and either processing, failed or
completed state, retry eligibility and a safe completed response. It rechecks
current actor grants, ownership, tenant, resource eligibility and answer policy.
Revocation prevents replay. It never exposes leases, worker tokens, prompts or
provider diagnostics. Conversation summaries identify an unfinished turn with
`pending_turn_id`, allowing recovery after reload without browser-stored tokens
or request payloads.

The service-only claim RPC serializes each actor/turn and conversation. It saves
one question, pins the conversation institution and permits one unfinished turn
per conversation. Failed or expired claims reuse the question with a new worker
token. Raw service message inserts cannot interleave with managed conversations.

Completion validates the current worker and knowledge policy, then commits the
assistant message, AI response, retrieval operation, retrieved chunks, citations
and safe receipt in one transaction. Invalid citations or changed access roll
back all answer records. A worker replaced after lease expiry cannot complete or
fail its replacement. Insufficient context is a saved terminal response.

Unkeyed API callers retain their legacy workflow on unmanaged conversations;
the current shared UI always uses durable turns. Public chat remains stateless.

## Interface and failures

The POST transport has a 90-second deadline with no automatic write retry.
An uncertain outcome offers **Check reply**, which only reads status. It restores
an already completed answer without resending the question. Active work stays
pending; a failed, expired or confirmed missing request offers **Retry reply**
using the same ID and saved question. Further sends are blocked during recovery.
History can restore unfinished turns after reload. Recovered server message IDs
prevent duplicate display if a history read already contains the saved answer.

The same components serve admin, faculty, staff and student chat. Selection,
new-chat and identity guards discard late callbacks. Query keys exclude tokens;
status reads consume cancellation signals and retire their private cache on
selection or identity change. Credential renewal retains the conversation.

The five-minute lease fences database completion, not external model execution.
If an original worker continues beyond an expired lease, an explicit retry can
start another provider call. Only one answer can commit; exactly-once provider
billing is not guaranteed. There is no automatic retry loop or background worker.

## Verification

Backend tests cover claim/replay, failed work, permission/error translation,
HTTP contracts and atomic completion payloads. Frontend tests cover lost replies,
stable retry IDs, running status, reload restoration, duplicate display, renewal,
late callbacks, access revocation and deadline cleanup.

The disposable SQL runner tests real service transactions, rollback on invalid
receipts, expired-worker fencing, revocation and simultaneous requests. The
loopback browser runner uses real FastAPI and PostgreSQL with fictional identity,
storage and model boundaries. It drops a committed HTTP response, replays it,
then fails and retries a question after reload across all management roles.

History source cards are implemented through migration
`20261029020000_history_citations.sql`. The history API batches owner-scoped,
current-policy and retrieval-provenance checks, then returns `MessageSummary.sources`
for the shared card UI. It restores valid legacy citations as well as durable
turns, without fabricating missing records. Access changes redact affected history.
Internal model history skips this presentation read.

Public timeout/retry handling is implemented in the
[public-chat feature](../../../frontend/src/features/publicChat/README.md).
Its 35-second deadline includes response-body loading; Stop waiting preserves
the question, and Retry-After gates explicit retries without automatic resends.
Public history stays browser-local and the endpoint remains stateless. Each
retry is a new anonymous generation call, separate from durable signed-in turns.

The [configured-service acceptance runner](../../../scripts/validation/chat_live/README.md)
also checks real Auth, storage, embeddings and generation. Signed-in answers
replay the same completed turn and restore identical canonical source cards.
It checks explicit same-ID recovery for confirmed failed provider work and uses
normal browser login for all roles, with run-owned identities disabled afterward.
