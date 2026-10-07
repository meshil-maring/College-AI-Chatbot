# Faculty Attendance Management & Import Workflow

Verified on 7 October 2026. This supersedes the earlier incomplete attendance foundation report.

## 1. Status

**IMPLEMENTATION STATUS: PASS**

**DATABASE VERIFICATION: PASS**

The Faculty portal now uses recorded attendance for overview, students, subject profiles, session history, reports, marking, import correction/review and import history. Teaching mutations remain separate from responsibility monitoring. Marking and imports use atomic database operations with audits and live scope checks. Registration reconciliation preserves history and quarantines conflicting identities.

Final complete suites: **2,873 backend tests passed, 27 skipped, 6 warnings**; **70 frontend files and 582 tests passed**. TypeScript, build, targeted Ruff, compilation, SQL parsing, fresh migration replay, database contracts and concurrency checks passed. This is not a production deployment or live OCR/provider verification; deployment requirements are reported below.

## 2. Architecture audit

The preimplementation audit is recorded in [FACULTY_ATTENDANCE_ARCHITECTURE_BASELINE.md](FACULTY_ATTENDANCE_ARCHITECTURE_BASELINE.md). It inspected Phase 10 attendance tables/migrations, legacy attendance, academic relationships, student registration/approval, teaching assignments, responsibilities and central authorization, Faculty routes/services/UI/navigation, uploads, extraction/provider, R2, audit and existing tests.

The hierarchy remains institution → department/program → academic year/semester → course offering/subject → section → attendance. Sections are course-specific; Class In-Charge class scope groups the authorized program/year/semester/section code across subjects. Prior uncommitted responsibility and attendance UI changes were retained.

## 3. Existing attendance infrastructure reused

- Existing Phase 10 faculty attendance rosters, sessions, records, imports and staging rows.
- Existing student_attendance projection, status vocabulary and student identity/approval tables.
- Central faculty_responsibilities.authorize_section and authorization.effective_authorization, live assignments and responsibility mappings.
- FacultyShell/navigation, authentication provider, API envelopes and established dark portal components.
- Bounded upload reading, extraction.extract_text, OpenRouterGenerationProvider, private storage and append-only admin_audit_log.
- Existing paginated repository helpers to avoid REST row-limit truncation.

No duplicate attendance/student/section tables, authentication, permission, assignment, storage, generation provider or audit system was created.

## 4. Changes implemented

Added authorized resources, recorded statistics/trends, searchable/paginated students, individual subject history, session history and import history. Added strict deterministic import parsing, staged correction, atomic stage/review/commit/mark RPCs, safer reconciliation, legacy history deduplication and bounded OCR/optional AI extraction. Expanded file/identity/security and regression tests.

Main implementation files: backend attendance services/reporting/extraction, Faculty API and attendance schemas; frontend facultyAttendanceApi.ts, FacultyAttendance and its attendance components. Runtime dependencies added: xlrd for binary XLS and Pillow for image verification; uv.lock updated.

## 5. Database changes

20261012000000_faculty_attendance_workflow.sql extends existing rosters with reconciliation state/errors and staged rows with warnings. It replaces the existing context/reconciliation triggers, backfills legacy attendance roster identities, preserves IDs/history, quarantines inconsistent inherited links and synchronizes already-approved identities using the same safe trigger.

Atomic functions stage/review/commit imports and create/correct sessions, with owner/version/identity checks and transactional audits. Locks protect compound writes and ensure live assignment validity is checked after waits. Mutation RPC execution is service_role-only; public/anonymous/authenticated execution is revoked.

20261004235959_permission_primary_key_convergence.sql resolves an actual fresh-replay failure: the historical baseline used permissions.id, while Phase 8 expected permission_id. A conditional rename retains IDs/FKs, is a no-op for converged schemas and rejects ambiguous schemas. It sorts before Phase 8 for fresh replay; existing deployments must account for this earlier timestamp when applying pending migrations.

Historical migrations and the prior responsibility migration were retained. No new attendance table, destructive reset or summary-to-session fabrication occurs.

## 6. API changes

Paths below are under /api/v1/faculty/attendance and use the existing authenticated Faculty dependency.

| Method/path | Behavior |
| --- | --- |
| GET /resources | Authorized academic scopes and independent teaching mutation capability |
| GET /sections/{id}/overview | Recorded totals, low count, percentage and trends |
| GET /sections/{id}/students | Bounded pagination/search/registration/low filters/sorting |
| GET /roster/{id}/profile | Authorized identity and subject history |
| GET /sections/{id}/sessions | Paginated session statistics |
| POST /sections/{id}/mark | Atomic marking or owner correction for a date |
| POST /sections/{id}/imports | Bounded upload/extraction/validation/staging |
| GET /imports/{id}/review | Authorized reviewed rows and issues |
| PATCH /imports/{id}/rows/{number} | Owner correction and full revalidation |
| POST /imports/{id}/commit | Fresh validation and atomic version-checked commit |
| GET /sections/{id}/imports | Paginated history |
| GET /imports/{id}/errors.csv | Minimal formula-safe error report |

Existing assignment/roster endpoints remain. Client payloads cannot choose identity links or override registration/approval state. Deletion of rosters with recorded Faculty attendance is denied. Extraction runs in a thread pool.

## 7. Authorization model

Reads resolve the active account/institution/Faculty role, active academic chain, exact scope and mapped permission through the existing central resolver. Selectors contain only authorized resources. Profile/session/review/export routes independently repeat backend authorization.

Mutation requires a valid exact subject/section teaching assignment plus attendance.manage. Responsibility permissions alone cannot mutate. Existing sessions require the conducting teacher for correction; import correction/commit requires its uploader. Actor/tenant values come from authenticated context. Atomic RPCs enforce the same teaching, permission, academic chain, owner and validity invariants inside the transaction.

Expired/revoked scopes fail closed. The frontend refreshes on context changes and focus and clears stale workflow state.

## 8. Import workflow

Upload → validate → review/correct → explicit import. Upload retains validated staging JSON in existing private tables; attendance/account creation does not occur before commit. Blocking errors/duplicates/conflicts disable import, and commit revalidates stored rows.

CSV/XLSX/binary XLS are deterministic. XLSX shared/inline strings, absolute worksheet relationship paths and bounded cell references are supported; formulas are rejected. Structured machine-readable PDF text is extracted first. Scans use bounded local OCR. Structured OCR stays deterministic; unstructured text may use the existing OpenRouter provider after explicit token-cost consent. Strict schemas reject unexpected fields/authority IDs/non-string extracted identities before common validation.

Required columns: register_number, student_name (name alias supported) and attendance information. University roll number is optional in first semester with an explicit warning, required later. Email/address are optional. Explicit status requires an ISO date; summaries remain provenance and never create historical sessions. Percentage preserves present / all recorded statuses, including late/excused in the denominator.

Limits: 10 MB file, 500 rows, 20 columns, 50 MB expanded XLSX, 20-megapixel images; OCR maximum ten PDF pages, bounded render size, 30-second subprocess calls and 50,000 text characters; AI maximum 4,096 output tokens. Existing PDF extraction limits also apply.

## 9. Student identity and reconciliation behavior

Register number is primary and university roll secondary. Exact identifiers must agree. Tenant-scoped candidates are fetched in batches. Ambiguous candidates, conflicting secondary identifiers, incompatible existing links and mismatched program/year are blocking conflicts. Another tenant's identity is never exposed/linked; an otherwise valid local roster can remain unregistered.

Unregistered students have roster identities without fake accounts. Pending registration stays unlinked/PENDING_APPROVAL. Approval links a safe existing identity, retains Faculty records and synchronizes student_attendance without duplicates. Active/inactive registration is separate from low attendance and comes from student/account lifecycle.

Conflicts set reconciliation_state=CONFLICT and retain IDs/links/history for administrator resolution. Conflicted links are excluded from legacy joins and new student projection writes. Registration/identity/approval/activity updates trigger reconciliation server-side, including approved identities existing before this extension.

## 10. HOD behavior

Active HOD mappings grant monitoring for authorized department resources according to mapped attendance permissions. Overview, student/profile/session/import history and review use that same scope. HOD alone grants no marking, roster mutation, import upload/correction or commit.

## 11. Class In-Charge behavior

Active mappings permit monitoring across subjects in the authorized program/year/semester/class code. Other classes remain outside scope. Teaching mutations are independently resolved per subject; responsibility cannot take over another teacher's session/import.

## 12. Security

Backend/database contracts cover tenant, class/department, subject/section, role, owner, forged IDs and assignment validity/revocation. Payload schemas forbid actor/tenant/Faculty IDs; AI schemas forbid identity/authority IDs. React renders uploaded values as text.

File checks reject unsafe filenames/control characters/traversal and mismatched MIME/type/signatures where supported. Pillow verifies images. Archives reject unsafe/duplicate paths and excessive expansion; rows/columns/cell references/text are bounded. OCR uses fixed temporary names, argument arrays, shell=False, timeouts and cleanup. Exports neutralize formula prefixes. No public raw-file/R2/internal path is exposed.

Identity/resource queries are tenant-bound; records are fetched only for exact authorized sessions. Legacy mirrors are deduplicated. Passing tests are not a claim of an external penetration test.

## 13. Audit logging

The existing append-only admin_audit_log records roster changes, session creation/marking/correction, import creation/review/commit and identity reconciliation. Core session/import audits occur in the same transaction as mutations. Failed writes cannot leave partial success audits. Actors/tenants/resources are server-derived; lifecycle/count/status metadata excludes passwords, tokens and raw files.

## 14. Frontend implementation

The existing College AI dark Faculty shell supports Overview, Mark Attendance, Students, Upload/Import and Import History. It includes six academic selectors, recorded metrics, registration/attendance labels, search/filter/sort/25-row table pagination, low-attendance monitoring, subject profiles/history, date-based individual/bulk marking and owner corrections.

Review shows values and separates valid/warning/error/conflict/duplicate issues with safe corrections. Imported reviews are read-only with an accurate completion label. OCR/AI consent discloses possible token cost; success refreshes recorded data. History shows uploader ID, filename/import ID, timestamps/counts/errors/status within selected subject/class context. Session/trend reports use actual records.

Loading, empty/no authorized scope, insufficient data, permission/revocation, extraction/validation/network errors and success states are implemented. Monitoring disables mutation. Responsive grids and scrollable tables reuse existing components. Modals support focus management, Escape, Tab trapping and focus restoration. No demo students/attendance were added.

## 15. Backend tests

Final complete tests package: **2,873 passed, 27 skipped, 6 warnings**, 51.70 seconds. No failed tests were omitted; existing skips remain visible.

Attendance coverage includes identifier agreement/ambiguity/tenant matching, pending/unregistered states, first-semester rules, registration-state protection, malformed/formula/malicious files, headers/limits/MIME/signatures, XLSX variants, missing OCR, deterministic extraction without AI, invalid AI schemas, server-derived RPC arguments, forged metadata, legacy deduplication, statistics, pagination and API denials. Existing responsibility tests cover teaching, HOD/Class In-Charge, class/department/tenant boundaries and revocation.

Five existing regression test modules had stale external-boundary mocks: role tests mocked only basic student lookup although current endpoints use academic/approval projections; unknown-institution login lacked a database mock; general chat lacked a provider mock. A full run showed **11 failures, 2,862 passed, 27 skipped** due to external DNS/provider dependencies. Three diagnostic tests subsequently passed in isolation, confirming intermittent external dependency. The mocks were corrected to the actual boundaries with all assertions retained and provider/institution call assertions added. Production auth/registration/chat behavior was not changed. The subsequent complete suite passed as stated.

## 16. Frontend tests

Final complete suite: **70 files, 582 passed**, 193.31 seconds. Attendance has **20 passing interaction tests** for recorded statistics/selectors/no scope/table/profile/history, marking/bulk/deselection, read-only monitoring, denied/revoked scopes and refresh, multi-page roster loading, review correction/issues, AI consent/errors/success, completed read-only review and keyboard focus. Existing portal/regression tests remain.

An added completed-review test initially failed because read-only review reused saving state and displayed “Importing…”. Separating read-only from saving fixed it; focused and complete suites then passed. No test was deleted/weakened.

## 17. Build, type and static checks

npx.cmd tsc -b passed. npm.cmd run build passed TypeScript/Vite. Vite reports a main-bundle-size warning: approximately 604 kB before gzip, 153.52 kB gzip.

Targeted Ruff passed for changed attendance API/schema/services/tests, excluding B008 for the existing FastAPI dependency-default convention. Python app compilation passed. pglast parsed all 34 migrations and both database-contract files; the concurrency script compiled. git diff --check passed. No separate whole-project Python type-checker/Pylance or browser visual verification is claimed.

## 18. Migration verification

**Actual execution: PASS.** A fresh local Docker Desktop container used the cached Supabase public.ecr.aws/supabase/postgres:17.6.1.166 image. The verifier replayed **all 34 migrations**, executed responsibility and attendance rollback-only contracts, then concurrent-write tests. It published no ports, mounted no project/production volume and removed its container afterward. No remote application database was migrated.

Attendance contracts executed stage → reviewed replacement → commit, unregistered roster persistence, duplicate denial, tenant/scope/monitoring denial, co-teacher owner denial/correction, failed-mark rollback, pending/approved/inactive registration, register/roll matches, historical synchronization, already-linked deduplication, conflicts preserving history, failed-import rollback and audit presence. Responsibility contracts also passed.

Actual concurrency verified: two commits of one import produce one success/roster/session/commit audit; parallel same-owner marks retain a unique session and correct records; assignment revocation while a mutation waits is rechecked and denied.

Initial replay exposed the permissions-key mismatch; runtime tests exposed an existing polymorphic trigger referencing import-row fields that do not exist. Both were fixed and replayed successfully. The verifier also now waits for final PostgreSQL readiness after the image's temporary initialization server.

## 19. Known limitations

- Scanned files require Tesseract (tesseract) and scanned PDFs also require Poppler (pdftoppm) on server PATH. These binaries are unavailable here. Adapter/consent/schema paths were tested with mocked OCR/provider outputs; live scanned OCR and live attendance AI generation were **not verified**. Missing OCR returns actionable OCR_UNAVAILABLE (503). AI requires existing OpenRouter key/model settings.
- Summary-only imports are provenance, so recorded metrics stay empty until dated statuses exist.
- Frontend loads authorized student pages in 500-row batches and renders 25 rows. Backend reporting aggregates an authorized section in memory; SQL aggregation/filtering is advisable for much larger datasets.
- Imports/submissions are limited to 500 rows. Large classes can mark subsequent roster pages; large imports must be split.
- Conflicts are visible and do not auto-merge. A dedicated administrator resolution UI remains a future extension.
- Import history displays uploader UUID, with subject/class context in the selected page breadcrumb, rather than fetching a new private Faculty-name directory.
- Existing architecture has no safe import rollback workflow; none was invented. Historical Faculty roster deletion is blocked.
- No production tenant walkthrough/browser screenshot audit was performed. Vite bundle warning, existing backend warnings and skips remain.

## 20. Exact commands and actual results

Backend PowerShell (create the temporary directory if rerunning after cleanup):

    $env:DEBUG='true'
    $env:ENVIRONMENT='testing'
    $env:TEMP='F:\Git Project\CollegeAIChatbot\backend\.attendance-test-temp'
    $env:TMP=$env:TEMP
    .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests

Actual final result: **2,873 passed, 27 skipped, 6 warnings**. Output was redirected to backend/attendance-backend-tests-final.log. Host DEBUG is inherited as release, which is not boolean, so it was explicitly overridden. An earlier DEBUG=false run produced two existing conversational-RAG diagnostic failures; DEBUG=true in test mode satisfies their expected diagnostics.

Frontend PowerShell:

    npm.cmd test -- --run
    npx.cmd tsc -b
    npm.cmd run build

Actual: **70 files/582 tests passed; TypeScript passed; build passed with bundle warning**. Evidence: frontend/attendance-frontend-tests-final.log and frontend/attendance-build-final.log.

Backend static checks:

    .\.venv\Scripts\python.exe -m ruff check --ignore B008 app/api/faculty.py app/schemas/faculty_attendance.py app/services/faculty_attendance.py app/services/faculty_attendance_reporting.py app/services/faculty_attendance_extraction.py tests/test_faculty_attendance_imports.py tests/test_faculty_attendance_workflow.py
    .\.venv\Scripts\python.exe -m compileall -q app
    @'
    from pathlib import Path
    from pglast import parse_sql
    import py_compile
    root = Path.cwd().parent
    files = sorted((root / 'supabase/migrations').glob('*.sql'))
    for file in files:
        parse_sql(file.read_text(encoding='utf-8-sig'))
    for file in (root / 'scripts/validation').glob('faculty_*_database.sql'):
        parse_sql(file.read_text(encoding='utf-8-sig'))
    py_compile.compile(str(root / 'scripts/validation/faculty_attendance_concurrency.py'), doraise=True)
    print(f'PASS: {len(files)} migrations and both database contract files parsed; concurrency script compiled')
    '@ | .\.venv\Scripts\python.exe -

Actual: **targeted Ruff passed; app compilation passed; 34 migrations/both fixtures parsed; concurrency script compiled**. Ruff/pglast were installed as local verification tools, not runtime dependencies. Strip the Markdown indentation when copying the PowerShell here-string command.

Repository root PowerShell, with local Docker Desktop:

    & '.\scripts\validation\verify_faculty_attendance_database.ps1'
    git diff --check

Actual: **DATABASE PASS: 34 migrations replayed; responsibility, attendance and concurrency contracts passed**; diff check passed. Evidence: attendance-database-verification-final.log. PostgreSQL NOTICE messages are expected stderr; every command's exit status is checked. The runner requires a fresh fixed verification-container name and the local engine, and cleans up only its created container. Logs are ignored verification artifacts.

uv lock succeeded. Environment resync encountered the running user server's locked start.exe; dependencies were installed through uv pip install and checks ran through the existing .venv without stopping the user's server.

## 21. Remaining blockers

No blocker remains for deterministic attendance implementation or disposable migration/concurrency verification. Pending migration application and OCR binaries/provider configuration remain deployment steps. Live OCR/provider acceptance verification remains outstanding and distinct from tested implementation. No deployment, publishing, commit or remote database migration was requested/performed.

## 22. Future extensions

Move large-section aggregation/filtering into SQL; add an administrator conflict-resolution workflow; add deployment-level scanned/provider acceptance fixtures and optional uploader-name enrichment; split the frontend bundle through established routing conventions. Preserve central authorization, safe identities, transactional audit and the 75% monitoring semantics.
