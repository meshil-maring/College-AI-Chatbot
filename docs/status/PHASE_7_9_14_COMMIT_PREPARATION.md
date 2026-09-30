# Phase 7.9.14 — Recovery Series Commit Preparation & Final Diff Gate

## Phase Status

```text
READY_FOR_COMMIT
```

The recovery commit boundary contains 47 identified files. There are no staged
changes. The modified Phase 6.22 artifact and this Phase 7.9.14 preparation
report are explicitly outside the recovery commit list. No file in the
recovery list is unknown.

## Git State and Inventory

At review time, the worktree contained 40 tracked modifications and 8
untracked, non-ignored files. There were no deletions and the staged diff was
empty. Of these 48 pre-existing paths, 47 belong to the Phase 7.9 recovery
series and one is independent Phase 6.22 evidence.

| Classification | Count | Disposition |
| --- | ---: | --- |
| RECOVERY | 47 | Include in the recovery commit manifest below |
| PHASE_6_22_UNRELATED | 1 | Preserve unchanged; exclude |
| USER_WORK | 0 | None identified among pre-existing worktree changes |
| GENERATED | 0 changed/untracked candidates | Ignored local outputs are separately inventoried below |
| SENSITIVE | 0 changed/untracked candidates | No high-confidence secret match |
| UNKNOWN | 0 | All changed and untracked paths classified |

The new Phase 7.9.14 preparation report is a task output, not part of the
Phase 7.9.4–7.9.13 recovery payload. Keep it separate from the recovery commit.

### Recovery candidate classification

| File | Phase | Type | Recovery commit? | Reason |
| --- | --- | --- | --- | --- |
| `backend/app/api/students.py` | 7.9.10 | Runtime code | YES | Correct identity-chain documentation to `users.id`. |
| `backend/app/db/supabase.py` | 7.9.10 | Runtime code | YES | Select `users.id` under the existing application-facing `user_id` alias. |
| `backend/app/repositories/admin_academics.py` | 7.9.10 | Runtime code | YES | Document child-to-parent identity mapping accurately. |
| `backend/app/repositories/tenancy.py` | 7.9.10 | Runtime code | YES | Query `users.id` using the application alias. |
| `backend/app/services/authorization.py` | 7.9.10 | Runtime code | YES | Document RBAC link through `user_roles.user_id`. |
| `backend/app/services/student_academic_context.py` | 7.9.10 | Runtime code | YES | Document server-resolved `users.id` identity. |
| `backend/app/services/student_academic_profile.py` | 7.9.10 | Runtime code | YES | Document student join through child `students.user_id`. |
| `backend/app/services/student_attendance.py` | 7.9.10 | Runtime code | YES | Document student join through child `students.user_id`. |
| `backend/app/services/student_context.py` | 7.9.10 | Runtime code | YES | Document authoritative identity chain. |
| `backend/app/services/student_notices.py` | 7.9.10 | Runtime code | YES | Document server-side student resolution through `users.id`. |
| `backend/app/services/student_registration.py` | 7.9.10 | Runtime code | YES | Read, return, and delete public users by `id`; retain API alias. |
| `backend/scripts/check_auth_users.py` | 7.9.10 | Validation script | YES | Insert and clean up by `public.users.id`. |
| `backend/scripts/validation/test_physical_phase_4_2.py` | 7.9.10 | Validation script | YES | Resolve application identity from `public.users.id`. |
| `backend/scripts/validation/test_physical_phase_4_3.py` | 7.9.10 | Validation script | YES | Resolve application identity from `public.users.id`. |
| `backend/tests/test_approval_workflow_phase_6_13_4.py` | 7.9.10 | Test | YES | Fake user rows use the actual `id` column. |
| `backend/tests/test_auth.py` | 7.9.10 | Test | YES | Expect the `user_id:id` PostgREST projection. |
| `backend/tests/test_institution_registration_phase_6_13_3.py` | 7.9.10 | Test | YES | Fake user inserts return `id`. |
| `backend/tests/test_organization_institution_phase_6_13_1.py` | 7.9.10 | Test | YES | Correct identity-chain description. |
| `backend/tests/test_organization_registration_phase_6_13_2.py` | 7.9.10 | Test | YES | Fake user inserts return `id`. |
| `backend/tests/test_registration_error_handling.py` | 7.9.10 | Test | YES | Fake users schema uses `id`. |
| `backend/tests/test_role_scope_enforcement_phase_6_13_7.py` | 7.9.10 | Test | YES | Correct RBAC identity-chain description. |
| `backend/tests/test_student_registration_phase_6_3.py` | 7.9.10 | Test | YES | Fake user inserts return `id`. |
| `backend/tests/test_user_registration_phase_6_13_5.py` | 7.9.10 | Test | YES | Fake user inserts return `id`. |
| `docs/locks/PHASE_6_6_LOCK.md` | 7.9.10 | Documentation | YES | Correct current identity relationship. |
| `docs/locks/PHASE_6_9_LOCK.md` | 7.9.10 | Documentation | YES | Correct student FK target. |
| `docs/status/PHASE_6_2_STATUS.md` | 7.9.10 | Documentation | YES | Correct users PK and Auth mapping. |
| `docs/status/PHASE_6_3_STATUS.md` | 7.9.10 | Documentation | YES | Correct users PK and Auth mapping. |
| `docs/status/PHASE_6_6_STATUS.md` | 7.9.10 | Documentation | YES | Correct current identity relationship. |
| `docs/status/PHASE_6_7_STATUS.md` | 7.9.10 | Documentation | YES | Correct current identity relationship. |
| `docs/status/PHASE_6_9_STATUS.md` | 7.9.10 | Documentation | YES | Correct student FK target. |
| `docs/status/PHASE_6_13_6_SCOPE_REPORT.md` | 7.9.10 | Documentation | YES | Correct public users schema and RBAC mapping. |
| `docs/status/PHASE_6_15_1_AUTH_UI_AUDIT.md` | 7.9.10 | Documentation | YES | Correct authenticated identity chain. |
| `docs/status/PHASE_6_16_1_STUDENT_DASHBOARD_HARDENING.md` | 7.9.10 | Documentation | YES | Correct student identity resolution. |
| `docs/status/PHASE_6_16_2_STUDENT_ACADEMIC_DETAIL_EXPERIENCE.md` | 7.9.10 | Documentation | YES | Correct student identity and tenant chain. |
| `docs/status/PHASE_6_16_3_STUDENT_INFORMATION_RESOURCE_EXPERIENCE.md` | 7.9.10 | Documentation | YES | Correct student profile join description. |
| `docs/status/PHASE_6_17_FACULTY_EXPERIENCE_FOUNDATION.md` | 7.9.10 | Documentation | YES | Correct student identity resolution. |
| `scripts/validation/invoke_local_supabase.ps1` | 7.9.8 | Validation script | YES | Preserve action arguments as an array; local-only guards remain. |
| `scripts/validation/provision_local_demo_users.ps1` | 7.9.11 | Validation script | YES | Create Auth identities locally through GoTrue and verify mapping/idempotency. |
| `supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql` | 7.9.8 | Migration | YES | Faithful new baseline from trusted export; not claimed as recovered history. |
| `supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql` | 7.9.10–7.9.11 | Migration | YES | Repair user FKs and remove invalid deployment-dependent demo seed; preserve structural DDL. |
| `supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql` | 7.9.10 | Migration | YES | Correct four user FKs to reference `public.users(id)`. |
| `docs/status/PHASE_7_9_8_AUTHORITATIVE_BASELINE_RECONSTRUCTION.md` | 7.9.8 | Documentation | YES | Record baseline provenance, failures, and validation. |
| `docs/status/PHASE_7_9_9_USERS_PK_PROVENANCE_REVIEW.md` | 7.9.9 | Documentation | YES | Preserve historical PK provenance findings. |
| `docs/status/PHASE_7_9_10_USERS_SCHEMA_CONTRACT_REPAIR.md` | 7.9.10 | Documentation | YES | Record contract repairs and encountered migration failure. |
| `docs/status/PHASE_7_9_11_ADMIN_AUTH_SEED_PROVISIONING.md` | 7.9.11 | Documentation | YES | Record seed boundary and successful local validation. |
| `docs/status/PHASE_7_9_12_RECOVERY_SERIES_COMMIT_GATE.md` | 7.9.12 | Documentation | YES | Record final recovery review and commit gate. |
| `docs/status/PHASE_7_9_13_PHASE_6_22_EVIDENCE_DISPOSITION.md` | 7.9.13 | Documentation | YES | Record evidence provenance and exclude it from recovery scope. |
| `docs/evidence/complete_product_demo_phase_6_22.json` | 6.22 | Evidence | NO | Independent September 29 run, preserved as `PRESERVE_AND_RECLASSIFY` in Phase 7.9.13. |
| `docs/status/PHASE_7_9_14_COMMIT_PREPARATION.md` | 7.9.14 | Preparation report | NO | This manifest documents the recovery commit boundary; it is outside the defined Phase 7.9.4–7.9.13 payload. |

Phase 7.9.4–7.9.7 status reports were reviewed and remain tracked, unchanged
files; they are not additions to this worktree diff.

## Recovery Commit Scope

The exact 47 paths safe to stage for a recovery-only commit are:

```text
backend/app/api/students.py
backend/app/db/supabase.py
backend/app/repositories/admin_academics.py
backend/app/repositories/tenancy.py
backend/app/services/authorization.py
backend/app/services/student_academic_context.py
backend/app/services/student_academic_profile.py
backend/app/services/student_attendance.py
backend/app/services/student_context.py
backend/app/services/student_notices.py
backend/app/services/student_registration.py
backend/scripts/check_auth_users.py
backend/scripts/validation/test_physical_phase_4_2.py
backend/scripts/validation/test_physical_phase_4_3.py
backend/tests/test_approval_workflow_phase_6_13_4.py
backend/tests/test_auth.py
backend/tests/test_institution_registration_phase_6_13_3.py
backend/tests/test_organization_institution_phase_6_13_1.py
backend/tests/test_organization_registration_phase_6_13_2.py
backend/tests/test_registration_error_handling.py
backend/tests/test_role_scope_enforcement_phase_6_13_7.py
backend/tests/test_student_registration_phase_6_3.py
backend/tests/test_user_registration_phase_6_13_5.py
docs/locks/PHASE_6_6_LOCK.md
docs/locks/PHASE_6_9_LOCK.md
docs/status/PHASE_6_13_6_SCOPE_REPORT.md
docs/status/PHASE_6_15_1_AUTH_UI_AUDIT.md
docs/status/PHASE_6_16_1_STUDENT_DASHBOARD_HARDENING.md
docs/status/PHASE_6_16_2_STUDENT_ACADEMIC_DETAIL_EXPERIENCE.md
docs/status/PHASE_6_16_3_STUDENT_INFORMATION_RESOURCE_EXPERIENCE.md
docs/status/PHASE_6_17_FACULTY_EXPERIENCE_FOUNDATION.md
docs/status/PHASE_6_2_STATUS.md
docs/status/PHASE_6_3_STATUS.md
docs/status/PHASE_6_6_STATUS.md
docs/status/PHASE_6_7_STATUS.md
docs/status/PHASE_6_9_STATUS.md
scripts/validation/invoke_local_supabase.ps1
scripts/validation/provision_local_demo_users.ps1
supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql
supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql
supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql
docs/status/PHASE_7_9_8_AUTHORITATIVE_BASELINE_RECONSTRUCTION.md
docs/status/PHASE_7_9_9_USERS_PK_PROVENANCE_REVIEW.md
docs/status/PHASE_7_9_10_USERS_SCHEMA_CONTRACT_REPAIR.md
docs/status/PHASE_7_9_11_ADMIN_AUTH_SEED_PROVISIONING.md
docs/status/PHASE_7_9_12_RECOVERY_SERIES_COMMIT_GATE.md
docs/status/PHASE_7_9_13_PHASE_6_22_EVIDENCE_DISPOSITION.md
```

For a later commit, after reviewing the staged diff, the user can stage exactly
these paths with:

```powershell
git add -- backend/app/api/students.py backend/app/db/supabase.py backend/app/repositories/admin_academics.py backend/app/repositories/tenancy.py backend/app/services/authorization.py backend/app/services/student_academic_context.py backend/app/services/student_academic_profile.py backend/app/services/student_attendance.py backend/app/services/student_context.py backend/app/services/student_notices.py backend/app/services/student_registration.py backend/scripts/check_auth_users.py backend/scripts/validation/test_physical_phase_4_2.py backend/scripts/validation/test_physical_phase_4_3.py backend/tests/test_approval_workflow_phase_6_13_4.py backend/tests/test_auth.py backend/tests/test_institution_registration_phase_6_13_3.py backend/tests/test_organization_institution_phase_6_13_1.py backend/tests/test_organization_registration_phase_6_13_2.py backend/tests/test_registration_error_handling.py backend/tests/test_role_scope_enforcement_phase_6_13_7.py backend/tests/test_student_registration_phase_6_3.py backend/tests/test_user_registration_phase_6_13_5.py docs/locks/PHASE_6_6_LOCK.md docs/locks/PHASE_6_9_LOCK.md docs/status/PHASE_6_13_6_SCOPE_REPORT.md docs/status/PHASE_6_15_1_AUTH_UI_AUDIT.md docs/status/PHASE_6_16_1_STUDENT_DASHBOARD_HARDENING.md docs/status/PHASE_6_16_2_STUDENT_ACADEMIC_DETAIL_EXPERIENCE.md docs/status/PHASE_6_16_3_STUDENT_INFORMATION_RESOURCE_EXPERIENCE.md docs/status/PHASE_6_17_FACULTY_EXPERIENCE_FOUNDATION.md docs/status/PHASE_6_2_STATUS.md docs/status/PHASE_6_3_STATUS.md docs/status/PHASE_6_6_STATUS.md docs/status/PHASE_6_7_STATUS.md docs/status/PHASE_6_9_STATUS.md scripts/validation/invoke_local_supabase.ps1 scripts/validation/provision_local_demo_users.ps1 supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql supabase/migrations/20260915000000_phase_6_13_organization_institution_tenancy.sql docs/status/PHASE_7_9_8_AUTHORITATIVE_BASELINE_RECONSTRUCTION.md docs/status/PHASE_7_9_9_USERS_PK_PROVENANCE_REVIEW.md docs/status/PHASE_7_9_10_USERS_SCHEMA_CONTRACT_REPAIR.md docs/status/PHASE_7_9_11_ADMIN_AUTH_SEED_PROVISIONING.md docs/status/PHASE_7_9_12_RECOVERY_SERIES_COMMIT_GATE.md docs/status/PHASE_7_9_13_PHASE_6_22_EVIDENCE_DISPOSITION.md
```

No staging or commit command was run in Phase 7.9.14.

## Explicit Exclusions

- `docs/evidence/complete_product_demo_phase_6_22.json` — preserved byte for
  byte as independent Phase 6.22 evidence. It remains at 35/39 with four failed
  checks and one conditional admin-role check missing from the run. Phase
  7.9.13 classified it `PRESERVE_AND_RECLASSIFY`; this phase did not fix or
  rerun those checks.
- `docs/status/PHASE_7_9_14_COMMIT_PREPARATION.md` — this preparation record is
  outside the Phase 7.9.4–7.9.13 commit scope.
- No other unrelated or unexplained user files were found among changed or
  untracked files.

## Migration Integrity

- Migration count: **16**
- Filename/timestamp ordering: **PASS**; no malformed filenames, duplicate
  timestamps, or duplicate migration names.
- Reconstructed baseline: **new reconstructed authoritative baseline**, not the
  recovered historical Phase 3.5 migration. Original Phase 3.5 remains
  **UNRECOVERED**. Trusted-export and baseline hashes match the values in the
  Phase 7.9.12 report.
- Admin-1: the three user foreign keys target `public.users(id)`; structural
  constraints remain. The connected demo seed was removed after its invalid
  Auth placeholder dependency was established; no foreign key was weakened.
- Phase 6.11, Phase 7.2, Phase 7.4: validated successfully in two fresh local
  resets documented in Phase 7.9.11/7.9.12.
- No migration filename or timestamp changed since validation. The two modified
  migration diffs match the reviewed 7.9.10/7.9.11 contract and seed repairs.
  No further SQL edits were made in Phases 7.9.12–7.9.14.

## Documentation Integrity

The Phase 7.9.4–7.9.13 reports were reviewed. Their historical failures remain
documented; later reports record the repairs and the fresh successful local
validation. The original Phase 3.5 migration remains **UNRECOVERED**. The
baseline is consistently described as **NEW RECONSTRUCTED AUTHORITATIVE
BASELINE**. The reviewed recovery reports state that the remote production-like
database was not modified. Phase 7.9.13 preserves the separate 6.22 evidence
and its failures.

## Security and Generated Artifacts

- Recovery-candidate secret scan: **NO_SENSITIVE_ARTIFACTS**. No high-confidence
  private key, bearer token, service-role key, API key, or credential pattern
  appeared in the 47 recovery paths. `.env` files are not among the candidates.
- Local `backend/.env`, `supabase/.temp`, virtualenv, dependencies, pytest
  cache, and frontend build output are ignored local state and are not in the
  manifest. Values were not printed.
- `backend/.pytest-tmp/`: absent.
- `supabase/.branches/`: absent.
- Existing backend logs are ignored and untracked; no log is in the manifest.
- Tracked configuration templates such as `.env.example` are unchanged and
  excluded.
- No binary, database dump, editor/OS metadata, debug-only file, or generated
  output is among the recovery candidates.

## Validation

No application, test, script, or migration source changed after the validation
results below. The intervening Phase 7.9.12–7.9.14 edits are documentation
only, so equivalent technical results are reused rather than rerunning the
expensive suites.

- Migration: **PASS** — 16 files; two fresh local resets; ledger; Phase 6.11,
  Phase 7.2, and Phase 7.4.
- Backend: **PASS** — 2,126 normal tests passed, 15 skipped, 6 warnings; two
  debug-only tests passed separately.
- Frontend: **PASS** — 50 files, 431 tests, 0 failures.
- TypeScript: **PASS** — `npx tsc --noEmit -p tsconfig.json`.
- Build: **PASS** — `npm run build`, 97 modules.
- `git diff --check`: **PASS**, rerun after this report was created.
- Staged diff: **empty**.
- Untracked text whitespace: checked as part of final diff gate.

## Remote Safety

```text
Remote Supabase modified: NO
Remote Auth modified: NO
Remote migrations applied: NO
Remote data modified: NO
```

No remote command or deployment was performed in Phase 7.9.14.

## Final Decision

```text
READY_FOR_COMMIT
```

The exact 47-file recovery scope is listed above. The Phase 6.22 evidence and
this Phase 7.9.14 preparation report are excluded. This phase did not stage or
commit files.
