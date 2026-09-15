# PHASE 6.2 — STUDENT DATABASE MODEL STATUS

## STATUS: COMPLETE — READY FOR REVIEW

Status date: 2026-09-12
Baseline: PHASE_6_1_LOCK.md (LOCKED, `75a794e28bd42c5d3f8008428a4457cd7e2818ce`)
No LOCK record is created by this step; locking requires separate review per
project change-control convention.

---

## 1. Phase Number / Name

Phase 6.2 — Student Database Model (Student Identity Extension)

## 2. Existing Student Model Discovered

The existing architecture (Phase Admin-1) already provided:

- **Table** `public.students` (no second table existed): `student_id` PK,
  `user_id` (UNIQUE, FK → `users.user_id` ON DELETE CASCADE),
  `institution_id` (FK → `institutions.institution_id` ON DELETE RESTRICT —
  the Phase 6.1 canonical tenant key), `student_number`,
  `program_id` FK, `academic_year_id` FK, `enrollment_date`,
  `expected_graduation_date`, academic `status`
  (active/inactive/graduated/withdrawn), `is_active` (soft-archive),
  `created_at`, `updated_at`.
- **Uniqueness as found**: `students_user_id_key` (global) and
  `students_student_number_key` (**global**).
- **Indexes**: `idx_students_user_id`, `idx_students_institution_id`,
  `idx_students_program_id`, `idx_students_academic_year_id`,
  `idx_students_is_active`.
- **Auth boundary**: authentication is fully delegated to **Supabase Auth**
  (GoTrue) — JWT verified via `backend/app/core/security.py`
  (`verify_jwt`, `get_current_user`); the application user row is
  `public.users` (`auth_user_id` → `user_id`); the JWT user's tenant is
  resolved from their one-to-one `students.institution_id`
  (`backend/app/db/supabase.py get_user_by_auth_id`). **No plaintext or
  duplicate password storage existed** — none was added.
- **Account-level login email uniqueness** already owned by
  `public.users.email` (globally UNIQUE since the Phase 3 baseline) plus
  Supabase Auth.
- **Academic identity present**: program (`program_id` FK), academic year
  (`academic_year_id` FK). Department/batch/semester/section already exist as
  separate reference tables and are intentionally NOT duplicated on students
  (avoid speculative fields per phase boundary).
- **Existing CRUD**: repositories `backend/app/repositories/admin_academics.py`
  (read-oriented), services `backend/app/services/admin_academics.py`
  (`create/update/archive student`), admin API `backend/app/api/admin.py`,
  self-service API `backend/app/api/students.py`.

## 3. Existing vs Changed

| Capability | Existed | Added in 6.2 |
| --- | --- | --- |
| students table | ✔ | unchanged (extended additively) |
| institution_id tenant FK | ✔ | untouched |
| student_number | ✔ | uniqueness scope global → institution-scoped |
| email (institutional identity) | ✘ | ✔ `students.email` |
| register_number | ✘ | ✔ `students.register_number` |
| university_roll_number | ✘ | ✔ `students.university_roll_number` |
| approval lifecycle state | ✘ | ✔ `students.approval_status` |
| password / credential storage | ✘ | intentionally NOT added (Supabase Auth owns auth) |
| tenant_id | ✘ | intentionally NOT added (Phase 6.1 boundary) |

## 4. Database Changes

Single migration `supabase/migrations/20260912000000_phase_6_2_student_identity_model.sql`
(all on the EXISTING `public.students`; no other table touched):

- **Columns**: `email text NULL`, `register_number text NULL`,
  `university_roll_number text NULL`,
  `approval_status text DEFAULT 'pending' NOT NULL`.
- **CHECK constraints**: `students_email_check` (email must equal its
  trimmed lowercase form), `students_register_number_check`,
  `students_university_roll_number_check` (non-empty when present),
  `students_approval_status_check` (pending/approved/rejected).
- **Uniqueness (all institution-scoped)**:
  - `students_institution_id_student_number_key (institution_id, student_number)`
    — replaces the dropped GLOBAL `students_student_number_key`;
  - `students_institution_id_email_key (institution_id, email)`;
  - `students_institution_id_register_number_key (institution_id, register_number)`;
  - `students_institution_id_university_roll_number_key
    (institution_id, university_roll_number)`.
- **Indexes**: `idx_students_email`, `idx_students_register_number`,
  `idx_students_university_roll_number`,
  `idx_students_institution_approval (institution_id, approval_status)`
  (approval-queue lookup pattern).
- **Foreign keys**: none added/removed; `students_institution_id_fkey`
  preserved exactly.
- **Backfill**: existing 3 rows (admin-provisioned demo students)
  `approval_status` → `approved`; DB default stays `pending` for the future
  self-registration flow.
- **Comments**: documented on all four new columns.
- **Reversibility**: full inverse DDL documented in the migration's ROLLBACK
  section.

## 5. Identity Design (email / register number / roll number)

- All three are **nullable until Phase 6.5 provisioning** defines requiredness
  (existing rows legitimately have no values; imposing NOT NULL would have
  destroyed data or forced fabrication).
- Academic identifiers (register number, university roll number,
  student_number) are **unique WITHIN institution_id**, not globally —
  `College A register 1001` and `College B register 1001` coexist by design.
  Architectural justification: academic identifiers are assigned per
  institution; the migrated-from global `students_student_number_key`
  contradicted the documented product rule ("student_number is
  institution-assigned and unique across the institution" — Phase Admin-1
  header).
- `students.email` is the institutional student email identity
  (lowercase/trimmed, enforced by CHECK), unique per institution.
  Account-level login-email uniqueness stays with `public.users.email`
  (global UNIQUE) + Supabase Auth — deliberately NOT duplicated.
- Identifier resolution helpers added (additive, unconsumed until Phase 6.5):
  `get_student_by_email`, `get_student_by_register_number`,
  `get_student_by_university_roll_number`, `resolve_student_by_identifier` —
  all REQUIRE `institution_id`; an identifier alone never resolves a student
  (tenant boundary preserved).

## 6. Tenant Relationship

`institutions.institution_id → students.institution_id` (pre-existing FK)
remains the sole tenant relationship. The migration never references a
`tenant_id` (verified by test). Existing projections (`STUDENT_COLUMNS`) are
unchanged so live endpoints respond byte-identically; the new
`STUDENT_IDENTITY_COLUMNS` identity projection always selects
`institution_id` first so resolved rows carry their tenant for future
authorization.

## 7. Account State Representation

- **Approval lifecycle** (`approval_status`): `pending` → `approved` |
  `rejected` — represents Registration → Pending → Approval → Approved →
  Login. DB default `pending` matches the future self-registration flow;
  the admin API's `StudentCreate.approval_status` defaults to `approved`
  (admin provisioning is the approving action; self-registration in a later
  phase will explicitly insert `pending`).
- **Existing fields reused, not duplicated**: academic `status`
  (active/inactive/graduated/withdrawn) and `is_active` (soft-archive)
  remain the academic-state/archive representation
  (`archive_student` untouched). No overlapping status field was invented.

## 8. Existing Data (pre-migration, verified read-only against the remote DB)

- 3 student rows (STU2026001-003), all institution `...0001` (GIT),
  status `active`, `is_active` true.
- Zero `(institution_id, student_number)` duplicate pairs, zero global
  student_number duplicates, zero `users.email` duplicates — the constraint
  changes are collision-free. No record deleted, no identity value modified;
  the only existing-row change is the documented approval backfill.

## 9. Migration Status

- **Migration pushed and applied**: `supabase db push` completed against the
  linked project `rjnfmjcvkfotneswpygr`.
- **Synchronized**: `supabase migration list` shows `20260912000000` present in
  BOTH the Local and Remote columns.
- **Live schema verified** during final verification (Supabase Management API +
  service-role client):
  - Columns `email`, `register_number`, `university_roll_number`,
    `approval_status` present on the live `students` table.
  - ALL Phase 6.2 constraints present, including the 4 institution-scoped
    UNIQUE keys ({institution_id, email | register_number |
    university_roll_number | student_number}); the old GLOBAL
    `students_student_number_key` is **gone**; `students_institution_id_fkey`
    intact; CHECK constraints present.
  - Indexes present: `idx_students_email`, `idx_students_register_number`,
    `idx_students_university_roll_number`,
    `idx_students_institution_approval`.
  - 3 existing student rows all `approval_status='approved'` (backfill OK).

## 10. Tests

- **New suite** `backend/tests/test_student_model_phase_6_2.py` — 38 passed +
  2 skipped (opt-in physical live-DB validation, following the
  `test_physical_validation_phase_4_4.py` convention). Covers: migration
  static validation (columns, institution-scoped uniqueness, CHECKs,
  approval lifecycle, backward-compatible projections, tenant-only scoping);
  institution-scoped identity resolution (email/register/roll; same identifier
  across institutions; normalization; institution filter applied to queries);
  service contracts (valid student creation, institution required, approval
  validation + defaults, identifier normalization); physical live-column and
  backfill verification.
- **Physical tests executed against live DB during final verification**:
  `test_physical_migrated_table_has_phase62_columns` PASS and
  `test_physical_existing_students_backfilled_approved` PASS (run directly,
  bypassing the opt-in skip, per the final-verification task). They report as
  skipped under the default `pytest` run (project convention).
- **Full backend suite**: `629 passed, 5 skipped, 0 failed`
  (5 skipped = 3 pre-existing Phase 4.4 physical + 2 new Phase 6.2 physical).
- **All existing student tests pass** (test_students_api,
  test_student_data_service, test_admin_academics_repository,
  test_admin_academics_service, test_admin_api, test_admin_schemas,
  test_tenant_isolation, test_auth).

## 11. Backward Compatibility

- No endpoint, response shape, or existing projection changed;
  `STUDENT_COLUMNS` is byte-identical to the pre-6.2 value (test-enforced).
- `create_student` now always inserts `approval_status` and
  `create/update_student` accept the identity fields — these require the applied
  migration (see §9); the code+migration coupling is consistent with every
  prior phase.
- Phase 6.1 tenant isolation: untouched and test-verified
  (`test_tenant_isolation.py` passes; migration never touches
  `students_institution_id_fkey`).

## 12. Security

No authorization/RLS implemented (later phase). The established security
architecture is preserved: Student → `institution_id` → Tenant; identity
resolution always requires the tenant context; the model adds no credential
storage, weakening the existing boundary in no way.

## 13. Out of Scope (NOT implemented — later Phase 6 phases)

Student registration workflow; admin/staff approval workflow endpoints;
student login (any identifier); password/email/register-number/roll-number
login logic; attendance; test/exam results; personalized or student-specific
chatbot context; new RBAC; RLS policies; approval-queue admin endpoints;
frontend changes. Only the database representation + additive, unconsumed
lookup helpers exist.

## 14. Known Limitations / Remaining Risks

- Identity columns are nullable by design; identifier uniqueness for NULLs is
  repeatable (Postgres semantics) — Phase 6.5 must enforce requiredness for
  login-eligible students.
- The institutional `email` namespace is independent of `public.users.email`;
  Phase 6.5 must define their binding policy (same value recommended).
- The global→institution-scoped `student_number` change assumes the product
  permits identical student_numbers across institutions (per the Phase Admin-1
  documented rule); if the product later decides global uniqueness, the
  constraint must be re-scoped deliberately.
- Approval state is enforced only by CHECK constraint; gating login on
  `approval_status='approved'` is Phase 6.5 behavior.

# PHASE 6.2 — COMPLETE AND LOCKED ✅
(lock record: `PHASE_6_2_LOCK.md`)


