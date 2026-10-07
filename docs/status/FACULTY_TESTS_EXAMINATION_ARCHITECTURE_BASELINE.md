# Faculty tests and examination architecture baseline

Audited 7 October 2026, before implementation. Existing uncommitted responsibility and attendance work is retained.

Repository-wide searches found no shared exam/test entity. `test_results` (Admin-1) stores per-student scores, with Phase 6.8 tenant/context guards and uniqueness. `student_results` and `student_result_items` store semester summaries and grades; these remain separate and unchanged. Existing types are quiz, assignment, midterm, final, project, internal, external. No grading policy or timetable engine exists.

`services/results.py` and `repositories/results.py` provide legacy admin CRUD and score calculation. Admin APIs already require results.read/results.manage and tenant scope. `TestResultsManager` reads a selected student's scores; `ResultsManager` reads semester results and uploads CSV. They do not create scheduled shared tests. Student `student_data`/`student_results` services filter published own records; `ResultsDetail` uses the existing Student shell. Faculty Results currently renders a placeholder.

Academic context is sections → course_offerings → course/program/year/semester, with course and program departments anchoring institution. Sections are subject-specific; class responsibilities group program/year/semester/section code. The central `faculty_responsibilities.authorize_section` and `authorization.effective_authorization` already support results.read/results.manage and exact teaching scope. HOD/Class In-Charge mappings currently lack results.read; add that explicit monitoring mapping only. Preserve role/permission/assignment architectures.

Attendance rosters support unregistered and pending students, safe identifier agreement, conflict quarantine and registration reconciliation. Marks will reference these existing roster IDs in `test_results`; optional student linkage is derived from safe roster reconciliation. No second roster/enrollment/result system is needed. Historical legacy result IDs and marks remain untouched. Extend the existing result guard for roster-backed rows, retaining its legacy behavior.

Attendance import parsing supplies bounded CSV/XLSX/XLS readers, formula rejection for XLSX, archive validation and upload limits. Reuse these parsers and shared filename/MIME validation; store marks review provenance privately, without raw R2 files or AI. Existing private storage/R2 and extraction were inspected; deterministic spreadsheets need neither OCR nor provider calls.

`admin_audit_log` is append-only. Existing atomic attendance RPCs show transaction/audit and live authority checks after locks. New test operations will use server-derived actor/tenant, owner enforcement, version checks, transaction locks and that audit table. Locked corrections require an explicit reason and preserve old/new values in the existing audit.

Frontend reuses FacultyShell/navigation, dark portal components, academic selectors, authentication and existing API error conventions. Bulk marks use one bounded request, explicit present/absent/exempt/not_attempted/missing semantics, review before submit/publish and navigation protection. Student projection adds status/pass-fail without internal remarks.

Verification baseline: Phase 6.8 result tests; Faculty/responsibility/attendance tests; Student result tests; shell/navigation tests; full backend/frontend suites; disposable Docker migration replay and SQL concurrency fixtures. No remote database migration or deployment is authorized or planned.
