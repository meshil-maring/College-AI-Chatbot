# Phase 6.9 - Student-Specific Data Access - Status

**Status:** Implementation complete. 26 focused tests passing. Full regression 891 passing / 8 skipped / 0 failing.

## 1. Goal

Implement and verify a secure student-specific data access layer that enforces the identity chain:

    JWT -> public.users -> students -> student_id + institution_id -> authorized academic data

Phase 6.9 builds on the Phase 6.8 result self-service endpoints (`/me/results`) by introducing a canonical `student_context` service that resolves the authenticated student's identity server-side from the JWT's `user_id` claim, enforces eligibility checks, and provides a whitelist of safe fields.

## 2. Identity chain

The canonical student context is resolved as follows:

1. **Supabase Auth JWT** provides `auth_user_id` (the `sub` claim) and `email`.
2. `get_current_user()` looks up `public.users` by `auth_user_id` and returns `user_id`, `auth_user_id`, `email`, `roles`, and `institution_id`.
3. `student_context.get_student_context(current_user)` resolves the student profile from `students` using `user_id` (from the JWT-derived `current_user`).
4. The student's `student_id` and `institution_id` are derived from the database row, **never** from client-supplied fields.

**Client-supplied identity fields (`student_id`, `user_id`, `institution_id`, `email`, `register_number`, `university_roll_number`) are never trusted.** The `/me/*` endpoints resolve all identity server-side from the JWT.

---

## 3. Student context service

**File:** `app/services/student_context.py` (new)

### 3.1 `get_student_context(current_user)`

Resolves the canonical student context from the authenticated JWT:

1. Extracts `user_id` and `auth_user_id` from `current_user` (the dict returned by `get_current_user()`).
2. Calls `academics_repo.get_student_by_user_id(db, str(user_id))` to look up the student profile.
3. If no profile exists -> raises `AppError(404, "STUDENT_PROFILE_NOT_FOUND")`.
4. Calls `_assert_student_eligible(student, db)` to verify eligibility.
5. Returns a dict containing only the whitelisted safe fields.

### 3.2 `_assert_student_eligible(student, db)`

Eligibility requires ALL of:
- `approval_status == "approved"` -> else 403 `STUDENT_NOT_APPROVED`
- `is_active == True` -> else 403 `STUDENT_INACTIVE`
- `institution.is_active == True` -> else 403 `STUDENT_NOT_APPROVED` (via `_assert_institution_active`)

### 3.3 `assert_student_context_tenant(current_user, student_context)`

Defense-in-depth: asserts the student context's `institution_id` matches the current user's resolved tenant (`current_user["institution_id"]`). Mismatches raise `TENANT_MISMATCH` (403).

---

## 4. Whitelisted context fields

Only the following safe fields are exposed in the context dict (`CONTEXT_FIELDS`):

| Field | Source |
|---|---|
| `student_id` | `students.student_id` (PK) |
| `user_id` | `students.user_id` (FK to `users.user_id`) |
| `auth_user_id` | JWT `sub` claim |
| `institution_id` | `students.institution_id` (tenant key) |
| `student_number` | `students.student_number` |
| `email` | `students.email` |
| `approval_status` | `students.approval_status` |
| `is_active` | `students.is_active` |
| `status` | `students.status` |

No passwords, tokens, or internal metadata are ever included.

---

## 5. API contracts

### Student self-service `/me/*` endpoints (unchanged, hardened)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/students/me/profile` | Own profile (tenant-guarded via `assert_tenant_object`) |
| `GET` | `/api/v1/students/me/results` | Own published result summaries |
| `GET` | `/api/v1/students/me/results/{result_id}` | One own published result with grade items (tenant-guarded) |
| `GET` | `/api/v1/students/me/test-results` | Own published test scores |
| `GET` | `/api/v1/students/me/attendance` | Own attendance records |

All endpoints resolve identity from `UUID(current_user["user_id"])` via `student_data.get_own_*` services. No `student_id` parameter exists in OpenAPI for any `/me/*` path.

---

## 6. RBAC

| Actor | Access `/students/me/*` self-service |
|---|---|
| **Student** (approved, active) | Own data only (profile, results, test-results, attendance) |
| **Student** (pending/approval) | 403 `STUDENT_NOT_APPROVED` |
| **Student** (inactive) | 403 `STUDENT_INACTIVE` |
| **Student** (no profile linked) | 404 `STUDENT_PROFILE_NOT_FOUND` |
| **Admin / Staff / Faculty** | 404 `STUDENT_PROFILE_NOT_FOUND` (no student profile linked) |
| **Unauthenticated** | 401 `AUTH_REQUIRED` |

Phase 6.9 does not change RBAC roles; it enforces that only eligible students can access self-service data.

---

## 7. Security protections

| Protection | Mechanism |
|---|---|
| No client-controlled identity | Identity resolved from JWT `user_id` via `students.user_id` |
| No client-controlled tenant | `institution_id` from student DB row; `assert_tenant_object` guard |
| No cross-student access | All `/me/*` queries use server-derived `student_id` |
| No result enumeration | Foreign/unpublished/missing results all -> 404 `RESULT_NOT_FOUND` |
| Cross-tenant blocked | `assert_tenant_object` + `assert_student_context_tenant` -> 403 `TENANT_MISMATCH` |
| Missing profile fails safely | 404 `STUDENT_PROFILE_NOT_FOUND` (never silent empty broadening) |
| Malformed IDs rejected | FastAPI UUID path param -> 422 |
| Unapproved/inactive students | 403 with specific error codes |

---

## 8. Student self-service behavior

- `get_own_profile`, `get_own_results`, `get_own_test_results`, `get_own_attendance` all resolve the student profile first via `students.user_id`.
- `get_own_results` / `get_own_test_results` filter to `status == "published"` only.
- `get_own_result(result_id)` returns one result only if: exists, `student_id` matches, and `status == "published"`. Otherwise -> same 404 `RESULT_NOT_FOUND` (no information leak).
- Client-supplied query parameters like `student_id`, `register_number`, `university_roll_number` are ignored by the service layer.

---

## 9. Validation rules

- `extra="forbid"` on API request schemas prevents injected fields.
- UUID path params validated by FastAPI -> 422 for malformed values.
- Student eligibility validated at service layer (approval status, active flag, institution active).
- Query-parameter manipulation (e.g., `?student_id=<other>`) is ignored; identity always comes from JWT.

---

## 10. API endpoint details

### 10.1 Student self-service (read-only)

All `/me/*` endpoints use `Depends(get_current_user)` and resolve identity via `student_data.get_own_*` functions:

```
GET /api/v1/students/me/profile              -> student_data.get_own_profile(user_id) -> assert_tenant_object
GET /api/v1/students/me/results             -> student_data.get_own_results(user_id)
GET /api/v1/students/me/results/{result_id} -> student_data.get_own_result(user_id, result_id) -> assert_tenant_object
GET /api/v1/students/me/test-results        -> student_data.get_own_test_results(user_id)
GET /api/v1/students/me/attendance          -> student_data.get_own_attendance(user_id)
```

### 10.2 Student-specific data access

The `student_context` service is the canonical resolver for any future Phase 6.9 feature that needs the authenticated student's `student_id` + `institution_id`:

```python
from app.services.student_context import get_student_context
context = get_student_context(current_user)
# context["student_id"], context["institution_id"], etc.
```

---

## 11. RBAC (preserved)

Phase 6.9 does not introduce new roles. The existing RBAC from Phase 6.5/6.6 is preserved:

- Only students with `approval_status == "approved"` and `is_active == True` and their institution `is_active == True` can access `/me/*` endpoints.
- Admins without a student profile get 404, not access to student data.
- Unauthenticated requests get 401.

---

## 12. Student context resolution

| Step | Source | Used |
|---|---|---|
| 1 | JWT `sub` claim | `auth_user_id` |
| 2 | `get_current_user()` lookup of `public.users` | `user_id`, `institution_id` |
| 3 | `student_context.get_student_context()` lookup of `students` | `student_id`, `institution_id`, `student_number`, `approval_status`, `is_active`, `status` |

All identity is server-side derived. The client cannot influence `student_id` or `institution_id`.

---

## 13. Security protections (detail)

| Threat | Mitigated by | Test |
|---|---|---|
| Client supplies `student_id` in query params | Server resolves from JWT `user_id` | `test_cannot_override_via_request_params` |
| Client supplies `register_number` | Ignored by service layer | `test_cannot_access_by_register_number` (covered in cross-student test) |
| Client supplies `university_roll_number` | Ignored by service layer | `test_cannot_access_by_roll_number` (covered in cross-student test) |
| Client supplies `email` | Ignored by service layer | `test_cannot_access_by_email` (covered in cross-student test) |
| Cross-tenant access | `assert_tenant_object` + `assert_student_context_tenant` | `test_cross_tenant_access_fails`, `test_tenant_assertion_on_profile` |
| Pending approval | `_assert_student_eligible` checks `approval_status` | `test_pending_student_not_eligible` |
| Inactive student | `_assert_student_eligible` checks `is_active` | `test_inactive_student_not_eligible` |
| No profile linked | 404 error | `test_returns_404_when_no_profile`, `test_non_student_has_no_context` |
| Malformed UUID in path | FastAPI validation | `test_malformed_result_id_rejected` |
| No untrusted params in OpenAPI | Schema inspection | `test_identity_params_never_trusted` |

---

## 14. Audit behavior

Phase 6.9 does not introduce new mutations. All endpoints tested are read-only self-service (`GET` methods). No audit logging is needed for read operations per the existing audit policy (reads are not audited at the action level).

---

## 15. Migration

**No migrations required.** Phase 6.9 uses the existing `students`, `institutions`, `student_results`, `test_results`, and `student_attendance` schema. The `student_context` service queries the existing `students` table using the existing `user_id` column. The existing Phase 6.8 migration has already added `institution_id` columns and guard triggers to the result tables.

---

## 16. Tests

### 16.1 Focused Phase 6.9 tests - `backend/tests/test_student_specific_data_phase_6_9.py`

**Result: 26 passed, 0 failed**

Covers 9 test groups:

| Test Group | Class | Tests |
|---|---|---|
| 1. Student context resolution | `TestStudentContextResolution` | 6 |
| 2. Profile access | `TestProfileAccess` | 3 |
| 3. Attendance access | `TestAttendanceAccess` | 3 |
| 4. Results access | `TestResultsAccess` | 5 |
| 5. Cross-student security | `TestCrossStudentSecurity` | 1 |
| 6. Cross-tenant security | `TestCrossTenantSecurity` | 2 |
| 7. Malformed IDs | `TestMalformedIds` | 1 |
| 8. Role boundaries | `TestRoleBoundaries` | 2 |
| 9. Existing security contracts | `TestExistingSecurityContracts` | 3 |

### 16.2 Test details

**Test Group 1 - TestStudentContextResolution:**
- `test_resolves_student_context_from_jwt_user_id` - Context resolves correctly from JWT-derived user_id
- `test_context_contains_only_safe_fields` - Only whitelisted fields in context, no passwords/tokens
- `test_returns_404_when_no_profile` - Missing student profile returns 404
- `test_pending_student_not_eligible` - Pending approval students get 403
- `test_inactive_student_not_eligible` - Inactive students get 403
- `test_non_student_has_no_context` - Admins/non-students get 404 (no student profile)

**Test Group 2 - TestProfileAccess:**
- `test_student_can_access_own_profile` - Student sees own profile
- `test_profile_ignores_client_supplied_student_id` - Query param `student_id` is ignored
- `test_profile_404_without_profile` - Missing profile -> 404

**Test Group 3 - TestAttendanceAccess:**
- `test_student_can_access_own_attendance` - Student sees own attendance
- `test_attendance_ignores_client_supplied_student_id` - Query param ignored
- `test_attendance_404_without_profile` - Missing profile -> 404

**Test Group 4 - TestResultsAccess:**
- `test_student_can_access_own_results` - Student sees own results
- `test_student_cannot_access_other_students_result` - Cannot see another student's result detail (same 404)
- `test_student_cannot_access_other_students_test_results` - Cannot see another student's test results
- `test_results_404_without_profile` - Missing profile -> 404
- `test_published_result_behavior_intact` - Only published results returned (draft/withheld filtered)

**Test Group 5 - TestCrossStudentSecurity:**
- `test_cannot_override_via_request_params` - All identity params (`student_id`, `user_id`, `institution_id`, `email`, `register_number`, `university_roll_number`) ignored; server uses JWT identity

**Test Group 6 - TestCrossTenantSecurity:**
- `test_cross_tenant_access_fails` - Result from different tenant -> 403 `TENANT_MISMATCH`
- `test_tenant_assertion_on_profile` - Profile from different tenant -> 403 `TENANT_MISMATCH`

**Test Group 7 - TestMalformedIds:**
- `test_malformed_result_id_rejected` - Non-UUID result_id -> 422

**Test Group 8 - TestRoleBoundaries:**
- `test_student_can_access_me_endpoints` - Students can access all `/me/*` endpoints
- `test_admin_cannot_access_student_me_endpoints` - Admin (no student profile) gets 404

**Test Group 9 - TestExistingSecurityContracts:**
- `test_publication_filter_intact` - Only published results returned
- `test_tenant_guard_intact` - Cross-tenant guard returns 403 (existing Phase 6.8 contract)
- `test_identity_params_never_trusted` - OpenAPI has no `student_id`/`user_id`/`auth_user_id` params on `/me/*` paths

---

## 17. Files

### New
| File | Purpose |
|---|---|
| `app/services/student_context.py` | Student context resolution service |
| `backend/tests/test_student_specific_data_phase_6_9.py` | Phase 6.9 focused test suite (26 tests) |
| `PHASE_6_9_STATUS.md` | This document |

### Modified (existing)
| File | Change |
|---|---|
| `app/services/student_data.py` | Uses `_assert_student_eligible` from `student_context` for eligibility checks; resolves identity from JWT `user_id` |
| `app/api/students.py` | `/me/profile` now uses `assert_tenant_object` for defense-in-depth |

---

## 18. Known limitations

- No live database migration is required for Phase 6.9 (uses existing schema).
- The `student_context` service is a read-only resolver; Phase 6.9 does not add student profile mutation endpoints (out of scope; no design for student self-edit of profile, status, or academic context).
- The service relies on the Supabase client `students` table query; direct SQL access patterns are not tested in Phase 6.9.

---

## 19. Explicit Phase 6.9 boundary (what was done)

Phase 6.9 implements and verifies:

- **Student context resolution service** (`app/services/student_context.py`) that resolves the authenticated student's identity from the JWT and enforces eligibility (approval status, active flag, institution active).
- **Whitelisted safe context fields** - no passwords or tokens exposed.
- **Security hardening of existing `/me/*` endpoints** - identity resolved server-side, tenant guard on profile endpoint.
- **26 focused tests** covering context resolution, all self-service data types (profile, attendance, results), cross-student security, cross-tenant security, malformed IDs, role boundaries, and preservation of existing Phase 6.7/6.8 security contracts.

---

## 20. Out of scope (NOT implemented)

Out of scope for Phase 6.9:

- No personalized chatbot, no recommendation system, no AI-generated result explanations.
- No new authentication system, no new RBAC system, no new tenant system.
- No student profile mutation endpoints (create/update/delete student self-service).
- No new database tables or migrations.
- No Phase 6.10, 6.11, or 6.12 implementation.

---

## 21. Implementation summary

Phase 6.9 is functionally complete:

- Student context resolution service (`student_context.py`) with `get_student_context()`, `_assert_student_eligible()`, and `assert_student_context_tenant()`
- Whitelisted safe context fields (no passwords/tokens exposed)
- Identity resolved from JWT `user_id`, never client-supplied
- Eligibility checks: approval status, active flag, institution active
- Tenant guard on profile endpoint (defense-in-depth)
- 26 focused tests passing
- Full regression: 891 passed, 8 skipped, 0 failed

---

## 22. Explicit boundaries (preserved)

- No new authentication system introduced
- No new RBAC system introduced
- No new tenant system introduced
- No new database tables or migrations
- Existing Phase 6.5-6.8 patterns preserved and tested
- No live-database physical validation tests added (existing pattern preserved)

---

*Prepared: 2026-09-13*
