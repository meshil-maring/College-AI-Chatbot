# Phase 7.9.9 — `public.users` Primary-Key Evolution & Admin-1 Provenance Review

## Decision

**PHASE 7.9.9 STATUS: COMPLETE**

**Conclusion: ADMIN-1 INCORRECT**

For the authoritative repository migration chain, `public.users.id` is the established primary key. No authoritative migration creates `public.users.user_id`, renames `users.id`, drops `users.id`, changes the primary key, or adds a compatibility alias. `20260909000000_phase_admin_1_admin_student_schema.sql` was authored against an undocumented live/remote schema assumption and is inconsistent with the committed source schema and the reproducible migration chain.

This conclusion does not authorize a repair in this phase. Neither the reconstructed baseline nor Admin-1 was modified, no local migration ledger was repaired, and the linked remote project was not inspected or modified.

## Known state preserved

| Fact | Value |
| --- | --- |
| Historical Phase 3.5 migration | UNRECOVERED |
| Reconstructed baseline | `20250717000000_reconstructed_pre_phase_3_6_baseline.sql` |
| Trusted export | `docs/schema/schemaV2_export.sql` |
| Trusted export commit | `ee9ceee404452ccf4eb824a9594c5b2203290318` |
| Trusted export SHA-256 | `6BD4BD8A1E6B14524E0B0DA57539752C3E1E1808A860CF40FD253D99FE1203A7` |
| Reconstructed baseline SHA-256 | `7FD1EA5C096EB47667A2BA55CC1BF4A872C959E12300C2110A69A698CA6E6429` |
| Failing migration | `20260909000000_phase_admin_1_admin_student_schema.sql` |
| Failure | referenced `public.users.user_id` does not exist, SQLSTATE `42703` |

## Evidence classification

| Evidence | Classification | Use |
| --- | --- | --- |
| Trusted schema export at commit `ee9ceee` | AUTHORITATIVE | Establishes the original committed table contract |
| Surviving migrations and their Git history | AUTHORITATIVE | Establishes recorded schema transitions |
| Admin-1 at main-line commit `99e114a` and parent `ca70cba` | AUTHORITATIVE | Establishes Admin-1 authoring context |
| Reconstructed baseline | AUTHORITATIVE for the new local chain | Faithfully reproduces the verified export; does not prove missing history |
| Backend, frontend, tests, and phase documents | SUPPORTING | Shows the application contract adopted after Admin-1 |
| Admin-1 comments about the “actual” remote database | UNTRUSTED / INSUFFICIENT for history | Describes undocumented external state, not a migration |
| Unreachable Admin-1/Phase 6.13 blob variants | UNTRUSTED / INSUFFICIENT | No transition DDL and no stronger lineage than the committed artifacts |
| Any inferred or guessed `user_id` transition | UNTRUSTED / INSUFFICIENT | Cannot establish historical behavior |

## Question 1 — What does the trusted schema export define?

The export defines:

```sql
CREATE TABLE IF NOT EXISTS public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    auth_user_id uuid NOT NULL,
    email text NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    display_name text,
    status text DEFAULT 'active'::text NOT NULL,
    created_at timestamptz DEFAULT now() NOT NULL,
    updated_at timestamptz DEFAULT now() NOT NULL,
    last_login_at timestamptz,
    CONSTRAINT users_status_check
        CHECK (status = ANY (ARRAY['active', 'inactive', 'deactivated']))
);
```

### Complete `users` object inventory

| Category | Definition |
| --- | --- |
| Primary key | `users_pkey PRIMARY KEY (id)` |
| Unique constraints | `users_auth_user_id_key (auth_user_id)`; `users_email_key (email)` |
| Foreign key | `users_auth_user_id_fkey`: `auth_user_id → auth.users(id)` |
| Standalone indexes | None; PK/unique constraints provide their backing indexes |
| RLS | Not enabled in the export |
| Policies | None |
| Triggers | None |
| Dependent functions | None |
| Explicit table grant | `GRANT ALL ON TABLE public.users TO service_role` |

The export contains no `public.users.user_id` column. Its child relations consistently reference `public.users(id)`, including `conversations.user_id`, `user_roles.user_id`, document reviewer/creator fields, and knowledge-source owner/reviewer/approver fields.

**Answer:** `users.id` exists and is the primary key. `users.user_id` is absent.

## Question 2 — What does Admin-1 expect?

Admin-1 is 1,134 working-tree lines and was reviewed completely. It creates eight tables, constraints, indexes, grants, comments, and deterministic demo data. It creates no function, trigger, RLS policy, or users-table transition.

| Admin-1 object/use | Referenced users column | Expected target | Evidence |
| --- | --- | --- | --- |
| CLI failing statement 8, `students_user_id_fkey` (source lines 98–102) | `students.user_id` | `public.users.user_id` | AUTHORITATIVE migration |
| `notices_created_by_fkey` (lines 468–472) | `notices.created_by` | `public.users.user_id` | AUTHORITATIVE migration |
| `admin_audit_log_actor_user_id_fkey` (lines 506–510) | `admin_audit_log.actor_user_id` | `public.users.user_id` | AUTHORITATIVE migration |
| `public.users` seed insert (lines 614–650) | inserts `user_id` | `public.users.user_id`; conflict target `user_id` | AUTHORITATIVE migration |
| `user_roles` seed insert | child `user_roles.user_id` | Assumes seeded users keyed by the same UUIDs | AUTHORITATIVE migration |
| Student/profile and audit seed rows | child user identifiers | Assumes the Admin-1 `public.users` inserts succeeded | AUTHORITATIVE migration |

Admin-1 comments explicitly say its foreign keys use the “ACTUAL primary-key column names in the remote database” and call the export’s `id` names “stale.” That sentence proves the authoring assumption, but it does not provide repository provenance for a schema transition. No DDL in Admin-1 creates or renames the alleged column.

**Answer:** Admin-1 expects `public.users.user_id` in three foreign keys and its user seed DML.

## Questions 3 and 4 — Does an authoritative migration introduce or rename `users.user_id`?

**No.** Repository-wide and history searches found:

- no `ALTER TABLE public.users ADD COLUMN user_id`;
- no `ALTER TABLE public.users RENAME COLUMN id TO user_id`;
- no migration dropping `users.id`;
- no migration replacing `users_pkey`;
- no alias/compatibility column or trigger;
- no earlier migration creating a different `public.users` definition.

The only current migration statement defining the primary key is the reconstructed baseline’s faithful export statement `PRIMARY KEY (id)`. Later migrations reference `users.user_id`, but references are consumers, not definitions.

### Narrow unreachable-object search

The Phase 7.9.7 broad recovery was not repeated. A narrow scan examined 855 unreachable blobs for:

```text
users.user_id
REFERENCES "public"."users" ("user_id")
RENAME COLUMN id TO user_id
phase_admin_1
admin_student_schema
```

Eleven blobs contained the `users.user_id` foreign-key pattern. Ten were Admin-1 variants and one was a Phase 6.13 variant. None created `public.users`, added `user_id`, or renamed `id`; zero blobs contained the required rename DDL. They therefore repeat the assumption and do not identify an intervening migration.

**Answer to Question 3:** No authoritative migration introduces `users.user_id`.

**Answer to Question 4:** No authoritative migration renames `users.id`.

## Git provenance and Admin-1 authoring context

| Event | Commit | Parent | Finding |
| --- | --- | --- | --- |
| Trusted export introduced | `ee9ceee404452ccf4eb824a9594c5b2203290318` | root | Defines `users.id`; commit is an ancestor of current `main` |
| Admin-1 introduced on main line | `99e114ae3aafad59b5645224693344f106da5ac7` | `ca70cba2292b9676abfa8049e2147bc2c4412fbb` | Adds Admin-1 and application code, but no users-key migration |
| Export moved under `docs/schema` | `751940f8a0cef043e0107e96690383d7f683caa6` | `58736f78b6aea688d4492afd1abb2a9c8af797ee` | 100% rename; schema semantics unchanged |

Admin-1’s parent has only the four surviving Phase 3.6–3.8 migrations and no migration introducing `users.user_id`. Commit `99e114a` adds Admin-1, Admin-2 files, application code, diagnostic scripts, and an empty `auth_schema.sql`; it does not add a users-table migration. Its checked-in Admin-1 blob is the same blob used by the current file.

Disconnected agent/checkpoint commits contain earlier Admin-1 drafts that also assume `users.user_id`. They do not contain a transition migration and therefore show persistence of the assumption, not provenance for it.

The authoring context establishes that Admin-1 was built against external live-schema knowledge rather than the repository’s reproducible schema history. Per this phase’s safety rule, that external-state assertion cannot override the committed export.

## Question 5 — What identifier does application authentication/RBAC use?

Current application code consistently expects `public.users.user_id`:

- `backend/app/db/supabase.py` selects `user_id` from `users` by `auth_user_id` and returns it as canonical identity.
- `backend/app/services/authorization.py` describes and implements `JWT sub → users.user_id → user_roles`.
- `backend/app/repositories/tenancy.py` selects `user_id, auth_user_id, email` from `users`.
- `backend/app/services/student_registration.py` selects `user_id, email` from `users`.
- Student repositories join `students.user_id` to the server-resolved identity.
- Frontend DTOs expose `user_id` as the application-facing identifier.

RBAC uses the same UUID through `user_roles.user_id`; authentication begins with `auth_user_id` (JWT subject) and then expects the public user row to expose `user_id`.

This is **SUPPORTING** evidence. Much of it was introduced with or after Admin-1 and therefore demonstrates architectural adoption of Admin-1’s naming assumption, not an earlier authoritative database transition.

**Answer:** Authentication and RBAC currently expect `users.user_id`; this does not make that column part of the authoritative pre-Admin migration chain.

## Documentation evidence

Later locks and status reports consistently describe chains such as:

```text
JWT → public.users.user_id → students.user_id
JWT → public.users.user_id → user_roles → roles
```

Examples include Phase 6.2, 6.6, 6.7, 6.9, 6.13.6, 6.15.1, and Phase 6.16 reports. An earlier Phase 4.2 architecture report instead documents conversation `user_id` as a foreign key to `users.id`, matching the export.

The later documents are **SUPPORTING** evidence of the intended post-Admin application vocabulary. None documents or identifies a migration that changes the primary key, so none closes the historical gap.

## Evolution timeline

| Stage | `users.id` | `users.user_id` | Primary key | Evidence |
| --- | --- | --- | --- | --- |
| Initial committed schema (`ee9ceee`) | Exists | Absent | `id` | AUTHORITATIVE export |
| Reconstructed pre-Phase-3.6 baseline | Exists | Absent | `id` | AUTHORITATIVE new baseline derived from verified export |
| Phase 3.6–3.8 | Exists | Absent | `id` | AUTHORITATIVE migrations do not alter `users` |
| Immediately before Admin-1 | Exists by recorded lineage | Absent by recorded lineage | `id` | AUTHORITATIVE migration history |
| Admin-1 (`99e114a`) | Not altered | Assumed, not created | Assumed `user_id` | AUTHORITATIVE file; unsupported external-state comment |
| Phase 6.x application and migrations | Still never renamed in migration history | Repeatedly consumed/assumed | Application assumes `user_id` | Migrations authoritative as consumers; code/docs supporting |

The first identifier change is not a schema transition. It is the unsupported assumption introduced by Admin-1.

## Question 6 — Is an intervening migration missing?

**NO identifiable authoritative intervening migration is missing.** Searches of reachable history, the Admin-1 authoring context, and narrowly relevant unreachable objects found no such migration or DDL. It is impossible to prove that no unrecorded SQL was ever applied to an external database, but unrecorded external state is not migration provenance and cannot establish a missing migration under this phase’s rules.

The supported repository-history conclusion is therefore Result A, not Result B.

## Question 7 — Can Admin-1 be safely validated without changing the baseline?

**Not as currently written.** The baseline must remain faithful to `users.id`. Admin-1 cannot execute against that authoritative state because it references and inserts a nonexistent `users.user_id` column.

Admin-1 may be validated only after a separately authorized correction phase establishes a coherent forward contract. That work must account for all of the following, rather than changing only the first failing foreign key:

- all three Admin-1 foreign keys to `public.users`;
- Admin-1’s `public.users` insert and conflict target;
- later migrations that consume `public.users.user_id`;
- authentication/RBAC repositories that select `users.user_id`;
- child tables whose column is legitimately named `user_id` but whose target key is currently `users.id`.

## Final safeguards and next safe step

- Baseline modified in Phase 7.9.9: **NO**
- Admin-1 modified in Phase 7.9.9: **NO**
- Local migration ledger modified: **NO**
- Remote production-like database inspected or modified: **NO**

The next safe step is a separately authorized schema-contract repair phase. It should choose and document one forward architecture: either correct Admin-1 and downstream consumers to target the authoritative `users.id`, or create an explicitly new (not historical) key-evolution migration and update the full chain coherently. The evidence in this review supports correcting the inconsistent consumers; it does not support pretending that a historical `id → user_id` migration existed.
