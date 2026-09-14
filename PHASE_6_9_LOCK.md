# PHASE 6.9 — STUDENT-SPECIFIC DATA ACCESS LOCK

## STATUS: LOCKED

Lock date: 2026-09-13
Locked at formal review approval. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.9

## 2. Phase Name

Phase 6.9 — Student-Specific Data Access

## 3. Locked Objective

Phase 6.9 establishes secure student-specific data access. The locked objective includes:

- canonical authenticated student identity resolution
- student context resolution
- student eligibility
- own profile access
- own attendance access
- own result access
- own test-result access
- cross-student isolation
- cross-tenant isolation
- identifier security
- RBAC boundaries
- security validation
- preservation of Phase 6.7 and Phase 6.8 protections

## 4. Canonical Identity Chain

The exact canonical identity chain locked by Phase 6.9:

```text
JWT auth_user_id
        -> public.users
        -> students.user_id
        -> students.student_id
        -> students.institution_id
```

The student identity is derived server-side from the authenticated JWT.

Client-supplied:

- student_id
- user_id
- auth_user_id
- institution_id

are NOT trusted to determine the authenticated student's identity for `/students/me/*` access.

## 5. Student Context Service

File: `backend/app/services/student_context.py`

Actual responsibilities:

- `get_student_context(current_user)` — resolves the canonical student context from the authenticated JWT (public.users -> students); raises 404 `STUDENT_PROFILE_NOT_FOUND` when no profile is linked; returns only whitelisted safe fields.
- `_assert_student_eligible(student, db)` — verifies `approval_status == "approved"`, `is_active == True`, and (when the student has an institution) institution active via `_assert_institution_active`.
- `CONTEXT_FIELDS` — the whitelist of safe context fields exposed by the context dict.
- `assert_student_context_tenant(current_user, student_context)` — defense-in-depth assertion that the context institution matches the current user's resolved tenant (403 `TENANT_MISMATCH` on mismatch).

Actual safe context fields exposed (`CONTEXT_FIELDS`):

| Field | Source |
|---|---|
| student_id | students.student_id (PK) |
| user_id | students.user_id (FK to users.user_id) |
| auth_user_id | JWT sub claim |
| institution_id | students.institution_id (tenant key) |
| student_number | students.student_number |
| email | students.email |
| approval_status | students.approval_status |
| is_active | students.is_active |
| status | students.status |

Sensitive authentication credentials, passwords, and tokens are NOT included in the student context.

## 6. Student Eligibility

Actual eligibility requirements implemented:

- student profile existence (a `students` row linked by `user_id`)
- `approval_status == "approved"`
- `is_active == True`
- institution active state (when the student has an institution)

Actual error behavior for ineligible/missing students:

- No student profile -> 404 `STUDENT_PROFILE_NOT_FOUND`
- `approval_status != "approved"` -> 403 `STUDENT_NOT_APPROVED`
- `is_active == False` -> 403 `STUDENT_INACTIVE`
- institution inactive -> 401 `INVALID_CREDENTIALS` (`SafeAuthFailure` raised by `_assert_institution_active`)

No new eligibility states were invented.

## 7. Student-Specific Data

Datasets covered by Phase 6.9:

- student profile
- attendance
- test results
- student results
- result items where applicable

Access is constrained to the authenticated student's canonical `student_id`. Phase 6.9 does NOT make all college academic data student-accessible.

## 8. Attendance Access (Phase 6.7 preserved)

Phase 6.7 attendance access behavior preserved through Phase 6.9:

- authenticated student identity
- own attendance only
- foreign student protection
- tenant protection
- no client-controlled student identity

Attendance was NOT redesigned.

## 9. Results Access (Phase 6.8 preserved)

Phase 6.8 result access behavior preserved through Phase 6.9:

- own results only
- own test results only
- result-item ownership where applicable
- published-result behavior (only `status == "published"` is returned; foreign / unpublished / missing results all surface the same 404 `RESULT_NOT_FOUND`, so no enumeration or information leak)
- foreign-result protection
- tenant protection

Results were NOT redesigned.

## 10. Cross-Student Isolation

A student cannot use:

- another student's UUID
- another student's register number
- another student's university roll number
- another student's email
- another student's user ID
- another student's institution ID
- manipulated query parameters
- manipulated path parameters
- request-body identity fields

to access another student's data. All `/me/*` queries use the server-derived canonical `student_id`; client-supplied identity fields are ignored.

Actual safe error semantics:

- Missing / foreign / unpublished result -> 404 `RESULT_NOT_FOUND` (indistinguishable by design)
- Malformed UUID path parameter -> 422 (FastAPI path validation)
- No student profile -> 404 `STUDENT_PROFILE_NOT_FOUND`

## 11. Cross-Tenant Isolation

`students.institution_id` remains the canonical tenant key.

- student context tenant — derived from the student database row
- tenant assertions — `assert_tenant_object` on profile and result-detail endpoints; `assert_student_context_tenant` for defense-in-depth
- cross-institution rejection — 403 `TENANT_MISMATCH`
- defense-in-depth behavior — the context institution must match the current user's resolved tenant

No `tenant_id` was introduced. No new tenant architecture was described.

## 12. Identifier Security

Relationship to the Phase 6.2/6.5 identity model:

- email globally unique
- register_number institution-scoped
- university_roll_number institution-scoped
- academic identifiers are NOT authorization credentials after authentication

Explicit statement: Academic identifiers cannot replace JWT-derived student identity for `/students/me/*` access.

## 13. RBAC

Actual Phase 6.9 role behavior:

- **Student self-service** — approved, active students access only their own `/me/*` data; pending approval -> 403 `STUDENT_NOT_APPROVED`; inactive -> 403 `STUDENT_INACTIVE`; no linked profile -> 404 `STUDENT_PROFILE_NOT_FOUND`.
- **Admin behavior** — an admin without a linked student profile gets 404 `STUDENT_PROFILE_NOT_FOUND` on `/me/*`; admins have no student-data access through `/me/*`.
- **Staff behavior** — staff without a linked student profile get 404 `STUDENT_PROFILE_NOT_FOUND` on `/me/*`.
- **Faculty behavior** — faculty without a linked student profile get 404 `STUDENT_PROFILE_NOT_FOUND` on `/me/*`.
- **Platform-account behavior** — platform accounts without a linked student profile get 404 `STUDENT_PROFILE_NOT_FOUND` on `/me/*`.
- **Unauthenticated** — 401 `AUTH_REQUIRED`.

The existing RBAC framework was reused. Phase 6.9 does NOT create a new RBAC system.

## 14. API Contracts

Actual `/api/v1/students/me/*` endpoints affected or verified by Phase 6.9:

| Route | Method | Purpose | Identity source | Authorization | Ownership | Relevant error behavior |
|---|---|---|---|---|---|---|
| `/api/v1/students/me/profile` | GET | Own student profile | JWT `user_id` | Student + eligible | own `student_id`; `assert_tenant_object` | 404 no profile; 403 `TENANT_MISMATCH` |
| `/api/v1/students/me/results` | GET | Own published result summaries | JWT `user_id` | Student + eligible | own `student_id` | published only; 404 no profile |
| `/api/v1/students/me/results/{result_id}` | GET | One own published result with per-course items | JWT `user_id` | Student + eligible | own `student_id` + `assert_tenant_object` | 404 `RESULT_NOT_FOUND`; 403 `TENANT_MISMATCH` |
| `/api/v1/students/me/test-results` | GET | Own published test scores | JWT `user_id` | Student + eligible | own `student_id` | published only; 404 no profile |
| `/api/v1/students/me/attendance` | GET | Own attendance records | JWT `user_id` | Student + eligible | own `student_id` | 404 no profile |

No `student_id` / `user_id` / `auth_user_id` query parameter exists on any `/me/*` path in OpenAPI (asserted by `test_identity_params_never_trusted`).

## 15. Security Tests

Test suite: `backend/tests/test_student_specific_data_phase_6_9.py`

Actual test coverage (26 tests, 9 test groups):

- context resolution
- field whitelist
- profile isolation
- attendance isolation
- result isolation
- test-result isolation
- cross-student attacks
- cross-tenant attacks
- identity injection
- identifier substitution
- malformed IDs
- RBAC boundaries
- eligibility behavior
- preservation of Phase 6.7/6.8 contracts

## 16. Test Baseline

Final verified baseline:

Full backend:

```text
891 passed
8 skipped
0 failed
```

Canonical command:

```text
cd backend
python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py
```

Phase 6.9 focused suite (exact actual count):

```text
backend/tests/test_student_specific_data_phase_6_9.py
26 passed
0 failed
```

Skipped tests explained: the 8 skipped tests are pre-existing opt-in live-database / real-DB checks that require explicit manual opt-in and valid credentials. None are Phase 6.9 tests; Phase 6.9 introduces no skips:

- 3 x `tests/test_attendance_phase_6_7.py` — live-database validation requires explicit manual opt-in
- 3 x `tests/test_results_phase_6_8.py` — live-database validation requires explicit manual opt-in
- 1 x `tests/test_student_model_phase_6_2.py` — real DB schema check requires explicit manual opt-in
- 1 x `tests/test_student_model_phase_6_2.py` — real DB seed check requires explicit manual opt-in

## 17. Database / Migration

"No new Phase 6.9 database migration was required."

Existing relationships were reused:

- students
- attendance
- results
- institution

No migration was created during the lock.

## 18. Security Architecture

Central Phase 6.9 invariant:

```text
AUTHENTICATED USER
        |
        v
CANONICAL STUDENT
        |
        v
AUTHORIZED INSTITUTION
        |
        v
ONLY THAT STUDENT'S DATA
```

Phase 6.9 does NOT permit:

```text
CLIENT-SUPPLIED STUDENT ID
        |
        v
DATA ACCESS
```

or:

```text
CLIENT-SUPPLIED INSTITUTION ID
        |
        v
AUTHORIZATION
```

## 19. File Set

Phase 6.9 files:

New:

```text
backend/app/services/student_context.py
backend/tests/test_student_specific_data_phase_6_9.py
backend/PHASE_6_9_STATUS.md
```

No other file was part of the final Phase 6.9 implementation. The pre-existing uncommitted Phase 6.8 reviewer changes in the working tree (`PHASE_6_8_LOCK.md`, `backend/tests/test_results_phase_6_8.py`, `supabase/migrations/20260913010000_phase_6_8_results.sql`, `backend/_measure_local.py`) are NOT Phase 6.9 changes and were not modified by the lock. The `/me/*` endpoint security already present in `backend/app/api/students.py` and `backend/app/services/student_data.py` (JWT-derived identity, `assert_tenant_object`, published-only filtering) is committed Phase 6.8 behavior and was not modified by Phase 6.9.

## 20. Known Limitations

Documented in `backend/PHASE_6_9_STATUS.md` and preserved unchanged:

1. No live database migration is required for Phase 6.9 (uses the existing schema).
2. The `student_context` service is a read-only resolver; Phase 6.9 does not add student profile mutation endpoints (no design for student self-edit of profile, status, or academic context).
3. The service relies on the Supabase client `students` table query; direct SQL access patterns are not tested in Phase 6.9.

These limitations are documented and were not solved during the lock step.

## 21. Phase Boundary

Phase 6.10 has NOT started. The lock explicitly excludes:

- personalized chatbot responses
- prompt personalization
- student data injection into prompts
- personalized RAG
- AI-generated student summaries
- AI recommendations
- student-specific chatbot memory
- AI context construction
- chatbot access to attendance/results

Those belong to Phase 6.10. Phase 6.9 does NOT implement any of them.

## 22. Lock Verification

Pre-lock checks performed:

- `git status --short` confirmed the working tree. Only the Phase 6.9 deliverables (`backend/app/services/student_context.py`, `backend/tests/test_student_specific_data_phase_6_9.py`, `backend/PHASE_6_9_STATUS.md`) are new; the pre-existing uncommitted Phase 6.8 reviewer changes were left untouched.
- Focused Phase 6.9 suite: 26 passed, 0 failed.
- Full backend regression via the canonical command: 891 passed, 8 skipped, 0 failed.
- No temporary or debug files remain; no secrets were added; no production code, tests, migrations, or configuration were modified during the lock.
- Post-lock verification (section 23 below) confirms the lock step added only this document.

---

## 23. Post-Lock Verification

After creation, the full `PHASE_6_9_LOCK.md` was re-read and verified:

- all claims match the implementation
- identity chain is correct
- eligibility rules are correct
- student data scope is correct
- attendance behavior is correct
- results behavior is correct
- tenant behavior is correct
- RBAC behavior is correct
- test numbers are correct (26 focused / 891 full / 8 skipped)
- file list is correct
- known limitations are preserved
- Phase 6.10 is explicitly excluded

---

## Official lock statement

> "PHASE 6.9 — LOCKED"

> "Student-specific data access, including canonical student identity resolution, eligibility enforcement, ownership isolation, tenant isolation, academic data access boundaries, identifier security, RBAC enforcement, and verified security tests are formally locked."

> "No Phase 6.10+ functionality has been implemented as part of this lock."



