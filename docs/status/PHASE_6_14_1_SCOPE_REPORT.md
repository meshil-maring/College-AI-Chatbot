# Phase 6.14.1 - Student Academic Profile

## Objective

Secure reusable backend representation of the authenticated student's
academic profile. No architecture redesign; reuse Phase 6 identity, auth,
RBAC, tenant-resolution, authorization code.

## Inspection

Inspected: Phase 6 migrations, students model/schema, repositories
`get_own_profile` returns the raw internal row (with student_id / user_id
/ institution_id / program_id / academic_year_id) and locked
STUDENT_COLUMNS lacks register_number / university_roll_number / email /
approval_status. New additive service + projection required; nothing
duplicated.

## Files created

- `backend/app/schemas/student_profile.py` (StudentAcademicProfile)
- `backend/app/services/student_academic_profile.py` (get_academic_profile)
- `backend/tests/test_academic_profile_6141.py` (9 hermetic tests)
- `PHASE_6_14_1_SCOPE_REPORT.md` (this report)

## Files modified (additive only)

- `backend/app/repositories/admin_academics.py`: STUDENT_ACADEMIC_PROFILE_
  COLUMNS + get_student_academic_profile_row(). Existing projections and
  functions byte-identical.
- `backend/app/api/students.py`: new GET /students/me/academic-profile.
  All existing routes unchanged.

## APIs

- ADDED `GET /api/v1/students/me/academic-profile` -> StudentAcademicProfile
  (14 student-facing fields, no internal ids). Auth via get_current_user
  (401 AUTH_REQUIRED). No identity params; unknown query params 422.
- CHANGED: none. All existing contracts preserved.

## Database changes

None. No migration. All columns read already exist (Admin-1 + Phase 6.2 +
reference tables via existing repository helpers).

## Security guarantees

- Student derived from authenticated identity only (user_id from JWT).
  Service signature (current_user, client=None): no identity params.
- Tenant via existing mechanism + assert_tenant_object (403
## Tests added (test_academic_profile_6141.py, 9 tests)

1. own profile ok (Req 1). 2. no internal ids. 3. unauth 401 (Req 2).
4. other token 404 (Req 3). 5. cross-tenant 403 API (Req 4).
6. client identifiers ignored/422 (Req 5). 7. service signature.
8. service cross-tenant 403. 9. service missing profile 404.
Auth tests (test_student_auth_phase_6_5.py) kept, green (Req 6).

## Validation results

- 6.14.1 file: 9 passed.
- Focused Phase 6 (profile + students_api + student_data_service +
  student_specific_data_6_9 + student_auth_6_5): 98 passed.
- Full backend suite: 1410 passed, 15 skipped (baseline 1401/15 per
  6.13.9 report; +9 new, zero regressions, no tests modified/removed).

## Unresolved issues

None. No lock file created per instructions.

  TENANT_MISMATCH cross-tenant).
- No authorization weakened; no new roles; no client-trusted fields.
- Cross-student access impossible (no student selector).
- Client identifiers cannot override (no params; 422 or ignored).
- Data minimization: no internal ids, no secrets, own data only.
- Institution label emitted only when institution row id matches.

(admin_academics, personalization, tenancy), services (student_data,
student_context, student_auth, authorization), security.py, students +
student_auth APIs, personalized chat, tests, lock/scope docs.

Finding: no equivalent reusable student-facing profile service existed.
