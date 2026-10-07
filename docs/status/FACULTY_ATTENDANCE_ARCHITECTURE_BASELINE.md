# Attendance implementation baseline

Audit recorded on 7 October 2026 before implementation changes.

The existing Phase 10 migration owns `faculty_attendance_rosters`, sessions,
records, imports and staging rows. `student_attendance` remains the registered
student projection. Reuse these tables and their IDs; summaries are provenance,
never historical sessions. Existing attendance percentage is present / recorded
statuses, including late/excused in the denominator. 75% is a monitoring threshold.

`phase81_rbac._active_sections` resolves section → offering → course/program →
semester/year/department/institution. `faculty_responsibilities.authorize_section`
and `authorization.effective_authorization` are the authorization baseline.
Teaching mutations require exact live teaching scope and attendance.manage.
HOD/Class In-Charge mapped permissions grant reads only; class membership uses
program/year/semester/section code. Preserve validity and revocation checks.

Student registration services create pending students using tenant-derived identity;
approval changes the existing students row. Phase 10 has a reconciliation trigger,
but its OR match can link conflicting identities and does not synchronize history.
Extend that trigger instead of adding registration/account creation mechanisms.

Faculty API/service and `facultyAttendanceApi.ts`, FacultyAttendance, its upload
stages/primitives and FacultyShell are existing integration points. The current
dashboard uses imported summaries and placeholder history; replace with recorded
data. Existing staged imports lack correction and atomic commit; extend them.

`extraction.extract_text` provides bounded deterministic PDF extraction;
`generation_provider.OpenRouterGenerationProvider` provides AI generation. There
is no OCR implementation in the repo. Add a bounded OCR adapter before optional
generation, validate schema and feed the existing staging pipeline. R2 storage
is private through `services/storage.py`; attendance currently retains staging
JSON rather than raw files. No new storage backend or public raw-file URL is needed.

Audit events use append-only admin_audit_log/record_admin_action. Existing backend
pytest and frontend Vitest suites include responsibility authorization, student
attendance, registration, admin isolation, shells and RAG regression coverage.
No AGENTS.md was found in the workspace/parent instruction paths. The worktree
already contains the prior responsibility phase and attendance UI edits; retain
those changes. Real migration/concurrency execution must be reported separately.
