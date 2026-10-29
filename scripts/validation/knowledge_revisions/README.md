# Knowledge revision database validation

From the repository root:

```powershell
backend/.venv/Scripts/python.exe scripts/validation/knowledge_revisions/verify.py
```

Uses the cached PostgreSQL image and local Docker Desktop safety checks from
`disposable_container.py`. The run owns its container, disables networking,
publishes no ports, uses memory-backed storage and removes only its own container.
It never reads application credentials or connects to a configured project.

The runner replays prior migrations, seeds fictional source/document metadata,
applies the generated knowledge revision migration, then exercises actual SQL
constraints, deferred publication transitions and database-role privileges.
Fixtures contain no uploaded files, external generation or embedding calls.

Checks cover full migration rollback, conservative backfill and data preservation; empty/unknown/combined
audiences; tenant/source/version FKs; review and publication provenance; frozen
metadata/audiences/manifests; replacement publication; failed indexing; policy
concurrency; real anonymous/authenticated/service-role denial; and a concurrent
audience edit invalidating a stale review token. `workflow/` also exercises the
actual service-only writers, all audience matrix cells, scoped metadata/vector
reads, admin-only decisions, upload staging, failed-index retries, audit rollback
and history/public-response revocation. They also reject legacy chunking that
would purge reviewed chunks or embeddings. Fixture helpers run only inside this
disposable database; deployed RPC authorization is tested independently of them.
`workflow/service_transactions.sql` additionally commits each workflow operation
as the actual service role, including deferred checks after each writer returns.
Private integrity helpers remain unavailable as direct service capabilities.
The runner also applies the resource-chat migration and exercises actual context
eligibility, audience/tenant denial, service-only privileges, immutable
conversation source/institution/owner and revocation after unpublication.

The chat-turn migration adds durable claim/replay checks, failure and expired
lease recovery, stale/null worker denial, transactional answer/citation rollback,
insufficient-context persistence and actor/resource revocation. Independent
simultaneous service transactions must claim one worker and save one question.

The history-citation reader checks owned messages across all institution roles,
source order/metadata, legacy records, current access and cross-message retrieval
provenance. It excludes uncited, duplicate, unselected and outside-policy evidence,
and denies browser-role access. The tests use actual committed service reads.

Keep logs under repository-level `logs/backend/`. Also run the offline generator
parity tests in `backend/tests/knowledge/test_revision_migration.py`, backend
structure validation and the disposable-container safety regression tests.
