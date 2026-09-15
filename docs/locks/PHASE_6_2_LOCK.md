# PHASE 6.2 — STUDENT DATABASE MODEL LOCK

## STATUS: LOCKED

Lock date: 2026-09-12
Locked at final verification completion. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.2

## 2. Phase Name

Phase 6.2 — Student Database Model (Student Identity Extension)

## 3. Final Architecture

Phase 6.2 extends the EXISTING `public.students` table (Phase Admin-1) with the
identity fields and registration-approval lifecycle required by later Phase 6
phases. It does not create a second student table, nor replace `institution_id`
(a `tenant_id` is intentionally NOT introduced — Phase 6.1 boundary). The final
student model:

- Identity: `email` (institutional, lowercase/trimmed), `register_number`,
  `university_roll_number`.
- Tenant: `institution_id` FK → `institutions.institution_id` (the canonical
  Phase 6.1 tenant key, untouched).
- Account/approval state: `approval_status` (`pending | approved | rejected`)
  independent of the pre-existing academic `status` and `is_active` fields.
- Authentication boundary: no password/credential storage added — auth remains
  fully delegated to Supabase Auth (GoTrue).

## 4. Existing vs Newly Added Fields

| Field | Pre-existing | Added in 6.2 |
| --- | --- | --- |
| student_id (PK) | ✔ | — |
| user_id (UNIQUE, FK→users) | ✔ | — |
| institution_id (FK→institutions) | ✔ (tenant key) | untouched |
| student_number | ✔ (global UNIQUE) | scope → (institution_id, student_number) |
| program_id / academic_year_id FKs | ✔ | untouched |
| enrollment_date / expected_graduation_date | ✔ | untouched |
| status (academic) / is_active (soft-archive) | ✔ | untouched |
| email | — | ✔ |
| register_number | — | ✔ |
| university_roll_number | — | ✔ |
| approval_status | — | ✔ (DEFAULT 'pending' NOT NULL) |
| tenant_id | — | NOT added (locked-out) |
| password / credentials | — | NOT added (Supabase Auth owns auth) |

## 5. `institution_id` Tenant Relationship

```
institutions
      │
      │ institution_id (FK, ON DELETE RESTRICT)
      ↓
   students
```

`students.institution_id` is the sole tenant key. Every student belongs to
exactly one institution; every identity lookup helper in the repositories is
ALWAYS institution-scoped (an identifier value alone never resolves a student —
resolution requires the `institution_id` tenant context). This preserves the
Phase 6.1 security architecture: Student → `institution_id` → Tenant. No RLS
was added in this phase (later phase).

## 6. Identity Uniqueness Strategy

All academic identifiers are **unique within `institution_id`**, not globally:

- `UNIQUE(institution_id, email)`
- `UNIQUE(institution_id, register_number)`
- `UNIQUE(institution_id, university_roll_number)`
- `UNIQUE(institution_id, student_number)` (replaces the global
  `students_student_number_key`)

Rationale: academic identifiers are institution-assigned, so identical values
may legitimately coexist across colleges (College A register 1001, College B
register 1001). Account-level login-email uniqueness remains owned by
`public.users.email` (globally UNIQUE) + Supabase Auth — `students.email` is the
institutional identity namespace and does not duplicate that. Identity columns
are NULLABLE (provisioned in Phase 6.5); the CHECK constraints reject empty /
whitespace-only values and non-lowercase emails.

## 7. Approval-State Representation

`students.approval_status` (`pending | approved | rejected`) models the
registration lifecycle:

```
Registration → pending → Admin/Staff Approval → approved → Student Login
```

- Column default is `'pending'` (future self-registration flow).
- The three Phase Admin-1 seeded students were backfilled to `'approved'`
  (they were admin-provisioned, i.e. already approved by definition);
  the column default remains `'pending'`.
- DB CHECK constraint `students_approval_status_check` enforces the enum.
- `approval_status` is independent of the academic `status` and `is_active`
  fields — no overlapping status columns were created.

The registration / approval workflows themselves are NOT implemented (Phase 6.3+).

## 8. Migration ID

`20260912000000_phase_6_2_student_identity_model.sql`

## 9. Migration Application Status

- Pushed to the remote project: **YES**.
- `supabase migration list` → `20260912000000` present in BOTH the Local and
  Remote columns → **synchronized**.
- Live schema verified via the Supabase Management API + service-role client.
- Reversible: full ROLLBACK DDL is documented in the migration file.

## 10. Physical Test Results

The two physical (live-DB) tests, skipped by default per project
convention (`@pytest.mark.skip`, same pattern as
`test_physical_validation_phase_4_4.py`), were executed directly against the
live database during final verification:

- `test_physical_migrated_table_has_phase62_columns` — **PASS** (columns
  `email`, `register_number`, `university_roll_number`, `approval_status`
  present on the live DB).
- `test_physical_existing_students_backfilled_approved` — **PASS** (3 seeded
  students all `approval_status='approved'`).

Under the default `pytest` run these 2 report as **skipped** (opt-in physical).

## 11. Full Test-Suite Results

- **Phase 6.2 suite** (`backend/tests/test_student_model_phase_6_2.py`):
  38 passed, 2 skipped (opt-in physical), 0 failed.
- **Full backend suite** (`pytest tests/`):
  **629 passed, 5 skipped, 0 failed**
  (prior report was 620 passed, 5 skipped, 0 failed; the +9 is the Phase 6.2
  suite growth from 29 to 38 passing tests; the 5 skipped = 3 pre-existing
  Phase 4.4 physical + 2 new Phase 6.2 physical).
- All existing student tests continue to pass
  (students_api, student_data_service, admin_academics_*,
  admin_api, admin_schemas, auth, tenant_isolation, ingestion).

## 12. Git Verification

- Git status confirms Phase 6.2 touched ONLY:
  - `supabase/migrations/20260912000000_phase_6_2_student_identity_model.sql` (new)
  - `backend/app/repositories/admin_academics.py` (additive identity helpers)
  - `backend/app/services/admin_academics.py` (identity fields, approval
    validation, normalization)
  - `backend/tests/test_student_model_phase_6_2.py` (new)
  - `PHASE_6_2_STATUS.md` + `PHASE_6_2_LOCK.md` (docs)
- The other files present in `git status` (admin.py, ingestion.py, students.py,
  security.py, supabase.py, main.py, test_auth.py, test_ingestion.py,
  PHASE_6_1_LOCK.md, test_tenant_isolation.py) are **pre-existing Phase 6.1
  work that was uncommitted before Phase 6.2 began** — they are NOT Phase 6.2
  changes and were not modified by this phase.
- No unrelated production files changed by Phase 6.2.

## 13. Known Limitations / Remaining Risks

- Identity columns are nullable by design (repeatable NULLs within an
  institution under Postgres unique-constraint semantics) — Phase 6.5 must
  enforce requiredness for login-eligible students.
- `students.email` (institutional namespace) is independent of
  `public.users.email`; Phase 6.5 must define their binding policy (same value
  recommended).
- The global→institution-scoped `student_number` change assumes the product
  permits identical student_numbers across institutions (per the Phase Admin-1
  documented rule); if the product later requires global uniqueness it must be
  re-scoped deliberately.
- Approval gating (`approval_status='approved'` → login allowed) is Phase 6.5
  behavior; only the CHECK constraint enforces the enum in this phase.

## 14. Explicit Phase 6.3+ Exclusions (NOT implemented)

Student registration workflow; admin/staff approval workflow endpoints;
student login (email / register-number / university-roll-number); password
handling; attendance; test/exam results; personalized or student-specific
chatbot context; new RBAC system; RLS policies; approval-queue admin endpoints;
frontend changes. Only the Student database model and additive, unconsumed
identity-resolution foundations exist.

---

# PHASE 6.2 — LOCKED ✅