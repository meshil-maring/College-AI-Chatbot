# Phase 7.9.6 — Phase 3.5 Base Schema Recovery & Migration Chain Repair

**Status: BLOCKED.** The authoritative Phase 3.5 migration cannot be recovered from the repository, its local Git object database, local refs, or project files. No replacement migration was invented.

## Original failure

Phase 7.9.5 enabled Docker Desktop and started the repository-local Supabase PostgreSQL stack. Fresh migration execution failed on the first repository migration:

```text
20250718000000_phase_3_6_embeddings.sql
ERROR: relation "public.knowledge_chunks" does not exist (SQLSTATE 42P01)
At statement: 4
```

The linked remote Supabase project remained off limits throughout this recovery investigation.

## Search strategy and evidence

The investigation searched:

- all reachable local branches and the sole remote-tracking branch;
- all local tags (none exist);
- complete migration path history, including additions, deletions, and renames;
- content history using `-S` and `-G` searches for `knowledge_chunks`, `document_processing_runs`, `Phase 3.5`, and `CREATE TABLE` statements;
- the Phase 3.5 and Phase 3.6 commits and their parent trees;
- repository SQL, schema exports, documentation, lock files, services, repositories, and tests;
- all reflog and stash history; and
- Git's unreachable object database: 106 unreachable commits and 855 unreachable blobs.

No historical or orphaned path matching a Phase 3.5 migration was found. Unreachable commits contain the same Phase 3.6-and-later migration inventory or copies of the schema export. The only orphaned blob matching `Phase 3.5` is a 5,591-byte copy of the text chunking service; it contains no `CREATE TABLE knowledge_chunks` statement.

## Phase 3.5 commit provenance

Git commit:

```text
786b7b1abdc48cefe5415354cfe968e2e470e9eb
Phase 3.5 — Chunking implementation and tests
2026-09-04T23:31:14+05:30
```

That commit changed exactly six backend implementation/test files:

- `backend/app/api/ingestion.py`
- `backend/app/repositories/ingestion.py`
- `backend/app/schemas/ingestion.py`
- `backend/app/services/chunking.py` (added)
- `backend/tests/test_chunking.py` (added)
- `backend/tests/test_extraction.py`

It added or modified no SQL, migration, schema, or Supabase file. Its parent already contained the schema export and the database objects used by the new code. Therefore this commit cannot supply an original migration filename, timestamp, or migration contents.

## Schema export evidence is not a migration

The initial commit contains `schemaV2_export.sql`, later renamed without content changes to `docs/schema/schemaV2_export.sql`:

| Evidence | Value |
|---|---|
| First commit | `ee9ceee404452ccf4eb824a9594c5b2203290318` |
| First commit date | 2026-09-04T10:40:58+05:30 |
| Original path | `schemaV2_export.sql` |
| Current path | `docs/schema/schemaV2_export.sql` |
| Size | 1,178 lines |
| Git blob | `4682a29c02f0473d14462ff8102cd6700d66e1ec` |
| SHA-256 | `6BD4BD8A1E6B14524E0B0DA57539752C3E1E1808A860CF40FD253D99FE1203A7` |

The export contains `knowledge_chunks`, `document_processing_runs`, `document_versions`, `documents`, their keys and indexes, the wider application schema, and service-role grants. It is useful corroborating evidence of the pre-Phase-3.6 database shape.

It is not an authoritative Phase 3.5 migration: it predates the Phase 3.5 code commit, contains the entire then-current database rather than a phase-scoped change, has no migration filename or timestamp, and was never present under `supabase/migrations/`. Turning all or part of it into a newly named migration would require choosing contents and chronology that Git does not establish. The phase explicitly prohibits that reconstruction.

## Recovered migration

| Field | Result |
|---|---|
| Missing Phase 3.5 migration | Confirmed absent from all searched evidence |
| Recovered filename | **NOT FOUND** |
| Source Git commit | **NOT AVAILABLE** |
| Migration SHA-256 | **NOT AVAILABLE** |
| Working-tree migration change | None |

No file was added to `supabase/migrations/`, and no existing migration was edited or renamed.

## Phase 3.6 dependency analysis

`20250718000000_phase_3_6_embeddings.sql` creates the vector extension and `chunk_embeddings`, then extends `document_processing_runs`. Its pre-existing schema dependencies are:

| Phase 3.6 dependency | Required shape | Historical evidence | Verified as migration-provided |
|---|---|---|---|
| `extensions` schema | Target schema for `CREATE EXTENSION vector` and `extensions.vector(1536)` | Supabase platform baseline, referenced directly by Phase 3.6 | Platform-provided, not Phase 3.5 |
| `public.knowledge_chunks` | Existing table | Present in initial schema export | **NO** — no creating migration found |
| `public.knowledge_chunks.chunk_id` | UUID primary/unique key for embedding FK | UUID primary key in initial schema export | **NO** — no creating migration found |
| `public.document_processing_runs` | Existing table for two added columns | Present in initial schema export | **NO** — no creating migration found |
| Existing run `status` contract | Phase 3.6 explicitly preserves it | `queued`, `processing`, `ready`, `failed` check in export | **NO** — no creating migration found |
| `embedding_status` absent before Phase 3.6 | Added by Phase 3.6 | Absent from the initial export | Consistent with intended evolution |
| `embedding_error` absent before Phase 3.6 | Added by Phase 3.6 | Absent from the initial export | Consistent with intended evolution |

The export also shows the surrounding provenance chain expected by later retrieval code:

```text
knowledge_chunks.processing_run_id
  -> document_processing_runs.document_version_id
  -> document_versions.document_id
  -> documents.knowledge_source_id
  -> knowledge_sources
```

This validates what the missing base schema must have contained, but it does not establish an authoritative migration file or timestamp.

## Migration execution and database verification

No new local reset was run. Without an authoritative recovered migration, repeating the guarded reset would deterministically reproduce the Phase 7.9.5 failure, while applying the schema export or a selected subset would violate the no-reconstruction rule.

Consequently:

| Validation | Result |
|---|---|
| Phase 3.5 live schema verification | BLOCKED |
| Phase 3.6 execution | BLOCKED at known missing dependency |
| pgvector catalog/type/index verification | NOT RUN |
| Complete migration chain | NOT RUN |
| Migration ledger | NOT RUN |
| Phase 6.11 | NOT REACHED |
| Phase 7.2 | NOT REACHED |
| Phase 7.4 | NOT REACHED |
| Fresh reset #1 | NOT RUN |
| Fresh reset #2 | NOT RUN |

No migration ledger rows were inserted or repaired manually. No SQLite or mock substitute was used.

## Regression tests

Backend `pytest`, frontend `npm test`, TypeScript checking, and the frontend build were not run. The phase orders them after successful PostgreSQL migration validation, which cannot begin without the authoritative migration. `git diff --check` was run after creating this report.

## Remote database status

Remote production-like database modified: **NO**.

No remote schema query, dump, migration command, migration-history operation, backup, or data access was performed. The committed local schema export was inspected as repository evidence only; the remote database was not used to reconstruct SQL.

## Remaining blocker and next safe step

The missing artifact is not recoverable from the available repository evidence. A trusted external source must provide the original Phase 3.5 migration file together with its original filename/timestamp and provenance—for example, an earlier repository clone, archived patch, reviewed development artifact, or backup of the source tree.

Once that exact artifact is supplied, verify its hash and source, restore it unchanged, and use `scripts/validation/invoke_local_supabase.ps1 reset -ConfirmLocalReset` to test the entire chain twice. Do not derive a replacement from `schemaV2_export.sql` without a separately authorized migration-history reconstruction and review phase.

## Final report

```text
PHASE 7.9.6 STATUS: BLOCKED

Missing Phase 3.5 migration: CONFIRMED; no authoritative migration exists in searched repository evidence
Recovered filename: NOT FOUND
Source Git commit: NOT AVAILABLE (Phase 3.5 code commit 786b7b1 added no SQL)
SHA-256: NOT AVAILABLE FOR A MIGRATION

Migration dependency analysis: COMPLETE; required base objects exist only in a committed schema export, not migration history
Phase 3.5: BLOCKED — authoritative migration unavailable
Phase 3.6: BLOCKED — public.knowledge_chunks and public.document_processing_runs have no creating migration
pgvector: NOT RUN

Complete migration chain: NOT RUN
Migration ledger: NOT RUN

Phase 6.11: NOT REACHED
Phase 7.2: NOT REACHED
Phase 7.4: NOT REACHED

Fresh reset #1: NOT RUN
Fresh reset #2: NOT RUN

Backend tests: NOT RUN
Frontend tests: NOT RUN
TypeScript: NOT RUN
Build: NOT RUN
git diff --check: PASS (new report also passed an explicit trailing-whitespace check)

Remote production-like database modified: NO

Remaining blockers: The original Phase 3.5 migration filename, timestamp, and SQL are absent from all available repository and local Git evidence.
Next safe step: Obtain the exact original migration from a trusted archived source, verify its provenance/hash, then restore and validate it locally.
```
