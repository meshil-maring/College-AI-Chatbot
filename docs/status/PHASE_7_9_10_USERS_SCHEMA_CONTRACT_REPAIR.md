# Phase 7.9.10 — Authoritative `users.id` Schema-Contract Repair & Migration Revalidation

## Status

**PHASE 7.9.10 STATUS: INCOMPLETE**

The authoritative contract is preserved:

```text
auth.users.id
    ↓ public.users.auth_user_id
public.users.id
    ↓ child user_id foreign keys
students.user_id / user_roles.user_id / other child identifiers
```

The `users.id` repair was completed statically across Admin-1, Phase 6.13, application queries, validation scripts, tests, and current architecture documentation. Fresh local migration run #1 progressed beyond the previously failing `students_user_id_fkey`, then stopped at the next failure inside Admin-1 seed data, as required.

No remote project was inspected or modified. No migration ledger was manually changed.

## Phase 7.9.9 conclusion

Phase 7.9.9 established with authoritative repository evidence that:

- `public.users.id UUID DEFAULT gen_random_uuid() PRIMARY KEY` is authoritative;
- no authoritative migration introduces `public.users.user_id`;
- no authoritative migration renames `users.id`;
- Admin-1 incorrectly assumed an undocumented remote `users.user_id` schema.

This phase does not add `users.user_id` to the reconstructed baseline and does not rename `users.id`.

## Occurrence inventory and repairs

Twenty executable invalid assumptions were identified and repaired before local execution:

| Category | Count | Repair |
| --- | ---: | --- |
| SQL foreign-key parent references | 7 | Point child columns to `public.users(id)` |
| Admin-1 user-seed clauses | 2 | Seed column and conflict target changed from `user_id` to `id` |
| Runtime application operations | 6 | Query `id`, alias to application-facing `user_id` where needed, read inserted `id`, delete by `id` |
| Local diagnostic/physical-validation scripts | 4 | Insert/select/delete `public.users.id` |
| Unit-test query expectation | 1 | Expect explicit `user_id:id` PostgREST alias |

Descriptive occurrences in application comments, tests, locks, and current Phase 6 reports were separately classified and corrected. Valid child columns named `user_id` were preserved.

The historical Phase 7.9.8 and Phase 7.9.9 reports retain their evidence about the former inconsistency and were intentionally not rewritten.

## Admin-1 repair

### Foreign keys

| Child table | Child column | Constraint | Former parent | Correct parent |
| --- | --- | --- | --- | --- |
| `students` | `user_id` | `students_user_id_fkey` | `public.users(user_id)` | `public.users(id)` |
| `notices` | `created_by` | `notices_created_by_fkey` | `public.users(user_id)` | `public.users(id)` |
| `admin_audit_log` | `actor_user_id` | `admin_audit_log_actor_user_id_fkey` | `public.users(user_id)` | `public.users(id)` |

All three child-column names remain unchanged.

### Deterministic user seed

Admin-1 has child seed rows that depend on fixed application-user UUIDs. The existing deterministic UUID strategy was therefore retained, but the parent insert now supplies `public.users.id` and uses `ON CONFLICT (id)`. No new identifiers were fabricated.

Static result: **PASS**. Runtime Admin-1 result: **FAIL**, due to the separate auth foreign-key failure documented below.

## Phase 6.13 downstream repair

Four later foreign keys were repaired:

| Child table | Child column | Constraint | Correct parent |
| --- | --- | --- | --- |
| `institution_join_requests` | `requested_by_user_id` | `institution_join_requests_requested_by_fkey` | `public.users(id)` |
| `institution_join_requests` | `decided_by_user_id` | `institution_join_requests_decided_by_fkey` | `public.users(id)` |
| `institution_membership_requests` | `user_id` | `institution_membership_requests_user_id_fkey` | `public.users(id)` |
| `institution_membership_requests` | `decided_by_user_id` | `institution_membership_requests_decided_by_fkey` | `public.users(id)` |

Valid comparisons between child identifiers, such as `user_roles.user_id = students.user_id`, were preserved. Phase 6.13 was not reached during local execution because Admin-1 failed first.

## Application contract

The external application/session contract continues to expose a field called `user_id`; that value now comes explicitly from `public.users.id`.

- Auth lookup uses PostgREST projection `user_id:id` while filtering by `auth_user_id`.
- Sign-in context uses `user_id:id`.
- Tenancy and duplicate-email lookups use `user_id:id`.
- Public-user creation reads the inserted row’s `id` and returns it as the application variable `user_id`.
- Compensation deletes a public user by `id`.
- Child writes continue to populate `students.user_id`, `user_roles.user_id`, membership request identifiers, and audit identifiers.

### Authentication identity mapping

```text
Supabase JWT sub
    = auth.users.id
    = public.users.auth_user_id (unique FK)

public.users.id
    = application user_id
    = parent key for child user_id columns
```

`auth_user_id` and `public.users.id` remain separate concepts and are never assumed equal.

### RBAC mapping

```text
public.users.id
    ↓ user_roles.user_id
user_roles.role_id
    ↓ roles.role_id
```

The trusted export already defines `user_roles.user_id UUID` with a foreign key to `public.users(id)`. Role resolution still receives the application-facing `user_id` alias whose value is the parent `id`.

### Student identity mapping

```text
public.users.id
    ↓ students.user_id
students.student_id
    ↓ academic child tables
```

Registration, authentication context, tenant resolution, approval, `/auth/me`, and student services continue to pass the same UUID under the application-facing name `user_id`; database queries no longer request a nonexistent parent column.

## Test and script changes

- Updated the auth repository unit-test query expectation to `user_id:id`.
- Updated local physical Phase 4.2 and Phase 4.3 scripts to select and read `public.users.id`.
- Updated `check_auth_users.py` to insert and delete the public row by `id`.
- Updated code/test documentation describing authentication, RBAC, and student identity.

Regression suites were not run because the migration chain did not complete.

## Fresh local migration run #1

The guarded wrapper established the local-only boundary:

```text
TARGET=LOCAL
DOCKER_CONTEXT=desktop-linux
DATABASE_ENDPOINT=127.0.0.1:54322
LINK_METADATA_PRESENT=YES (ignored; this wrapper only invokes local commands)
```

Successfully applied before the failure:

1. `20250717000000_reconstructed_pre_phase_3_6_baseline.sql`
2. `20250718000000_phase_3_6_embeddings.sql`
3. `20260905000000_phase_3_7_1_vector_search_index.sql`
4. `20260905000001_phase_3_7_2_vector_similarity_search.sql`
5. `20260905000002_phase_3_8_metadata_access_filtering.sql`

Admin-1 progressed beyond the repaired statement 8 foreign key and reached its user seed.

### Stop-on-next-failure record

```text
Migration: 20260909000000_phase_admin_1_admin_student_schema.sql
Statement: 94, public.users deterministic seed insert
SQLSTATE: 23503
Error: insert or update on table "users" violates foreign key constraint
       "users_auth_user_id_fkey"
Referenced object: auth.users.id
Expected object: auth.users rows for placeholder UUIDs
Likely dependency: Admin-1 seeds public.users.auth_user_id values
                   40000000-0000-0000-0000-000000000001 through ...0003,
                   but does not create corresponding auth.users rows
```

The Admin-1 comments explicitly call these `auth_user_id` values placeholders to be replaced by GoTrue Admin API provisioning. PostgreSQL nevertheless enforces the trusted baseline foreign key during migration, so placeholder values cannot be inserted into `public.users` unless corresponding auth principals exist.

### Failure classification

This is an **unrelated Admin-1 seed/auth dependency defect**, not:

- another `users.user_id` assumption;
- a reconstructed-baseline ownership error; or
- evidence that `public.users.id` is incorrect.

Per the Phase 7.9.10 stop rule, this new defect was recorded without immediately changing the seed, disabling the foreign key, inserting raw auth records, skipping Admin-1, or modifying any ledger.

The CLI stopped the local containers after the failure.

## Verification status

| Check | Result | Notes |
| --- | --- | --- |
| Invalid `users.user_id` executable references | PASS | Zero remain after classified repair |
| Admin-1 foreign-key source repair | PASS | Three repaired to `users(id)` |
| Admin-1 execution | FAIL | SQLSTATE `23503` at seed statement 94 |
| User seed key-column repair | PASS | Uses deterministic `id`; auth dependency remains |
| Phase 6 downstream source repair | PASS | Four Phase 6.13 FKs repaired |
| Application `users.id` source contract | PASS | Explicit aliases preserve API contract |
| Authentication mapping | PASS (static) | Runtime DB verification blocked by migration failure |
| RBAC mapping | PASS (static) | Runtime synthetic validation not reached |
| Student identity mapping | PASS (static) | Runtime synthetic validation not reached |
| Full migration chain | FAIL | Stopped in Admin-1 |
| Migration ledger | NOT VERIFIED | No manual entries or repairs |
| PostgreSQL users metadata | NOT VERIFIED | Stack stopped on migration failure |
| PostgreSQL FK metadata | NOT VERIFIED | Stack stopped on migration failure |
| Phase 6.11 | NOT RUN | Admin-1 failure |
| Phase 7.2 | NOT RUN | Admin-1 failure |
| Phase 7.4 | NOT RUN | Admin-1 failure |
| Fresh reset #1 | FAIL | Admin-1 statement 94 |
| Fresh reset #2 | NOT RUN | Stop-on-failure rule |
| Backend tests | NOT RUN | Migration chain prerequisite failed |
| Frontend tests | NOT RUN | Migration chain prerequisite failed |
| TypeScript | NOT RUN | Migration chain prerequisite failed |
| Build | NOT RUN | Migration chain prerequisite failed |
| `git diff --check` | PASS before local run | No whitespace errors at the static audit point |

## Remote status

Remote production-like database modified: **NO**

No remote schema, data, migration history, or ledger operation was performed. Link metadata was ignored by the guarded wrapper.

## Remaining blocker and next safe step

Admin-1’s deterministic application-user seed is incompatible with the authoritative `public.users.auth_user_id → auth.users.id` foreign key because its placeholder auth UUIDs have no parent rows.

The next safe step is a separately scoped Admin-1 seed/auth-provisioning provenance review. It must decide whether demo application-user/student seed data belongs in migrations at all, whether it should move to a local seed/provisioning workflow, or whether deterministic local GoTrue accounts can be created through a supported mechanism before the public rows. It must not insert raw `auth.users` rows merely to make the migration pass and must not weaken the authoritative foreign key.
