# PHASE 6.7 — ATTENDANCE DATA LOCK

## STATUS: LOCKED

Lock date: 2026-09-13
Locked at formal review approval. Remaining blockers: NONE.

---

## 1. Phase Number

Phase 6.7

## 2. Phase Name

Phase 6.7 — Attendance Data

## 3. Locked Objective

Phase 6.7 provides the attendance data foundation. The existing
`student_attendance` model was reused rather than creating a duplicate
attendance table. Phase 6.7 adds additive tenant and security hardening
plus attendance management and self-service behavior on top of the
locked Phase 6.1-6.6 identity, tenant, authentication, and RBAC
foundations.

## 4. Locked Attendance Model

Existing attendance structure remains authoritative. Attendance is
associated with:

- student
- section
- academic year
- semester
- institution

Section provides the academic context through the existing chain:

```text
section -> offering -> course -> department
```

The Phase 6.7 migration
(`supabase/migrations/20260913000000_phase_6_7_attendance.sql`) is
additive only and provides:

- `institution_id` column
- tenant foreign key to `institutions(institution_id)`
- NOT NULL enforcement
- `updated_at` column
- tenant guard trigger
  (`student_attendance_tenant_guard` / `trg_student_attendance_tenant_guard`)
- ownership protection (student_id, section_id, academic_year_id,
  semester_id are immutable on UPDATE)
- academic-context consistency checks (row academic_year_id and
  semester_id must correspond to the section offering context)
- required indexes

The migration has been verified on Local and Remote
(`supabase migration list` shows `20260913000000` on both). No duplicate
academic entities were introduced, and no previous migration was
modified.

## 5. Locked Attendance Statuses

The existing controlled statuses remain:

- present
- absent
- late
- excused

Invalid status values are rejected (service validation, 422
`INVALID_ATTENDANCE_STATUS`, backed by the existing CHECK constraint).
No new attendance-status vocabulary was introduced.

## 6. Locked Student Relationship

Attendance references:

```text
attendance.student_id -> students.student_id
```

Student self-service identity is derived server-side from the
authenticated relationship (JWT -> public.users -> students).
Client-supplied student identity cannot override the authenticated
student for self-service.

## 7. Locked Tenant Model

Canonical tenant key remains:

```text
students.institution_id
```

Attendance institution context is server-derived and must match the
student's institution. The attendance tenant guard enforces the
relationship at database level. Section institution must also be
consistent with the attendance and student institution. Cross-tenant
access is rejected (403 `TENANT_MISMATCH`).

## 8. Locked Academic Context

Attendance uses the existing section and academic structure. The
attendance academic year and semester must correspond to the section's
offering context. Do not create a new enrollment system. The absence of
an enrollment table is a documented limitation.

## 9. Locked Duplicate Protection

The existing database uniqueness rule remains authoritative:

```text
UNIQUE(student_id, section_id, date)
```

Database-level uniqueness is required for concurrency safety. Duplicate
attendance is mapped to the project's attendance-specific conflict
behavior:

```text
409 ATTENDANCE_DUPLICATE
```

## 10. Locked Database Hardening

Recorded migration:

```text
supabase/migrations/20260913000000_phase_6_7_attendance.sql
```

It is additive only and provides institution_id, the tenant foreign key,
NOT NULL enforcement, updated_at, the tenant guard trigger, ownership
protection, academic-context consistency checks, and required indexes.

## 12. Locked RBAC

Attendance management follows the locked Phase 6.6 authorization model.
Current management policy:

- admin -> permitted attendance management
- staff -> 403 on the attendance admin management paths
- faculty -> 403 on the attendance admin management paths
- student -> 403 on attendance mutation
- student -> own attendance read access

Staff and faculty attendance-management permissions are not broadened as
part of this lock. Future changes to attendance-management permissions
must be handled as a separately reviewed change.

## 13. Platform Policy

Platform admin behavior remains consistent with the locked Phase 6.1,
6.4, and 6.6 policy. Platform staff does not gain global administrative
authority. Platform role semantics are unchanged.

## 14. Student Self-Service

Student attendance access is locked to the authenticated student's own
records. The server resolves JWT -> public.users -> students and does
not trust a client-provided student_id for self-service. Students cannot
create, update, or delete attendance, and cannot access another
student's attendance.

## 15. Security

Locked guarantees:

- authentication required
- role authorization enforced
- tenant authorization enforced
- object ownership enforced
- client institution_id cannot override server context
- client student_id cannot override self identity
- cross-tenant access rejected
- unauthorized mutations do not execute
- database tenant guard provides defense in depth
- duplicate writes are database protected

Expected authorization behavior:

- Unauthenticated -> 401
- Insufficient role -> 403
- Wrong tenant -> 403 TENANT_MISMATCH
- Wrong ownership -> existing safe ownership response

## 16. Audit

Attendance mutations reuse `admin_audit_log` and `record_admin_action`.
Actions include `attendance.create`, `attendance.update`, and
`attendance.delete`. No second audit system was introduced. Attendance
reads remain unaudited according to existing project policy.

## 17. Test Baseline

Phase 6.7 tests:

```text
54 passed
3 skipped
0 failed
```

The 3 skipped tests are the opt-in live-database class requiring
credentials.

Complete backend result:

```text
819 passed
5 skipped
0 failed
```

Canonical command:

```text
cd backend
python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py
```

## 18. Test Integrity

Recorded explicitly:

- no tests weakened
- no tests deleted
- no failures hidden
- no artificial skips
- database constraints verified
- concurrency duplicate protection verified
- live database migration verified

## 19. Files

Modified:

```text
backend/app/api/admin.py
backend/app/repositories/admin_academics.py
backend/app/services/admin_academics.py
backend/tests/test_admin_api.py
```

New:

```text
backend/app/repositories/attendance.py
backend/app/services/attendance.py
backend/tests/test_attendance_phase_6_7.py
supabase/migrations/20260913000000_phase_6_7_attendance.sql
PHASE_6_7_STATUS.md
```

No other file was part of the final Phase 6.7 implementation.

## 20. Known Limitations

1. No enrollment table currently exists.
2. Attendance validates institution and offering/section consistency
   rather than enrollment membership.
3. Broken academic offering chains fail closed.
4. Attendance uses calendar-day DATE semantics.
5. Multiple attendance sessions on the same student/section/date are
   not supported by the current uniqueness model.
6. RLS was not redesigned.
7. Action-level audit exists; reads are not audited.
8. Staff/faculty attendance-management permissions are not currently
   enabled through the admin attendance paths.

These limitations are documented and were not solved during the lock
step.

## 21. Phase Boundary

Phase 6.7 does NOT implement:

- Phase 6.8 test/exam results
- marks
- grades
- personalized chatbot
- Phase 6.9 student-specific academic data architecture
- Phase 6.10 personalized chatbot
- Phase 6.11 broader security testing
- Phase 6.12 final demo validation

Phase 6.8 has NOT started.

## 22. Lock Verification

Pre-lock checks performed: `git status` confirmed the Phase 6.7 file
set; `git diff --name-only HEAD` showed no Phase 6.1-6.6 lock-file
modifications; no unrelated files changed; no temporary or debug files
remained; no secrets were added; and focused plus full-suite test runs
matched the reviewed report. Post-lock verification below confirms the
lock step added only this document.

---

## Official lock statement

> "PHASE 6.7 — LOCKED"

> "Attendance data functionality and its authorization, tenant isolation,
> validation, and database protections are formally locked. No Phase 6.8+
> functionality has been implemented as part of this lock."


