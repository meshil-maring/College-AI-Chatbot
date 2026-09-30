# Phase 7.9.11 — Admin Seed/Auth Provisioning Contract and Local Migration Validation

## Status

**PHASE 7.9.11 STATUS: COMPLETE**

The Admin-1 migration is classified as **MIXED**: it contained valid structural DDL followed by a connected development/demo data snapshot. The structural DDL remains in migration history. The demo snapshot has been removed from the migration and replaced by an explicit post-migration provisioning boundary.

The linked production-like Supabase project was not inspected, modified, reset, pushed, or used for validation. All database and Auth operations in this phase targeted the disposable local Supabase stack at `127.0.0.1`.

## Failure and root cause

After the reconstructed baseline and `public.users.id` contract repair, the Admin-1 migration reached its seed section and attempted to insert three `public.users` rows whose `auth_user_id` values were fixed placeholder UUIDs. The enforced `users_auth_user_id_fkey` correctly rejected those rows because no corresponding identities existed in `auth.users`.

The failure was not evidence that the FK should be weakened. It exposed an invalid lifecycle assumption: a structural SQL migration cannot invent supported GoTrue identities by assigning placeholder UUIDs to an Auth foreign key.

## Seed classification and dependency analysis

The removed block was one connected demo snapshot, not required reference data. It contained:

- three demo `public.users` profiles with placeholder Auth identifiers;
- role assignments;
- student profiles;
- results and result items;
- test results and attendance;
- FAQs and notices;
- audit-log entries.

The downstream rows depended on deployment-specific institution, role, program, academic-year, course, section, and user identifiers that the fresh migration chain did not establish as structural prerequisites. Retaining a subset would therefore preserve hidden environment dependencies and create a misleading partially provisioned dataset. No production records, secrets, private documents, or real identities were copied into the migration.

| Seed component | Classification | Resolution |
| --- | --- | --- |
| Admin/student demo identities | Development provisioning | Create through local GoTrue Admin API after migrations |
| `public.users` demo profiles | Development provisioning | Upsert only after the corresponding Auth identity exists |
| Demo roles/student/academic rows | Connected demo snapshot | Removed from structural migration; not silently recreated |
| Admin-1 tables, constraints, indexes, comments | Structural schema | Preserved in the migration |

Placeholder Auth identities found: **3**. They were deterministic placeholders only; none was accepted as an authoritative Auth identity.

## Supported local provisioning contract

The local-only provisioner is `scripts/validation/provision_local_demo_users.ps1`.

It:

1. requires an ephemeral password through `COLLEGEAI_LOCAL_DEMO_PASSWORD` and never prints it;
2. fails closed if `DOCKER_HOST` is set, Docker Desktop Linux is not the active engine, or the Supabase API is not exactly `http://127.0.0.1:54321`;
3. obtains the transient local service-role credential from `supabase status` without persisting or printing it;
4. creates missing identities using the supported local GoTrue Admin API;
5. reuses an existing identity by email on repeat execution;
6. upserts `public.users` using the actual GoTrue-generated `auth.users.id` value;
7. verifies every public/Auth mapping and performs a password login for every provisioned account.

The provisioner intentionally does not reproduce the old roles/student/academic demo snapshot. Those records require a separately specified, deterministic development-fixture contract.

## Migration changes

`20260909000000_phase_admin_1_admin_student_schema.sql` now:

- preserves all Admin-1 structural DDL;
- keeps `students.user_id`, `notices.created_by`, and `admin_audit_log.actor_user_id` referencing the authoritative `public.users(id)` key;
- removes the connected demo seed block;
- documents that local demo identities must be provisioned after migrations through the supported GoTrue Admin API;
- keeps `users_auth_user_id_fkey` enforced.

No migration ledger record was inserted, changed, or skipped manually.

## Fresh local validation

### Reset and provisioning run 1

- Fresh local reset: **PASS**
- Complete 16-migration chain: **PASS**
- First provision: 3 Auth identities created, 3 public mappings verified
- Immediate repeat: 0 created, 3 reused, 3 public mappings verified
- Password authentication: **PASS** for all three identities
- Secret/password logging: **NO**

### Reset and provisioning run 2

- Fresh local reset: **PASS**
- Complete 16-migration chain: **PASS**
- First provision after reset: 3 Auth identities created, 3 public mappings verified
- Immediate repeat: 0 created, 3 reused, 3 public mappings verified
- Password authentication: **PASS** for all three identities
- Secret/password logging: **NO**

## Database evidence

| Check | Result |
| --- | --- |
| Local migration ledger count and ordering | PASS — 16 ordinary migration records, no duplicates or skips |
| `public.users.id` primary key | PASS |
| Stale `public.users.user_id` column absent | PASS |
| `users_auth_user_id_fkey` present | PASS |
| Provisioned public/Auth mappings | PASS — 3/3 |
| Orphaned provisioned public users | PASS — 0 |
| All user-child FKs target `public.users(id)` | PASS — 16 constraints |
| Admin-1 structural objects | PASS |
| Phase 6.11 objects | PASS |
| Phase 7.2 visibility constraint and public RPC | PASS |
| Phase 7.4 hardening migration | PASS |
| `vector` extension | PASS |
| vector column and HNSW index | PASS |

The exact migration ledger was checked after execution and contained all 16 repository migrations in filename/timestamp order, including the reconstructed pre-Phase-3.6 baseline and all migrations through Phase 7.4.

## Relationship validation

Inside a rollback-only local transaction, the validation created synthetic organization/institution/role prerequisites, then joined one provisioned identity through `public.users` to `user_roles` and `students`.

- Auth-to-public user mapping: **PASS**
- RBAC relationship join: **PASS** (`1` matching row)
- Student identity relationship join: **PASS** (`1` matching row)
- Transaction rollback: **PASS**; no synthetic relationship data was retained

## Regression validation

| Validation | Result |
| --- | --- |
| Backend established suite (`DEBUG=false`) | PASS — 2,126 passed, 15 skipped |
| Debug-only diagnostics (`DEBUG=true`) | PASS — 2 passed |
| Frontend tests | PASS — 50 files, 431 tests |
| TypeScript (`npx tsc --noEmit -p tsconfig.json`) | PASS |
| Frontend build | PASS — 97 modules built |
| `git diff --check` | PASS |

The backend suite is intentionally split by runtime mode: the two development-diagnostics cases require `DEBUG=true`; all normal tests ran with `DEBUG=false`. A repository-root pytest invocation is not the established unit boundary because it also collects live/manual validation scripts; the maintained `backend/tests` suite is the recorded regression result.

## Safety and conclusion

- Remote production-like database modified: **NO**
- Remote migration history modified: **NO**
- Auth FK weakened or removed: **NO**
- Raw SQL inserted into `auth.users`: **NO**
- Placeholder identities retained: **NO**
- Password or service-role secret logged: **NO**

Admin-1 now has a valid boundary: migrations create structural schema, while local development identities are created by GoTrue and mapped into the application schema afterward. Both fresh-reset runs, repeat provisioning, authentication, FK enforcement, migration-ledger checks, phase-object checks, and applicable regression suites passed.

Remaining blockers: **None for Phase 7.9.11.**

Next safe step: review and commit the local migration, provisioner, application contract repairs, tests, and phase reports as one coherent recovery series. Any remote reconciliation or deployment requires a separate explicitly authorized phase.
