# Phase 6.8 — Lock Record

**Phase:** 6.8  
**Subject:** Test / Exam Results  
**Lock date:** 2026-09-13  
**Precedence:** Phase 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7 are all formally locked before this lock step.

---

## 1. Objective

Phase 6.8 delivers secure Test / Exam Results functionality for the College AI Chatbot backend.

Phase 6.8 covers:

- test/exam/assessment result data
- student-specific results
- marks/scores
- maximum marks
- grade/result information where implemented
- academic context
- institution/tenant isolation
- student self-service result access
- authorized administrative result management
- validation
- duplicate protection
- auditability
- database integrity protections

---

## 2. Scope Status

**PHASE 6.8 — LOCKED.**  
**Phase 6.9 and later — NOT implemented.** No Phase 6.9+ functionality exists in this repository as of this lock.

No Phase 6.9+ functionality has been implemented as part of this lock.

---

## 3. Existing Result Schema Reused

Before implementation, the existing academic and result schema was inspected. The implementation reused existing structures wherever possible.

**Existing structures reused:**

- students — canonical student anchor with student_id, institution_id, and program_id relationships
- test_results — existing per-test/exam result table reused and hardened; no new result table was created
- student_results — existing per-student consolidated result table reused and hardened; no new result table was created
- student_result_items — existing per-course grade rows reused and hardened
- institutions — canonical tenant/institution table
- academic_years — academic year with institution_id as a strong tenant anchor
- semesters — semester with relationship to academic year
- courses to departments to institutions — academic chain used for tenant validation
- course_offerings and sections — academic context where applicable
- programs to departments to institutions — program academic chain where applicable
- admin_audit_log / record_admin_action — existing audit mechanism reused

**Model decision:**

The Phase 6.8 implementation reused the existing test_results and student_results tables and extended them with stronger integrity protections rather than creating a new result model.
---

## 4. Final Result Model

**test_results** (per-test/exam/per-assessment scores) — existing table hardened:

- scored_marks CHECK: must not exceed max_marks (test_results_score_marks_check)
- percentage CHECK: 0..100 (test_results_percentage_check), derived app-side from scored_marks / max_marks
- institution_id column added, server-derived from students.institution_id via trg_test_results_tenant_guard
- institution_id FK to institutions (test_results_institution_id_fkey)
- ownership fields (student_id, course_id, academic_year_id, semester_id) immutable on UPDATE
- section_id may be corrected but revalidated on every write
- updated_at refreshed by guard trigger on UPDATE

**student_results** (per-semester consolidated summaries) — existing table hardened:

- total_credits_earned CHECK: must not exceed total_credits_max (student_results_credits_earned_max_check)
- institution_id column added, server-derived from students.institution_id via trg_student_results_tenant_guard
- institution_id FK to institutions (student_results_institution_id_fkey)
- ownership fields (student_id, academic_year_id, semester_id, program_id) immutable on UPDATE
- updated_at refreshed by guard trigger on UPDATE

---

## 5. Student Relationship

Student identity and ownership are resolved through the existing chain:

public.users to students.user_id to students.student_id

Student self-service identity is derived from the authenticated user/JWT.

Explicitly:

- students cannot select another student as their identity
- student result reads are limited to the authenticated student own results
- missing student profiles fail safely
- ownership cannot be overridden through request parameters

No client-supplied student_id is trusted for determining whose results are returned.

---

## 6. Institution / Tenant Isolation

students.institution_id remains the canonical tenant/institution key.

Documented protections:

- institution-bound administrative access
- cross-tenant protection
- server-side tenant resolution
- academic-context tenant validation
- database-level protection where implemented
- platform admin behavior according to the already locked Phase 6.4/6.6 policy

No new tenant_id was introduced.

Phase 6.8 hardened the result tables by storing institution_id on the result rows themselves, derived from the canonical student/institution relationship.

Database-level tenant hardening:

- test_results.institution_id — column added, FK to institutions, value always equals students.institution_id
- student_results.institution_id — column added, FK to institutions, value always equals students.institution_id
- trg_test_results_tenant_guard — BEFORE INSERT OR UPDATE trigger on test_results
- trg_student_results_tenant_guard — BEFORE INSERT OR UPDATE trigger on student_results

---

## 7. Academic Context

Results are tied to the existing academic hierarchy: student to section to offering to course to department, plus academic year and semester.

Inconsistent or cross-institution academic relationships fail closed.

Database-level academic-context validation (both triggers):

- academic year must exist and belong to the student institution
- semester must belong to the academic year
- course must belong to the student institution (courses to departments to institutions)
- program must belong to the student institution (programs to departments to institutions)
- when a section is attached, the section offering must match the row course_id / academic_year_id / semester_id and belong to the student institution
---

## 8. Score / Mark Validation

Implemented and verified validation rules:

- negative scores are rejected
- maximum marks must be positive
- score greater than maximum marks is rejected
- numeric validation is enforced server-side
- grade validation is applied where applicable; blank/empty grades are normalized
- decimal handling is consistent with the chosen schema
- database-level CHECK constraints provide a second defense layer

Database-level CHECK constraints:

- test_results_score_marks_check — scored_marks must not exceed max_marks
- test_results_percentage_check — percentage must be between 0 and 100
- student_results_credits_earned_max_check — total_credits_earned must not exceed total_credits_max

Score validation is enforced at multiple layers, not only in the frontend.

---

## 9. Duplicate Protection

Existing unique constraints (from the locked Phase Admin-1 migration, not modified):

- test_results_student_course_test_sem_key — UNIQUE(student_id, course_id, test_name, academic_year_id, semester_id)
- student_results_student_sem_ay_prog_key — UNIQUE(student_id, academic_year_id, semester_id, program_id)

---

## 10. API Contracts

**Administrative (admin-only mutation):**

- POST /api/v1/admin/test-results — create a test result
- POST /api/v1/admin/results — create a result summary
- GET /api/v1/admin/test-results/{id} — read a test result
- GET /api/v1/admin/results/{id} — read a result summary
- PATCH /api/v1/admin/test-results/{id} — update a test result
- PATCH /api/v1/admin/results/{id} — update a result summary
- DELETE /api/v1/admin/test-results/{id} — delete a test result
- DELETE /api/v1/admin/results/{id} — delete a result summary

**Student self-service (strictly scoped to JWT-derived profile):**

- GET /api/v1/students/me/results — list own published result summaries
- GET /api/v1/students/me/results/{result_id} — get one own published result summary with items
- GET /api/v1/students/me/test-results — list own published test scores

All admin mutation endpoints require authentication and admin role; staff/faculty/student roles receive 403; unauthenticated requests receive 401.

Student self-service endpoints return 404 for foreign or unpublished results (no existence leak).
---

## 11. RBAC

- Admin role required for all result mutations (create, update, delete)
- Staff/faculty roles receive 403 on mutation endpoints
- Student role receives 403 on mutation endpoints
- Unauthenticated requests receive 401
- Platform admins (no tenant) retain global authority consistent with locked Phase 6.4/6.6 policy
- Institution-bound admins are scoped to their tenant

---

## 12. Student Self-Service

- GET /api/v1/students/me/results — returns only the authenticated student own published result summaries
- GET /api/v1/students/me/results/{result_id} — returns one published result summary with per-course grade rows, strictly scoped to the JWT-derived student profile
- GET /api/v1/students/me/test-results — returns only the authenticated student own published test scores
- Foreign results and unpublished results return 404 (RESULT_NOT_FOUND) — indistinguishable from missing results
- A missing student profile returns 404 (STUDENT_PROFILE_NOT_FOUND)
- Tenant guard: a stale/moved profile cannot smuggle a foreign tenant result past the tenant assertion (403 TENANT_MISMATCH)

---

## 13. Security Protections

- Server-side tenant resolution from the authenticated user JWT
- Institution-bound admin scoping
- Cross-tenant creation rejected before academic lookup
- Database-level guard triggers as defense-in-depth
- institution_id on result rows never trusted from client input
- Ownership fields immutable on UPDATE at the database level
- Academic-context chain validated on every write
- CHECK constraints on scores, percentages, and credits
- UNIQUE constraints prevent duplicate results
- Request schema strictness (extra=forbid, malformed UUIDs rejected with 422)

---

## 14. Audit Behavior

Privileged result mutations are recorded via the existing record_admin_action / admin_audit_log mechanism.
---

## 15. Migration

**Migration file:** supabase/migrations/20260913010000_phase_6_8_results.sql

The migration is purely additive hardening of the existing test_results and student_results tables:

1. student_results.institution_id column added, backfilled from students.institution_id, FK to institutions, NOT NULL
2. test_results.institution_id column added, backfilled from students.institution_id, FK to institutions, NOT NULL
3. test_results_score_marks_check CHECK constraint (scored_marks <= max_marks)
4. student_results_credits_earned_max_check CHECK constraint (total_credits_earned <= total_credits_max)
5. trg_test_results_tenant_guard trigger function + trigger (BEFORE INSERT OR UPDATE)
6. trg_student_results_tenant_guard trigger function + trigger (BEFORE INSERT OR UPDATE)
7. Indexes: idx_test_results_institution_id, idx_test_results_student_conducted, idx_test_results_ay_semester, idx_student_results_institution_id, idx_student_results_student_issued, idx_student_results_ay_semester
8. Column comments on institution_id columns

No locked Phase 6.1-6.7 migration is modified. No new tables are created.
**Migration fix note:** The original migration contained a PL/pgSQL syntax error where NEW and OLD record variables were incorrectly double-quoted as SQL identifiers. This caused the initial remote db push to fail with: ERROR: NEW.institution_id is not a known variable (SQLSTATE 42601). The migration was corrected by removing the double-quotes around NEW and OLD in both trigger functions, and the corrected migration was successfully pushed to the remote database.



**Migration fix note:** The original migration contained a PL/pgSQL syntax error where NEW and OLD record variables were incorrectly double-quoted as SQL identifiers. This caused the initial remote db push to fail with: ERROR: NEW.institution_id is not a known variable (SQLSTATE 42601). The migration was corrected by removing the double-quotes around NEW and OLD in both trigger functions, and the corrected migration was successfully pushed to the remote database.
---

## 16. Local Migration Verification

**Local migration status: Applied.**

`
Local            | Remote           | Time (UTC)
------------------|------------------|-----------------------
20260913010000 | 20260913010000 | 2026-09-13 01:00:00
`

The migration was applied locally via supabase db push and is present in the local database.

---

## 17. Remote Migration Verification

**Remote migration status: Applied.**

`
Local            | Remote           | Time (UTC)
------------------|------------------|-----------------------
20260913010000 | 20260913010000 | 2026-09-13 01:00:00
`

The migration was pushed to the remote database via supabase db push --yes and confirmed applied via supabase migration list.

---

## 18. Remote Schema Verification

Remote schema verified via supabase db query --linked against the live remote database.

**Result tables intact:**

- public.test_results -- present
- public.student_results -- present

**institution_id additions:**

- test_results.institution_id -- uuid column present
- student_results.institution_id -- uuid column present

**Foreign keys verified:**

- test_results_institution_id_fkey -- FK to institutions on test_results.institution_id
- student_results_institution_id_fkey -- FK to institutions on student_results.institution_id
- All existing academic-context FKs intact (academic_year_id, course_id, section_id, semester_id, student_id, program_id)

**CHECK constraints verified:**

- test_results_score_marks_check -- present on test_results
- test_results_percentage_check -- present on test_results
- student_results_credits_earned_max_check -- present on student_results

**UNIQUE constraints verified:**

- test_results_student_course_test_sem_key -- intact
- student_results_student_sem_ay_prog_key -- intact

**Indexes verified:**

- idx_test_results_institution_id -- present
- idx_test_results_student_conducted -- present
- idx_test_results_ay_semester -- present
- idx_student_results_institution_id -- present
- idx_student_results_student_issued -- present
- idx_student_results_ay_semester -- present

**Trigger protections verified:**

- trg_test_results_tenant_guard -- BEFORE INSERT OR UPDATE on test_results -- present
- trg_student_results_tenant_guard -- BEFORE INSERT OR UPDATE on student_results -- present

**Compatibility with existing seed data:**

- Existing test_results and student_results rows were backfilled with institution_id from the corresponding students record during migration
- All existing FK relationships remain valid
- No existing data was modified or deleted

---

## 19. Physical Validation

Physical validation tests (TestResultsPhysicalValidationPhase68) are present in backend/tests/test_results_phase_6_8.py with a skip marker (@pytest.mark.skipif(True, reason=...)) following the project opt-in convention (mirrors test_physical_validation_phase_4_4.py).

The skip marker was not removed. Physical validation was not run as part of this lock because the environment skip conditions remain in effect.

---

## 21. Full Regression Baseline

**Command:** cd backend && python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py -q

**Result:** 865 passed, 8 skipped, 0 failed

---

## 20. Focused Test Baseline

**File:** backend/tests/test_results_phase_6_8.py

**Result:** 46 passed, 3 skipped, 0 failed

The 3 skipped tests are the physical validation tests (TestResultsPhysicalValidationPhase68) which remain skip-by-default per project convention.

**Note on migration test fix:** The test test_migration_defines_guard_triggers_and_ownership_immutability originally asserted the buggy quoted NEW/OLD syntax. After the migration was corrected, the test assertion was updated to assert the correct unquoted NEW record-variable syntax (PL/pgSQL record variable, not a quoted identifier). No test logic was altered -- only the expected string was corrected to match the fixed migration.

---

## 22. Exact File Set

**Production code (unchanged from Phase 6.8 implementation, except migration correction):**

- supabase/migrations/20260913010000_phase_6_8_results.sql -- migration (corrected for PL/pgSQL syntax)
- backend/app/api/students.py -- student self-service endpoints
- backend/app/services/student_data.py -- student self-service data access
- backend/app/services/results.py -- result service layer
- backend/app/services/admin_academics.py -- admin academic services
- backend/app/repositories/results.py -- result repositories
- backend/app/repositories/admin_academics.py -- admin academic repositories
- backend/app/core/security.py -- assert_tenant_object tenant guard
- backend/app/core/errors.py -- error definitions
- backend/app/main.py -- FastAPI application

**Test code (unchanged except for migration assertion correction):**

- backend/tests/test_results_phase_6_8.py -- Phase 6.8 tests (assertion corrected to match fixed migration)

**Lock documents:**

- PHASE_6_8_LOCK.md -- this file

**No other files were modified.**

---

## 24. Phase Boundary

**PHASE 6.8 -- LOCKED**

Test / Exam Results functionality, including its data model, validation, authorization, tenant isolation, student self-service access, database integrity protections, audit behavior, and verified test baseline are formally locked.

No Phase 6.9+ functionality has been implemented as part of this lock.

---

*Previous Phase 6.1-6.7 lock files are untouched.*
---

## 23. Known Limitations

- Physical validation tests are skip-by-default and were not run during this lock
- percentage is derived by the application layer, not the database; the database CHECK constraint guards the range but does not compute the value
- The guard triggers are a database-level safety net; application-layer authorization (RBAC + tenant) remains the primary access control
- The migration fix (removing double-quotes around NEW/OLD) corrected a PL/pgSQL syntax error; the semantic behavior of the triggers is unchanged

