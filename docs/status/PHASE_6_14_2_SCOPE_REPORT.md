# Phase 6.14.2 - Attendance Data Integration

## Objective

Secure, reusable student-facing attendance data layer. The authenticated
student retrieves ONLY their own attendance information, through the
existing Phase 6 identity / tenant / authorization architecture. No
second attendance system; no duplicated repository/service logic; no
schema redesign.

## Inspection (before coding)

Inspected before writing any code:

* `supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql`
  - `student_attendance(student_attendance_id, student_id, section_id,
    academic_year_id, semester_id, date, status, notes, created_at)` with
  status CHECK IN (present, absent, late, excused) and
  UNIQUE(student_id, section_id, date).
* `supabase/migrations/20260913000000_phase_6_7_attendance.sql`
  - additive hardening only: server-derived `institution_id`,
  `updated_at`, tenant/academic-context guard trigger, indexes.
* `backend/app/repositories/attendance.py` + `admin_academics.py`
  (`STUDENT_ATTENDANCE_COLUMNS`, `list_student_attendance` with
  academic_year_id / semester_id / date_from / date_to / limit filters).
* `backend/app/services/attendance.py` (admin CRUD service),
  `student_data.py` (`get_own_attendance(user_id, ...)` raw-row
  self-service), `student_context.py` (Phase 6.9 canonical context),
  `authorization.py` (Phase 6.13 scopes), `student_academic_profile.py`
  (Phase 6.14.1 pattern reused as the template).
* `backend/app/api/students.py` - existing `GET /students/me/attendance`
  returns RAW rows (includes `student_id`, `student_attendance_id`,
  `section_id`, ...). Existing tests
  (`test_attendance_phase_6_7.py`, `test_students_api.py`) assert the raw
  `student_id` field, so that contract genuinely requires internal ids
  and was left byte-identical.
* Authoritative attendance math:
  `app/services/personalization.py::_build_attendance_summary` -
  `present / total * 100`, `round(..., 2)`, `None` when no rows.
* `PHASE_6_14_1_SCOPE_REPORT.md` - additive, contract-preserving
  approach replicated here.

Finding: no reusable student-SAFE attendance projection/service existed
(raw rows or internal-only summary). New additive layer required;
nothing duplicated.

## Files created

* `backend/app/schemas/student_attendance.py`
  (`StudentAttendanceRecord`, `StudentAttendanceSummary`,
  `StudentOwnAttendance`; all `extra="forbid"`).
* `backend/app/services/student_attendance.py`
  (`get_own_attendance(current_user, ...)` + dict form).
* `backend/tests/test_attendance_6142.py` (15 hermetic tests).
* `PHASE_6_14_2_SCOPE_REPORT.md` (this report).

## Files modified

* `backend/app/api/students.py` (additive only):
  new `GET /students/me/attendance/summary` -> `StudentOwnAttendance`.
  All existing routes unchanged (including raw `GET /me/attendance`).

## Database changes

No migration required (verified). All columns read already exist:
`date/status/notes` (Admin-1) + `institution_id/updated_at` (Phase 6.7).
Counts/percentage are computed in Python, never stored.

## API changes

* ADDED `GET /api/v1/students/me/attendance/summary`
  (summary + student-safe records, no internal ids). Auth via
  `get_current_user` (401 AUTH_REQUIRED). Accepts ONLY non-identity
  filters already supported by the existing schema: `academic_year_id`
  / `semester_id` (UUID; FastAPI 422 VALIDATION_ERROR when malformed)
  and `date_from` / `date_to` (YYYY-MM-DD; 422 INVALID_FILTER when
  malformed, or when `date_from` > `date_to`). No identity parameters;
  `?student_id=...` is inert (200, own data) or 422, never trusted.
* CHANGED: none. Existing contracts preserved.
* UNCHANGED: `GET /api/v1/students/me/attendance` (raw rows; existing
  frontend/tests contract requires `student_id`).

## Security

* Student derived from authenticated identity only (`user_id` from JWT
  via `get_current_user`). Service signature
  `(current_user, academic_year_id=None, semester_id=None,
  date_from=None, date_to=None, client=None, limit=200)`: no identity
  params (`student_id`/`user_id`/`institution_id`/email/register-number/
  roll-number cannot occur).
* Tenant via existing mechanism + `assert_tenant_object` (403
  TENANT_MISMATCH cross-tenant); repository is queried with the
  JWT-derived `student_id`, plus defense-in-depth row filtering.
* No authorization weakened; no new roles; no client-trusted fields.
* Cross-student access impossible (no student selector; other token ->
  404 STUDENT_PROFILE_NOT_FOUND, never another student's rows).
* Data minimization: no internal ids, own data only.
* Error messages never leak another student's existence (404/403 use
  the project's standard codes).

## Attendance rules

Reused authoritative rule from
`app/services/personalization.py::_build_attendance_summary` (unchanged
semantics): total = number of rows; counts per status in
{present, absent, late, excused}; `attendance_percentage =
round(present / total * 100, 2)`; `None` when zero records (no
division error). Unknown/blank/missing statuses count toward the total
but toward no bucket (same as authoritative helper). No course-level
`total_classes`/`course_code`/`course_name`/`semester` label fields:
stored rows carry only section/academic FKs and the project has no
verified section->course label helper for self-service, so no fields
toward no bucket (same as authoritative helper). No course-level
`total_classes`/`course_code`/`course_name`/`semester` label fields:
stored rows carry only section/academic FKs and the project has no
verified section->course label helper for self-service, so no fields
were invented.

## Tests

* Phase 6.14.2 file (`backend/tests/test_attendance_6142.py`): 15 passed.
  1. own attendance ok. 2. belongs to auth student + no internal ids.
  3. unauth 401 AUTH_REQUIRED. 4. other token 404 (JWT-derived lookup).
  5. cross-tenant 403 TENANT_MISMATCH. 6. client student_id inert.
  7. empty attendance (records_available False, percentage None).
  8. percentage 3/4 -> 75.0. 9/9b. zero total -> None (service + API).
  10. invalid date/UUID filters -> 422 INVALID_FILTER.
  11. existing raw `/me/attendance` unchanged. 12. service signature has
  no identity params. 13. service cross-tenant 403. 14. service missing
  profile 404.
* Focused regression (6.14.1 + students_api + student_data_service +
  student_specific_data_6_9 + student_auth_6_5 + attendance_6_7 +
  personalized_chat_6_10 + tenant_isolation + rbac_6_6):
  248 passed, 3 skipped.
* Full backend suite (`pytest tests` from `backend/`):
  1425 passed, 15 skipped, 0 failed
  (baseline 1410 passed / 15 skipped per brief; +15 new, zero regressions,
  no tests modified/removed).

## Unresolved issues

None
