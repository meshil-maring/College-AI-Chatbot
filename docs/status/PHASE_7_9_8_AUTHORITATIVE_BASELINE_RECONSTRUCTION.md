# Phase 7.9.8 — Authoritative Baseline Migration Reconstruction & Local Validation

## Status

**PHASE 7.9.8 STATUS: INCOMPLETE**

> The historical Phase 3.5 migration was not recovered. This migration is a newly reconstructed authoritative baseline derived from the trusted `schemaV2_export.sql` artifact. It must not be represented as the original Phase 3.5 migration.

- Historical Phase 3.5: **UNRECOVERED / UNRECOVERABLE**
- Reconstructed baseline: **NEW AUTHORITATIVE BASELINE**
- Remote production-like database modified: **NO**
- Validation boundary: disposable local Supabase only (`127.0.0.1:54322`, Docker context `desktop-linux`)

The baseline and the Phase 3.6 through Phase 3.8 migrations executed locally. The run then stopped at the first later-migration failure, in `20260909000000_phase_admin_1_admin_student_schema.sql`, as required by the stop-on-failure rule.

## Authorization and source provenance

Phase 7.9.6 and Phase 7.9.7 established that the historical Phase 3.5 SQL migration could not be recovered from reachable or unreachable Git history, trusted backups, another clone, or trusted development artifacts. Phase 7.9.8 explicitly authorized creation of a new baseline without rewriting that historical result.

| Property | Value |
| --- | --- |
| Source artifact | `docs/schema/schemaV2_export.sql` |
| Initial commit | `ee9ceee404452ccf4eb824a9594c5b2203290318` |
| Git blob | `4682a29c02f0473d14462ff8102cd6700d66e1ec` |
| Expected SHA-256 | `6BD4BD8A1E6B14524E0B0DA57539752C3E1E1808A860CF40FD253D99FE1203A7` |
| Observed SHA-256 | `6BD4BD8A1E6B14524E0B0DA57539752C3E1E1808A860CF40FD253D99FE1203A7` |
| Integrity result | **PASS** |
| Export character | structural schema; no `INSERT` or `COPY` data statements |

Reconstruction did not begin until the observed hash exactly matched the trusted value.

## Schema export inventory

The 1,178-line export was inventoried before reconstruction.

### Extensions and types

- Explicit `CREATE EXTENSION`: none.
- Explicit `CREATE TYPE`: none.
- The export relies on Supabase/PostgreSQL-provided `gen_random_uuid()` and `now()`.
- Vector/pgvector objects are intentionally left to the surviving Phase 3.6 and Phase 3.7 migrations.

### Tables

The export defines these 26 tables:

`academic_years`, `ai_responses`, `campuses`, `conversations`, `course_offerings`, `courses`, `departments`, `document_processing_runs`, `document_versions`, `documents`, `institutions`, `knowledge_chunks`, `knowledge_sources`, `message_citations`, `messages`, `permissions`, `program_courses`, `programs`, `retrieval_operations`, `retrieved_chunks`, `role_permissions`, `roles`, `sections`, `semesters`, `user_roles`, and `users`.

All exported column definitions, PostgreSQL types, nullability, defaults, identity behavior, and owner declarations were retained. The export contains no sequences or identity columns; UUID primary keys use `gen_random_uuid()` defaults where defined.

### Constraints and indexes

| Object class | Count |
| --- | ---: |
| Primary-key constraints | 26 |
| Foreign-key constraints | 43 |
| Unique constraints | 24 |
| Check constraints | 58 |
| Regular/unique indexes | 17 |

There are no vector indexes in the export. They remain owned by later migrations.

### Functions, triggers, RLS, policies, and grants

- Functions: none.
- Triggers: none.
- Explicit RLS enablement: none.
- Policies: none.
- Grants: 30 explicit grants plus 8 default-privilege statements.

All structural objects present in the trusted export were retained; no production, student, user, document, embedding, or secret data was copied into the baseline.

## Baseline ownership analysis

Every later migration was cross-referenced against the export before selecting baseline contents.

- Later migrations create 13 distinct tables: `admin_audit_log`, `chunk_embeddings`, `faqs`, `institution_join_requests`, `institution_membership_requests`, `notices`, `organizations`, `student_attendance`, `student_notifications`, `student_result_items`, `student_results`, `students`, and `test_results`.
- Intersection between those later-created tables and the 26 exported tables: **zero**.
- Fifteen exported tables are explicitly consumed or altered by later migrations: `academic_years`, `course_offerings`, `courses`, `departments`, `document_processing_runs`, `document_versions`, `documents`, `institutions`, `knowledge_chunks`, `knowledge_sources`, `programs`, `sections`, `semesters`, `user_roles`, and `users`.
- Later ALTER targets already present in the export are `document_processing_runs`, `document_versions`, `institutions`, `knowledge_sources`, and `user_roles`.

| Object | In export | Required before Phase 3.6/later chain | Created later | Baseline-owned |
| --- | --- | --- | --- | --- |
| `knowledge_chunks` | YES | YES | NO | YES |
| `document_processing_runs` | YES | YES | NO | YES |
| Other 24 exported tables | YES | YES, directly or transitively | NO | YES |
| `chunk_embeddings` | NO | NO (created by Phase 3.6) | YES | NO |
| Admin/student tables | NO | NO (created by Admin-1/later) | YES | NO |
| Organization/membership tables | NO | NO (created by Phase 6.13) | YES | NO |

**Baseline ownership analysis: PASS.** The full export was selected only after this object-level classification showed that it is a pre-later-migration structural state. This is not a blind conversion of a current multi-phase schema.

## Reconstructed baseline identity

| Property | Value |
| --- | --- |
| Filename | `20250717000000_reconstructed_pre_phase_3_6_baseline.sql` |
| Timestamp | `20250717000000` |
| SHA-256 | `7FD1EA5C096EB47667A2BA55CC1BF4A872C959E12300C2110A69A698CA6E6429` |
| Tables | 26 |
| Data statements | 0 |

The timestamp is a new identity placed immediately before the repository's first surviving migration, `20250718000000_phase_3_6_embeddings.sql`. It does not reuse or imply knowledge of the unavailable historical Phase 3.5 timestamp. The filename and SQL header explicitly label the artifact as reconstructed.

## Migration inventory

| Migration | Principal responsibility | Baseline dependency |
| --- | --- | --- |
| `20250717000000_reconstructed_pre_phase_3_6_baseline.sql` | Trusted exported pre-Phase-3.6 structure | Source |
| `20250718000000_phase_3_6_embeddings.sql` | Embedding/vector foundation on `knowledge_chunks` | `knowledge_chunks` and related Phase 3 schema |
| `20260905000000_phase_3_7_1_vector_search_index.sql` | Vector search index | Phase 3.6 vector objects |
| `20260905000001_phase_3_7_2_vector_similarity_search.sql` | Vector similarity search | Phase 3.6/3.7.1 |
| `20260905000002_phase_3_8_metadata_access_filtering.sql` | Metadata/access filtering | Knowledge/document tables |
| `20260909000000_phase_admin_1_admin_student_schema.sql` | Admin/student tables and deterministic demo data | Core users, roles, academic structure |
| `20260909000001_phase_admin_2_extracted_text_column.sql` | Extracted-text schema addition | Document-processing schema |
| `20260909000002_phase_admin_2_faq_published_column.sql` | FAQ publication state | Admin-1 `faqs` |
| `20260909000003_phase_admin_2_notice_published_column.sql` | Notice publication state | Admin-1 `notices` |
| `20260912000000_phase_6_2_student_identity_model.sql` | Student identity evolution | Users, roles, students |
| `20260913000000_phase_6_7_attendance.sql` | Attendance evolution | Student/academic tables |
| `20260913010000_phase_6_8_results.sql` | Results evolution | Student/academic tables |
| `20260914000000_phase_6_11_student_notifications.sql` | Student notifications | Student identity model |
| `20260915000000_phase_6_13_organization_institution_tenancy.sql` | Organization/institution tenancy | Institutions and user roles |
| `20260928000000_phase_7_2_public_knowledge_policy.sql` | Public visibility, RLS, and search RPC | Knowledge/document lifecycle schema |
| `20260928010000_phase_7_4_public_rag_hardening.sql` | Public RAG hardening and retrieval constraints | Phase 7.2 and vector schema |

## Local validation run

The guarded wrapper reported:

```text
TARGET=LOCAL
DOCKER_CONTEXT=desktop-linux
DATABASE_ENDPOINT=127.0.0.1:54322
LINK_METADATA_PRESENT=YES (ignored; this wrapper only invokes local commands)
```

The first wrapper call exposed a local argument-splatting defect before Supabase was invoked: a single `start` value was passed as characters. `scripts/validation/invoke_local_supabase.ps1` was corrected to retain the switch result as an argument array. This event did not reach a database.

The corrected local run then reported successful application of:

1. `20250717000000_reconstructed_pre_phase_3_6_baseline.sql`
2. `20250718000000_phase_3_6_embeddings.sql`
3. `20260905000000_phase_3_7_1_vector_search_index.sql`
4. `20260905000001_phase_3_7_2_vector_similarity_search.sql`
5. `20260905000002_phase_3_8_metadata_access_filtering.sql`

This demonstrates that the original Phase 3.6 missing-relation failure for `public.knowledge_chunks` is resolved by the reconstructed baseline without modifying Phase 3.6.

### Stop-on-failure record

```text
migration: 20260909000000_phase_admin_1_admin_student_schema.sql
statement: 8 (students_user_id_fkey)
error: column "user_id" referenced in foreign key constraint does not exist
SQLSTATE: 42703
dependency: public.users.user_id
```

The trusted export defines `public.users.id`; the failing later migration references `public.users.user_id` and even notes that it intentionally targets a remote schema rather than the exported `id` name. The later migration's `public.students.user_id` column is present, so the unresolved side of this foreign key is `public.users.user_id`.

This mismatch is not evidence that `users.user_id` belongs in the reconstructed baseline: that definition is absent from the trusted source artifact, and inventing or renaming it would violate the no-fabrication/source-of-truth boundary. The failure is therefore recorded without changing the baseline or the failing later migration.

The CLI stopped the local containers after the failure. No migration ledger was edited and no migration was skipped or marked applied.

## Validation results

| Validation | Result | Evidence / reason |
| --- | --- | --- |
| Export SHA-256 | PASS | Exact trusted hash match |
| Baseline ownership | PASS | 26-table export/later-migration classification completed |
| Phase 3.6 dependency validation | PASS | Baseline and Phase 3.6 applied successfully |
| pgvector metadata and dimensions | NOT COMPLETED | Stop-on-failure prevented post-run inspection |
| Complete migration chain | FAIL | Admin-1 SQLSTATE `42703` |
| Migration ledger | NOT COMPLETED | Failed stack was stopped; no manual ledger work performed |
| Schema equivalence | NOT COMPLETED | Full resulting schema was not produced |
| Fresh reset #1 | FAIL | Chain stopped at Admin-1 |
| Fresh reset #2 | NOT RUN | Prohibited after first migration failure |
| Phase 6.11 | NOT RUN | Earlier migration failure |
| Phase 7.2 | NOT RUN | Earlier migration failure |
| Phase 7.4 | NOT RUN | Earlier migration failure |
| Synthetic tenant validation | NOT RUN | Requires successful chain |
| Public RAG validation | NOT RUN | Requires successful chain |
| Backend tests | NOT RUN | Stop-on-failure boundary |
| Frontend tests | NOT RUN | Stop-on-failure boundary |
| TypeScript | NOT RUN | Stop-on-failure boundary |
| Frontend build | NOT RUN | Stop-on-failure boundary |
| `git diff --check` | NOT COMPLETED | Final chain did not reach regression stage |

## Remaining blocker and next safe step

The complete migration chain cannot be derived from the trusted export alone because a later migration expects the unexported `public.users.user_id` shape. This is an existing later-migration/schema-lineage conflict, not the original Phase 3.6 prerequisite failure.

The next safe step is a separately scoped review of `20260909000000_phase_admin_1_admin_student_schema.sql` and the `public.users` key-name evolution. That review must determine, from authoritative evidence, whether the later migration should reference `users.id` or whether a documented intervening migration that changes `id` to `user_id` is itself missing. Do not alter the reconstructed baseline, bypass the migration, or touch the remote ledger to conceal the mismatch.
