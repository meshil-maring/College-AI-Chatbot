# PHASE 6.7 — ATTENDANCE DATA STATUS (UNLOCKED, PENDING REVIEW)

Status date: 2026-09-13. Baseline: Phases 6.1-6.6 LOCKED (765 passed / 0 failed / 2 skipped canonical baseline preserved). No LOCK file created for 6.7.

## 1. Existing academic schema discovered

Inspected `supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql`, `app/repositories/admin_academics.py`, `app/services/admin_academics.py`, `app/api/admin.py`, `app/api/students.py`, `app/services/student_data.py`, `app/core/security.py`, existing tests.

Found (reused, NOT duplicated):

- `institutions(institution_id)` — canonical tenant.
- `students(student_id, user_id, institution_id, program_id, ...)` — canonical tenant key is `students.institution_id`.
- `programs`, `academic_years`, `semesters`, `departments(institution_id)`, `courses(department_id)`, `course_offerings(course_id, academic_year_id, semester_id, program_id)`, `sections(section_id, code, offering chain)`.
- `student_attendance(student_attendance_id, student_id, section_id, academic_year_id, semester_id, date DATE, status, notes, created_at)` with status CHECK IN (present,absent,late,excused) + not-blank, UNIQUE(student_id, section_id, date), FKs student CASCADE / section RESTRICT / AY RESTRICT / semester RESTRICT.
- NO enrollment table exists — per-section enrollment cannot be verified (see section 17).
- NO prior attendance write API/service beyond read projection `list_student_attendance`.
- Auth: `get_current_user` (JWT) + `require_roles("admin")` for `/admin/*`; server-side `users.user_id -> students.user_id` for `/students/me/*`.
- Tenant helpers: `user_tenant_id / scope_tenant / assert_tenant_object` -> 403 TENANT_MISMATCH.
- Audit: `admin_audit_log` + `record_admin_action` via `_record_audit`.
- RLS: no CREATE POLICY / RLS statements in any migration; service-role + application-layer guards remain the model.

Decision: NO new attendance table. Harden existing `student_attendance` additively.

## 2. Attendance data model

Existing `student_attendance` + additive hardening (`supabase/migrations/20260913000000_phase_6_7_attendance.sql`):

- `institution_id uuid NOT NULL REFERENCES institutions(institution_id)` — server-derived tenant, backfilled from students, trigger-overridden on every write, never client-trusted.
- `updated_at timestamptz NOT NULL DEFAULT now()` — project convention; refreshed by guard trigger on UPDATE; backfilled from created_at.
- Guard trigger `student_attendance_tenant_guard` BEFORE INSERT OR UPDATE: derives institution_id from STUDENT; rejects student/section cross-institution pairing; rejects AY/semester not matching the section offering; forbids ownership reassignment on UPDATE; refreshes updated_at.
- Indexes: `idx_student_attendance_institution_id`, `idx_student_attendance_student_date`, `idx_student_attendance_ay_semester`.
- Date stored as DATE (calendar-day record, no timezone conversion).
- Layers: `app/repositories/attendance.py` (scoped queries) -> `app/services/attendance.py` (validation, tenant from student) -> `app/api/admin.py` (admin CRUD) + existing `/me/attendance` self-service via `student_data.get_own_attendance`. `admin_academics` attendance functions kept as thin delegates.

## 3. Attendance status model

Reused existing CHECK vocabulary: present, absent, late, excused. No new statuses. Service validates -> 422 INVALID_ATTENDANCE_STATUS. Create requires status; update validates when present.

## 4. Student relationship

`attendance.student_id -> students.student_id` (existing FK CASCADE). Never email/register-number for FK. Self-service derives identity from JWT, never client student_id.

## 5. Institution/tenant relationship

Canonical key remains `students.institution_id`. No tenant_id/college_id/school_id introduced. attendance.institution_id is a trigger-maintained denormalization guaranteed = students.institution_id; any client value overwritten. Section institution (section->offering->course->department->institution) must equal student institution or insert fails (403 TENANT_MISMATCH service / exception DB).

## 6. Subject/context relationship

Section is the academic context: `attendance.section_id -> sections.section_id` (existing FK). AY/semester on the row must equal the section offering (sections -> course_offerings). Repository resolves via sections + course_offerings(course_id, academic_year_id, semester_id, program_id, courses(department_id, departments(institution_id))). Mismatch -> 422 ACADEMIC_CONTEXT_MISMATCH (service) / exception (DB). No duplicate subjects/courses/programs/semesters/years created.

## 7. Uniqueness rule

Retained existing UNIQUE(student_id, section_id, date) (student_attendance_student_section_date_key, Admin-1). Correct because rows are daily per student+section; no session entity exists. DB-enforced (concurrency-safe). Service maps 23505/duplicate -> 409 ATTENDANCE_DUPLICATE. Verified by concurrent-thread test + live-DB opt-in test.

## 8. API endpoints

/api/v1 conventions, no route conflicts:

- GET /api/v1/admin/students/{student_id}/attendance (filters: academic_year_id, semester_id, date_from, date_to) — admin list, tenant-guarded.
- POST /api/v1/admin/attendance (201) — admin create.
- PATCH /api/v1/admin/attendance/{attendance_id} — admin update (status/notes only).
- DELETE /api/v1/admin/attendance/{attendance_id} — admin hard delete (Admin-1 policy, no soft-delete).
- GET /api/v1/students/me/attendance (pre-existing) — student self-service, JWT-derived identity; extra student_id/institution_id params are inert.

## 9. Role permissions

Locked Phase 6.6 RBAC reused, no new roles:

- admin (require_roles("admin")): full attendance management within tenant; platform admin (institution_id=None) retains global authority.
- staff / faculty / student: 403 FORBIDDEN on all /admin/*attendance* (verified). Students use only /students/me/attendance. Platform staff stays non-global (403).

## 10. Tenant isolation

Order: authenticate -> role (admin) -> _assert_student_tenant (assert_tenant_object) -> operation. Cross-tenant create/list/update/delete -> 403 TENANT_MISMATCH, service never reached. Update/delete re-resolve the row student. Service + DB trigger give defense-in-depth.

## 11. Student self-access

GET /students/me/attendance resolves users.user_id -> students.user_id server-side; tenant assert on profile; lists only own rows. No /{student_id} self path; no student create/update/delete (403 on admin paths). Missing profile -> 404 STUDENT_PROFILE_NOT_FOUND (never another student data, never silent empty broadening).

## 12. Validation rules

Pydantic extra="forbid" on AttendanceCreate/AttendanceUpdate: unknown/control fields (institution_id, created_by, updated_by, approval_status, role, auth_user_id, student_id on update, etc.) -> 422, service never reached. UUID fields -> 422 malformed; date -> 422 invalid; status -> 422 INVALID_ATTENDANCE_STATUS; empty update -> 422 EMPTY_UPDATE; missing fields -> 422. Unknown student -> 404 STUDENT_NOT_FOUND; unknown section -> 404 SECTION_NOT_FOUND; broken offering chain -> 422 ACADEMIC_CONTEXT_INVALID; AY/sem mismatch -> 422 ACADEMIC_CONTEXT_MISMATCH; section/student tenant split -> 403 TENANT_MISMATCH.

## 13. Database constraints

FKs (student CASCADE, section/AY/semester RESTRICT, institution), NOT NULLs, status CHECKs (retained), UNIQUE(student,section,date) (retained), guard trigger (tenant/academic/ownership/updated_at), 3 indexes (section 2). Python checks are pre-validation only; concurrency safety comes from DB constraints.

## 14. Audit behavior

Reused existing admin_audit_log/record_admin_action — no second system. Admin create/update/delete write attendance.create/update/delete on student_attendance via _record_audit (actor from JWT, no tokens logged). Student reads not audited (existing read policy). Faculty/staff cannot mutate so no audit gap; audit is action-level, not field-diff history.

## 15. Migration

supabase/migrations/20260913000000_phase_6_7_attendance.sql (additive only; no locked migration edited; no CREATE TABLE). Adds institution_id + backfill + NOT NULL + FK; updated_at + backfill + default + NOT NULL; guard function + trigger; 3 indexes; comments; manual rollback block. Applied to linked remote: supabase migration list shows 20260913000000 on Local + Remote.

## 16. Tests

NEW backend/tests/test_attendance_phase_6_7.py — 54 passed, 3 skipped (live-DB opt-in class mirroring test_physical_validation_phase_4_4.py, no hardcoded credentials): schema contract, service CRUD + delegates, concurrency race (ThreadPoolExecutor -> one ok + one ATTENDANCE_DUPLICATE), API auth/roles (401 unauth, 403 staff/faculty/student), tenant isolation (cross-tenant 403 all ops; platform admin global ok; platform staff 403), validation (UUID/date/required/unexpected/ownership-injection/empty/404), self-service (own ok, identity params inert, missing profile 404), repository units, live-DB opt-in (backfill/trigger/duplicate). Full canonical suite: 819 passed, 5 skipped (includes 54 new; baseline 765/0/2 — delta is the new file; zero failures from 6.7).

## 17. Known limitations

- No enrollment table exists -> per-section enrollment cannot be enforced; only institution + offering-match verifiable. Do not invent enrollment in 6.7; Phase 6.9 may address.
- Section institution resolution depends on the full offering->course->department chain; broken chain fails closed (422/exception) — orphaned academic rows block writes until fixed.
- Audit is action-level, not field-diff history.
- RLS unchanged (none; application-layer model retained by design).
- Date is calendar-day; multiple sessions per day per section not representable (matches existing UNIQUE; a session model would be a new academic entity, out of scope).

## 18. Explicit Phase 6.8 boundary

NOT implemented: test/exam results, marks, grades, personalized chatbot, student-specific reasoning, RBAC redesign, new auth, new tenant architecture, 6.9 academic-data authorization redesign, 6.10 chatbot, 6.11 security testing, 6.12 demo validation. No result/grade tables, columns, endpoints, or services added or altered.
