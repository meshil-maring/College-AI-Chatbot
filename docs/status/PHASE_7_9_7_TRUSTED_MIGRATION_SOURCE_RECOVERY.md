# Phase 7.9.7 — Trusted Phase 3.5 Migration Source Recovery & Provenance Gate

**Status: BLOCKED.** No authoritative copy of the original Phase 3.5/base-schema migration was found. No migration was created, reconstructed, restored, or executed.

## Phase 7.9.6 starting point

Phase 7.9.6 established that the reachable repository, local refs, 106 unreachable commits, and 855 unreachable blobs do not contain an original Phase 3.5 migration. Commit `786b7b1abdc48cefe5415354cfe968e2e470e9eb`, titled `Phase 3.5 — Chunking implementation and tests`, changed only backend code and tests. Phase 3.6 remains the earliest repository migration and fails on a fresh database because `public.knowledge_chunks` does not exist.

This phase expanded that search to trusted sources outside the active repository. The linked remote Supabase database was not accessed.

## External sources searched

The following available local roots were searched read-only for project archives, alternate project trees, Git clones, migration-like SQL filenames, and SQL containing the two prerequisite table definitions:

- `F:\Git Project`
- `C:\Users\dsmes\Documents`
- `C:\Users\dsmes\Downloads`
- `C:\Users\dsmes\OneDrive`
- relevant project roots on `D:` and `E:`

The requested `F:\Backup`, `F:\Projects`, standalone Desktop, Google Drive, `G:`, and `H:` locations were not present. Broad dependency/cache results were excluded from candidate evaluation.

## Archived source trees

### `F:\Git Project\CollegeAIChatbot.zip`

| Property | Result |
|---|---|
| Size | 126,862,415 bytes |
| Created | 2026-09-19 16:37:27 local time |
| Modified | 2026-09-19 16:44:18 local time |
| SHA-256 | `993FE70573CA36483CAA2BE300C9E1340E1391B3C8ECBB037975C7EE58BC0785` |
| Working-tree migrations | 14 files, Phase 3.6 through Phase 6.13; no Phase 3.5 file |
| Full `.git` metadata | Present and independently inspected |

The archive's Git metadata contained 381 reachable commits, 80 unreachable commits, and 840 unreachable blobs. Every reachable and unreachable commit tree was searched for a Phase 3.5 SQL path; result: **zero candidates**.

Sixteen orphaned blobs matched a broad Phase 3.5/`knowledge_chunks` content test. Classification showed:

- five Phase 3.5 matches were source/service files, not SQL migrations;
- ten apparent `CREATE TABLE` matches were Phase 6.13 Python test files containing SQL text patterns; and
- one 39,526-byte blob was a 26-table pg_dump-style schema export beginning with `SET statement_timeout = 0;`, not a phase-scoped migration.

None had an original migration path, timestamp, or commit. The temporary archive extraction used for Git inspection was removed after the read-only analysis; the ZIP was not modified.

## Other source trees and Git clones

`C:\Users\dsmes\Downloads\CollegeAIChatbot` is a source-tree snapshot created on 2026-09-19. It contains `backend`, `frontend`, and `supabase`, but no `.git` directory. Its migration inventory starts at `20250718000000_phase_3_6_embeddings.sql` and contains no Phase 3.5 migration.

No additional clone with the official remote or a matching `backend`/`frontend`/`supabase` Git structure was found in the searched roots. The active repository is the only matching Git clone.

## Official remote repository

The configured official remote is:

```text
https://github.com/meshil-maring/College-AI-Chatbot.git
```

`git ls-remote --heads --tags` returned one published ref:

```text
afdd94131fb8b29a9e8b879ef2ed12d3f92a6d6d refs/heads/main
```

There are no published tags or other branch refs. That main commit is already present locally, and its complete available migration history was searched in Phase 7.9.6. A search of the official GitHub repository for `phase_3_5`, `Phase 3.5`, and `knowledge_chunks` yielded no additional indexed source. Deleted remote branches are not exposed by Git's advertised refs and no separate remote artifact was available.

No fetch, push, branch modification, release modification, or remote Supabase operation was performed.

## Development artifacts

### Standalone SQL exports

| Artifact | Modified | SHA-256 | Phase 3.5 objects | Migration metadata | Result |
|---|---:|---|---|---|---|
| `Downloads\schema.sql` | 2026-08-31 11:26:47 | `0E9721D9A663041032B61AA66F5D2C2326D8C8A482C5F957998AE18000A1A9E0` | No | No | Rejected |
| `Downloads\schemaV2.sql` | 2026-08-31 22:19:07 | `3D0D4B59826832327F018212B184FD64C9129A9F19CE3715EE463B70A7F3DE72` | No | No | Rejected |
| Downloads project `docs\schema\schemaV2_export.sql` | 2026-09-19 snapshot | `6BD4BD8A1E6B14524E0B0DA57539752C3E1E1808A860CF40FD253D99FE1203A7` | Yes | No | Same committed export; rejected as original migration |

The two August SQL files contain academic/admin tables but do not contain `knowledge_chunks`, `document_processing_runs`, a Phase 3.5 marker, or a migration filename/timestamp.

### Editor and shell history

VS Code History, VS Code Backups, `.vscode`, `.cline` session artifacts, PowerShell PSReadLine history, and OneDrive were searched for Phase 3.5 migration names and the relevant table DDL.

VS Code History contained `JWMT.sql`, but its `entries.json` maps it directly to:

```text
F:\Git Project\CollegeAIChatbot\docs\schema\schemaV2_export.sql
```

It is an older editor snapshot of the known schema export, not a migration. No Cline session contained a filename matching a Phase 3.5 migration. Cline SQL-like matches were either schema export text or later test/migration discussion.

PowerShell history contains repeated commands of the form:

```text
supabase db dump --schema public --file schemaV2_export.sql
```

This establishes that `schemaV2_export.sql` was generated as a schema dump. It does not establish an original Phase 3.5 migration filename, timestamp, or content.

## Documentation searched

Repository phase reports, status documents, locks, architecture/schema documentation, backend services/repositories/tests, all current migrations, and historical project files were searched for `PHASE_3_5`, `Phase 3.5`, `knowledge_chunks`, `document_processing_runs`, `migration`, and `schema`.

Documentation confirms the object relationships and that Phase 3.6 treats Phase 3.5 as locked, but it identifies no original migration filename, timestamp, or source commit. Documentation was not treated as proof of original SQL.

## Existing schema export provenance and inventory

| Property | Value |
|---|---|
| Current file | `docs/schema/schemaV2_export.sql` |
| Original repository path | `schemaV2_export.sql` |
| First Git commit | `ee9ceee404452ccf4eb824a9594c5b2203290318` |
| First commit date | 2026-09-04T10:40:58+05:30 |
| Rename commit | `751940f8a0cef043e0107e96690383d7f683caa6` |
| Git blob | `4682a29c02f0473d14462ff8102cd6700d66e1ec` |
| File SHA-256 | `6BD4BD8A1E6B14524E0B0DA57539752C3E1E1808A860CF40FD253D99FE1203A7` |
| Embedded export date | Not present |
| Generation evidence | PowerShell history records `supabase db dump --schema public` |

The export contains 26 tables, 17 indexes, and 30 grants. It contains no exported function, trigger, policy, RLS-enable statement, or extension creation statement.

The 26 tables are:

```text
academic_years, ai_responses, campuses, conversations, course_offerings,
courses, departments, document_processing_runs, document_versions, documents,
institutions, knowledge_chunks, knowledge_sources, message_citations, messages,
permissions, program_courses, programs, retrieval_operations, retrieved_chunks,
role_permissions, roles, sections, semesters, user_roles, users
```

Relevant Phase 3.5 evidence includes:

- `document_processing_runs` with UUID primary key; FK to `document_versions`; status, failure/error, and time checks; document-version index; PostgreSQL ownership; and service-role grant;
- `knowledge_chunks` with UUID primary key; FK to `document_processing_runs`; unique `(processing_run_id, chunk_sequence)`; content, page, sequence, and token-count checks; processing-run index; PostgreSQL ownership; and service-role grant; and
- the broader provenance chain through `document_versions`, `documents`, and `knowledge_sources` required by later retrieval migrations.

The export proves a schema state existed and is compatible evidence for Phase 3.6 dependencies. It is not an original migration because it is a whole-schema dump, carries no migration metadata, and was never located under `supabase/migrations/` in any trusted source.

## Provenance matrix

| Candidate source | Contains Phase 3.5 objects | Original migration metadata | Trusted provenance | Acceptable as original migration |
|---|---:|---:|---:|---:|
| Active official clone/history | Schema export only | No | Yes | No |
| Official GitHub published refs | No migration found | No | Yes | No |
| `CollegeAIChatbot.zip` working tree | Schema export only | No | Yes | No |
| `CollegeAIChatbot.zip` archived Git objects | Orphan schema dump only | No | Yes | No |
| Downloads project snapshot | Schema export only | No | Reasonably trusted local snapshot | No |
| Other Git clone | None found | No | N/A | No |
| Standalone Downloads SQL exports | No | No | Local artifacts | No |
| VS Code local history | Schema export snapshot | No | Local editor provenance | No |
| Cline/session history | References/tests only | No | Local development provenance | No |
| PowerShell history | Records schema dump generation | No | Local command provenance | No |
| Committed schema export | Yes | No | Yes as schema-state evidence | No as original migration |
| Reconstructed SQL | Not created | No | No | No |

## Recovery and restoration result

```text
Candidate Phase 3.5 migration: NOT FOUND
Authoritative source: NOT AVAILABLE
Original filename: NOT AVAILABLE
Original timestamp: NOT AVAILABLE
Source commit: NOT AVAILABLE
SHA-256: NOT AVAILABLE FOR A MIGRATION
Migration restored: NO
```

No file in `supabase/migrations/` was created, edited, renamed, or restored. Because provenance failed, no local Supabase reset or migration execution was attempted in this phase.

## Remote database status

Remote production-like database modified: **NO**.

The linked Supabase project was not queried, dumped, migrated, reset, backed up, or otherwise used. The GitHub repository was inspected read-only and is distinct from the off-limits Supabase database.

## Remaining blocker and next safe step

Only schema snapshots are available; none carries the historical identity required to be accepted as the original Phase 3.5 migration. Historical recovery is therefore exhausted for the trusted sources available on this machine and the currently advertised official remote refs.

The next safe step is a separately authorized baseline-reconstruction decision. That phase must explicitly define a new authoritative baseline derived from verified schema evidence, give it new provenance rather than claiming it is historical, reconcile its ordering with Phase 3.6 and later migrations, and keep production reconciliation behind a separate explicit gate.

## Final report

```text
PHASE 7.9.7 STATUS: BLOCKED

External sources searched: Local project/backup roots, archives, editor history, shell history, and development artifacts
Other Git clones: None found; Downloads source tree has no .git and no Phase 3.5 migration
Remote repository: Official GitHub exposes main only; no tags/other branches or Phase 3.5 migration found
Archived source trees: CollegeAIChatbot.zip fully inspected, including archived Git objects; no migration found
Development artifacts: Two standalone SQL exports lack Phase 3.5 objects; editor/session artifacts contain only schema snapshots/references
Documentation: Confirms dependencies but provides no original migration metadata

Schema export: docs/schema/schemaV2_export.sql, SHA-256 6BD4BD8A1E6B14524E0B0DA57539752C3E1E1808A860CF40FD253D99FE1203A7
Schema export provenance: Initial commit ee9ceee; generated via supabase db dump; authoritative only as schema-state evidence

Candidate Phase 3.5 migration: NOT RECOVERED
Authoritative source: NOT FOUND
Original filename: NOT AVAILABLE
Original timestamp: NOT AVAILABLE
Source commit: NOT AVAILABLE
SHA-256: NOT AVAILABLE

Provenance: No candidate satisfies original-migration metadata and trusted-history requirements
Migration restored: NO

Remote production-like database modified: NO

Remaining blockers: Only whole-schema exports/snapshots exist; no original migration identity or contents can be established.
Next safe step: Begin a separately authorized new-baseline reconstruction phase; do not label the result as the historical Phase 3.5 migration.
```
