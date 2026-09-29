# Phase 7.9.3 — Staging Database & Migration Validation

**Status: BLOCKED — no isolated staging/disposable database is available in this environment.**

## Safety outcome

The currently linked Supabase project was not used for schema changes. No migrations were pushed, repaired, marked applied, or manually executed; no production-like data was changed. The Phase 7.9.3 database acceptance checks therefore remain unverified rather than being inferred from source SQL or application tests.

## Staging environment

| Item | Result |
|---|---|
| Environment | No staging target established |
| Staging project identity | Not available |
| Isolation from linked project | Cannot be established without a staging target |
| Local Supabase | Unavailable: Docker CLI exists, but the Docker engine pipe is absent |
| Separate Supabase project | No repository evidence/configuration identifies an existing staging project |
| Current linked project | Identifier withheld; left untouched |

`docker version` returned client information but exited 1 because it could not connect to the Docker engine. Local Supabase startup was not attempted after that result. The Supabase CLI version probe could not initialize its telemetry file due filesystem access denial; no project-list or remote mutation command was run. The linked project is not a staging substitute.

## Migration inventory and order

The repository contains 15 migration files. The three named migrations are present. The normal timestamp order includes earlier schema prerequisites and `20260915000000_phase_6_13_organization_institution_tenancy.sql` after Phase 6.11 and before Phase 7.2; files must be applied by the repository migration mechanism in timestamp order, not cherry-picked or reordered. Static dependency review indicates:

- Phase 6.11 requires the existing `students` and `institutions` tables and `gen_random_uuid()`; the migration creates `student_notifications`, four indexes (including the partial unread and deduplication indexes), a tenant-guard function and trigger, and grants table DML to `service_role`.
- Phase 7.2 requires the knowledge-source, document/version, processing-run, chunk, and embedding schema from earlier migrations. It adds `knowledge_sources.visibility` with restricted default and a check constraint, backfills published FAQ/notice/handbook sources to public, adds a policy index, and creates the public retrieval RPC. It revokes execution from `PUBLIC`, `anon`, and `authenticated`, granting it to `service_role`.
- Phase 7.4 replaces the RPC with hardening: match count 1–20, completed processing runs, 1536-dimension embeddings, and a bounded limit; its grant posture matches Phase 7.2.

Static review found no explicit table/data deletion. Phase 7.2 does contain an UPDATE backfill and replaces the visibility constraint; it is not safe to apply to an unverified live database. Phase 6.11 uses `CREATE TABLE/INDEX IF NOT EXISTS` and `CREATE OR REPLACE FUNCTION`, but its `CREATE TRIGGER` is not guarded against an already-existing trigger. No migration was run, so parser validity, actual dependencies, idempotency, ledger agreement, and rollback behavior have not been proven against PostgreSQL.

## Database and security verification

| Check | Staging result |
|---|---|
| Migration ledger | NOT VERIFIED |
| Phase 6.11 objects | NOT VERIFIED |
| Phase 7.2 visibility schema / policy | NOT VERIFIED |
| Phase 7.4 public RPC definition | NOT VERIFIED |
| RPC signature / return shape / bounded limit | Static source reviewed; database behavior NOT VERIFIED |
| Grants and direct table access | Static grants reviewed; effective privileges/RLS NOT VERIFIED |
| Required vector and policy indexes | Static SQL reviewed; database indexes NOT VERIFIED |
| Eligibility matrix / tenant isolation | NOT RUN |
| Public retrieval, provenance, context assembly | NOT RUN against a database |
| Generation, empty-context, prompt injection | NOT RUN against staging |
| Public/authenticated separation | NOT RUN against staging |
| Synthetic data / student-data isolation | No data created or copied |

The RPC is declared `SECURITY INVOKER`; the intended caller is `service_role`. The SQL explicitly withholds RPC execution from anonymous and authenticated roles. This source review is not a substitute for verifying actual role grants, RLS, or behavior in an isolated database.

## Recovery

No isolated staging export/backup or restore was possible because no staging database exists. **Staging backup/export: UNVERIFIED. Staging restore: UNVERIFIED.** A disposable database must be backed up/exported and restored to a second isolated database, followed by schema and RPC checks, before recovery can be called verified.

## Migration gate

Do not apply any migration to the linked remote project until all boxes are evidenced:

- [ ] Confirm a staging/disposable target and prove it differs from the linked project.
- [ ] Establish a restorable recovery point and test restore in isolation.
- [ ] Run the complete migration history, in normal timestamp order, on a fresh isolated database.
- [ ] Verify the migration ledger agrees with schema; do not use migration repair or edit the ledger.
- [ ] Verify Phase 6.11, Phase 7.2 and Phase 7.4 objects, grants, RLS, and indexes.
- [ ] Run synthetic public eligibility and cross-tenant tests, public retrieval/provenance, and relevant RAG regressions.
- [ ] Record the exact target identity in a restricted operational record (redact credentials and identifiers in public reports).

On any migration failure: stop immediately; capture the sanitized error; do not apply later migrations; restore the disposable database if needed; investigate and revise/test a migration through the normal review process. Application rollback does not reverse database migrations. Never edit migration history to bypass a failure.

## Verification commands and results

- `docker version` — **FAILED to reach Docker engine** (daemon unavailable).
- `supabase --version` — **BLOCKED** by CLI telemetry-file access denial; no Supabase database command was run.
- `uv run pytest -q tests` — **FAILED during collection (77 errors)** because the inherited `DEBUG` environment value is `release`, which is invalid for the boolean setting.
- `$env:DEBUG='false'; uv run pytest -q tests` — **BLOCKED** because `uv` could not initialize its cache outside the workspace (access denied).
- `$env:DEBUG='false'; .\\.venv\\Scripts\\python.exe -m pytest -q tests` — **FAILED**: 2 diagnostics assertions failed because diagnostics are suppressed with `DEBUG=false`; 1 test errored because the sandbox denied pytest's default temp directory; 2,125 passed, 15 skipped.
- `$env:DEBUG='true'; .\\.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider --basetemp='F:\\Git Project\\CollegeAIChatbot\\backend\\.pytest-tmp' tests` — **PASS**: 2,128 passed, 15 skipped, 6 warnings (76.18s).
- `npm.cmd run test -- --pool=vmThreads --maxWorkers=1` — **PASS** (50 files, 431 tests).
- `npx.cmd tsc --noEmit -p tsconfig.json` — **PASS** (exit 0).
- `npm.cmd run build` — **PASS** (Vite production build, 97 modules transformed; exit 0).
- `git diff --check` — **PASS** (exit 0; only line-ending warnings).

The local/remote staging database migration dry run was not available. No Phase 7.9.3 DB/RAG smoke test is claimed. `uv run` could not run here because it attempted to initialize a user-level cache outside the writable workspace; the existing backend virtualenv was used for the authoritative pytest run.

## Decision

```text
Migration chain locally validated: NO (no PostgreSQL migration execution)
Migration chain staging validated: NO
Recovery verified: NO
Remote migration: BLOCKED
Production-like remote database modified: NO
```

Remaining blocker: an explicitly authorized, isolated local Supabase or separate staging project with working database access and a verified restore path. Once supplied, repeat fresh-database migration application and database-level checks before considering remote production migration.
