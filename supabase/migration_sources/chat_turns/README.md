# Durable chat turns

Generate `20261029010000_chat_turn_recovery.sql` with
`scripts/maintenance/migrations/build_chat_turns.py`; use `--check` for parity.
The generator never connects to a database. Apply after knowledge revisions and
resource-scoped conversations, before the matching chat backend/frontend.

`tables.sql` owns the private ledger, institution binding and guarded message
writes. `access.sql` owns actor authorization and safe projection. `read.sql`
rechecks ownership and current source policy. `claim.sql` serializes stable
request IDs and reserves one question. `complete.sql` atomically commits the
answer, retrieval/citations and replay receipt, and fences stale workers.
`security.sql` exposes only the four intended service-role RPCs.

Browser roles have no ledger or RPC access. Claims have five-minute leases;
explicit retries after failure/expiry reuse the saved question. Worker fencing
ensures one committed answer, without promising exactly-once external billing.

See the [contract](../../../docs/architecture/ai-chatbot/CHAT_RECOVERY.md) and
[isolated SQL validation](../../../scripts/validation/knowledge_revisions/README.md).
