# Phase 7.9.12 — Recovery Series Review & Commit Gate

## Phase

Phase 7.9.12 — Recovery Series Review & Commit Gate

## Status

**READY_TO_COMMIT**

The migration, schema-contract, local Auth, backend, frontend, TypeScript, build,
and Git whitespace gates pass. The separate Phase 6.22 evidence modification
has been investigated under Phase 7.9.13 and is explicitly excluded from the
recovery commit boundary.

## Historical Provenance

- Original Phase 3.5 migration: **UNRECOVERED**
- Trusted schema export: **verified provenance**
- Trusted export: `docs/schema/schemaV2_export.sql`
- Trusted export SHA-256: `6BD4BD8A1E6B14524E0BDA57539752C3E1E1808A860CF40FD253D99FE1203A7`
- Reconstructed baseline: **NEW RECONSTRUCTED AUTHORITATIVE BASELINE**
- Reconstructed baseline: `20250717000000_reconstructed_pre_phase_3_6_baseline.sql`
- Reconstructed baseline SHA-256: `7FD1EA5C096EB47667A2BA55CC1BF4A872C959E12300C2110A69A698CA6E6429`
- Historical migration identity: **not recovered**

The reconstructed file is not, and must not be represented as, the historical
Phase 3.5 migration. Phase 7.9.8 and 7.9.9 preserve the failures and evidence
that led to the new baseline and were not rewritten to imply recovered history.

## Recovery Series Reviewed

- 7.9.4
- 7.9.5
- 7.9.6
- 7.9.7
- 7.9.8
- 7.9.9
- 7.9.10
- 7.9.11
- 7.9.12

## Repository Safety Inventory

| Category | Files | Expected? |
| --- | ---: | --- |
| Migration recovery | 3 | YES |
| Auth/application contract | 14 | YES |
| Validation scripts | 2 | YES |
| Documentation | 18 recovery/current-contract files | YES |
| Tests | 9 | YES |
| Unrelated, separately classified | 1 tracked evidence file | YES, exclude from recovery commit |
| Sensitive/generated | ignored local-only files; 2 untracked generated directories removed | YES, excluded from commit |

### Complete recovery-series worktree inventory

Migration recovery:

- `supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql`
- `supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql`
- `supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql`

Auth/application contract and validation:

- `backend/app/api/students.py`
- `backend/app/db/supabase.py`
- `backend/app/repositories/admin_academics.py`
- `backend/app/repositories/tenancy.py`
- `backend/app/services/authorization.py`
- `backend/app/services/student_academic_context.py`
- `backend/app/services/student_academic_profile.py`
- `backend/app/services/student_attendance.py`
- `backend/app/services/student_context.py`
- `backend/app/services/student_notices.py`
- `backend/app/services/student_registration.py`
- `backend/scripts/check_auth_users.py`
- `backend/scripts/validation/test_physical_phase_4_2.py`
- `backend/scripts/validation/test_physical_phase_4_3.py`
- `scripts/validation/invoke_local_supabase.ps1`
- `scripts/validation/provision_local_demo_users.ps1`

Tests:

- `backend/tests/test_approval_workflow_phase_6_13_4.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_institution_registration_phase_6_13_3.py`
- `backend/tests/test_organization_institution_phase_6_13_1.py`
- `backend/tests/test_organization_registration_phase_6_13_2.py`
- `backend/tests/test_registration_error_handling.py`
- `backend/tests/test_role_scope_enforcement_phase_6_13_7.py`
- `backend/tests/test_student_registration_phase_6_3.py`
- `backend/tests/test_user_registration_phase_6_13_5.py`

Documentation:

- `docs/locks/PHASE_6_6_LOCK.md`
- `docs/locks/PHASE_6_9_LOCK.md`
- `docs/status/PHASE_6_2_STATUS.md`
- `docs/status/PHASE_6_3_STATUS.md`
- `docs/status/PHASE_6_6_STATUS.md`
- `docs/status/PHASE_6_7_STATUS.md`
- `docs/status/PHASE_6_9_STATUS.md`
- `docs/status/PHASE_6_13_6_SCOPE_REPORT.md`
- `docs/status/PHASE_6_15_1_AUTH_UI_AUDIT.md`
- `docs/status/PHASE_6_16_1_STUDENT_DASHBOARD_HARDENING.md`
- `docs/status/PHASE_6_16_2_STUDENT_ACADEMIC_DETAIL_EXPERIENCE.md`
- `docs/status/PHASE_6_16_3_STUDENT_INFORMATION_RESOURCE_EXPERIENCE.md`
- `docs/status/PHASE_6_17_FACULTY_EXPERIENCE_FOUNDATION.md`
- `docs/status/PHASE_7_9_8_AUTHORITATIVE_BASELINE_RECONSTRUCTION.md`
- `docs/status/PHASE_7_9_9_USERS_PK_PROVENANCE_REVIEW.md`
- `docs/status/PHASE_7_9_10_USERS_SCHEMA_CONTRACT_REPAIR.md`
- `docs/status/PHASE_7_9_11_ADMIN_AUTH_SEED_PROVISIONING.md`
- `docs/status/PHASE_7_9_12_RECOVERY_SERIES_COMMIT_GATE.md`

Unexpected/unrelated:

- `docs/evidence/complete_product_demo_phase_6_22.json` — a later generated
  run replaced the committed 40/40 PASS evidence with a 35/39 result containing
  four failures. It is not part of the Phase 7.9.4–7.9.11 contract repair, was
  not silently reverted, and requires explicit human disposition before commit.

## Migration Chain

- Total local SQL migrations: **16**
- Filename format: **PASS**
- Timestamp ordering: **PASS**
- Duplicate timestamps: **none**
- Duplicate migration names: **none**
- Accidental/malformed migration files: **none found**
- Missing files in the reconstructed local chain: **none**
- Historical Phase 3.5 migration: **UNRECOVERED**, by design not fabricated
- Fresh local reset #1: **PASS**, all 16 migrations applied
- Fresh local reset #2: **PASS**, all 16 migrations applied
- Migration ledger: **PASS**, 16 ordered records, no duplicate or skipped version
- Phase 6.11: **PASS** (`student_notifications`, indexes, constraints/function/trigger chain present)
- Phase 7.2: **PASS** (visibility column/check/index and public retrieval RPC present)
- Phase 7.4: **PASS** (RPC replacement present, 1536-dimension hardening present,
  execution granted only to `postgres` and `service_role`)
- Vector extension and HNSW index: **PASS**

Both resets used `scripts/validation/invoke_local_supabase.ps1`, which verified
Docker Desktop Linux and invoked `supabase db reset --local`. Link metadata was
reported but ignored. The only reset warnings were the absent optional
`supabase/seed.sql` and an available Supabase CLI update; neither was a failure.

The baseline creates the verified pre-Phase-3.6 objects, uses
`public.users.id`, supplies Phase 3.6 prerequisites, contains no Admin-1,
Phase 7.2, or Phase 7.4 objects, embeds no environment credentials, and applied
deterministically in both fresh resets.

## Schema Contract

The validated contract is:

```text
auth.users.id
      ↓ public.users.auth_user_id
public.users.id
      ↓
user_roles.user_id
students.user_id
```

- `public.users.id` primary key: **PASS**
- `public.users.auth_user_id → auth.users.id`: **PASS**
- Stale executable `public.users.user_id` assumptions: **none**
- All 16 foreign keys targeting `public.users`: **PASS**, target `users(id)`
- Admin-1 structural DDL: **preserved and PASS**
- Admin-1 Auth FK: **enforced, not weakened**
- Auth-to-public mappings after clean provisioning: **3/3**, no orphans
- Provisioner repeat run: **0 created, 3 reused**, mapping/login checks PASS
- Rollback-only Auth/RBAC/student join: **PASS**, one complete joined mapping
- Synthetic relationship rows after rollback: **0**

Occurrences of `users.user_id` remaining in Phase 7.9.8–7.9.10 documents are
legitimate historical evidence of the discovered defect. Current executable
SQL, runtime code, validation scripts, tests, and current-contract documents use
the authoritative `users.id` contract.

## Security Review

- Tracked-change secrets scan: **PASS**, no private key, reusable credential,
  JWT, bearer token, service-role key, access token, or refresh token found.
- `provision_local_demo_users.ps1`: **PASS**. It requires an environment-supplied
  ephemeral password, never prints it, obtains the transient key from local
  status, accepts only `http://127.0.0.1:54321`, rejects `DOCKER_HOST`, verifies
  Docker Desktop Linux, uses the supported GoTrue Admin API, and preserves the
  Auth FK.
- `invoke_local_supabase.ps1`: **PASS**. Reset requires explicit confirmation
  and always supplies `--local`; Docker target checks fail closed.
- No raw inserts into protected Auth tables, FK disabling, RLS disabling,
  migration skipping, ledger repair, linked push, or remote destructive command
  was found or executed.
- `backend/.env` contains non-empty local credentials but is untracked and
  ignored by both repository and backend ignore rules. Values were not printed.
- `supabase/.temp` contains generated local Supabase runtime secrets and is
  ignored. Values were not printed.
- Existing backend log files are ignored/untracked; no high-confidence embedded
  token was found. They are local artifacts and must not be force-added.
- `.env.example` files are tracked configuration templates and were retained.
- Generated `backend/.pytest-tmp/` and `supabase/.branches/` directories were
  verified as workspace-local, untracked artifacts and removed in this phase.

## Regression Results

- Backend normal split: **PASS** — 2,126 passed, 15 skipped, 2 explicitly
  deselected debug-only cases, 6 warnings.
- Backend debug split: **PASS** — 2 passed.
- Transparency note: an initial `DEBUG=false` run collected the two debug-only
  cases and exited with those two failures (`KeyError: diagnostics`), while the
  other 2,126 tests passed. Both cases passed under their intended `DEBUG=true`
  mode; the subsequent explicit split run exited zero. The initial result is not
  hidden or reclassified as an application defect.
- Relevant migration/recovery/security coverage: **PASS**, included in the full
  maintained `backend/tests` run.
- Frontend: **PASS** — 50 files, 431 tests, 0 failures.
- TypeScript: **PASS** — `npx tsc --noEmit -p tsconfig.json`.
- Frontend build: **PASS** — 97 modules transformed.
- `git diff --check`: **PASS**.

The six backend warnings are one Starlette/httpx deprecation warning, three
Pytest collection warnings for Pydantic classes named `TestResult*`, and two
Supabase client deprecation warnings. They are warnings, not recovery failures.

## Repository Changes During Phase 7.9.12

- Added this commit-gate report.
- Corrected three current-contract documentation remnants:
  `PHASE_6_13_6_SCOPE_REPORT.md`, `PHASE_6_2_STATUS.md`, and
  `PHASE_6_3_STATUS.md` now identify `public.users.id` as the application key.
- Removed only the verified untracked generated directories
  `backend/.pytest-tmp/` and `supabase/.branches/`.
- Preserved the unrelated Phase 6.22 evidence modification for explicit human
  review; no unrelated user work was reverted.
- No commit was created or amended.

## Remote Safety

```text
Remote Supabase database modified: NO
Remote Auth modified: NO
Remote migrations applied: NO
Remote data modified: NO
```

No `supabase db push --linked`, remote migration, remote Auth/data operation,
PITR/backup change, DNS/TLS change, deployment, or production infrastructure
operation was executed during Phase 7.9.12.

**REMOTE DATABASE MODIFIED: NO**

## Commit Decision

```text
COMMIT GATE: READY_TO_COMMIT
```

The recovery series is internally consistent and all technical validation
gates pass. Phase 7.9.13 established that
`docs/evidence/complete_product_demo_phase_6_22.json` is a newer, validly
generated Phase 6.22 run with recorded failures, unrelated to the migration
recovery. It remains unchanged and is explicitly outside the Phase 7.9 recovery
commit boundary. Do not include that evidence file in a recovery-only commit.

## Remaining Work

1. Keep the Phase 6.22 evidence file out of the recovery commit. Its failed
   generation checks remain a separate Phase 6.22 follow-up.
2. Confirm the intended recovery file selection before any future commit. No
   commit was created in these review phases.
3. A local recovery commit decision does not authorize remote deployment.

Any later remote phase must separately address remote backup/recovery readiness,
production/staging classification, remote migration reconciliation, TLS and
hosting/DNS, monitoring and alerts, rollback strategy, and distributed abuse
controls before horizontal scaling.
