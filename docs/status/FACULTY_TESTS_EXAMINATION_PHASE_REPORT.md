# Faculty Tests & Examination Management

Verified on 7 October 2026. Existing uncommitted responsibility and attendance work was retained.

## 1. Status

**IMPLEMENTATION STATUS: PASS**

**DATABASE VERIFICATION: PASS**

Faculty can create and schedule authorized assessments, complete them, enter or import marks, review and submit marks, publish results, lock results and make explicit audited corrections after locking. HOD and Class In-Charge monitoring remains separate from teaching mutation authority. Students see their own safely linked published results through the existing Student result experience.

Final complete suites: **2,986 backend tests passed, 27 skipped, 6 warnings**; **71 frontend files and 612 tests passed**. TypeScript, production build, targeted Ruff, Python compilation, SQL parsing, complete disposable migration replay, database contracts and actual concurrency checks passed. This verifies implementation and a disposable database; it does not claim a production deployment or a production tenant/browser acceptance walkthrough.

## 2. Architecture audit

The preimplementation audit is recorded in [FACULTY_TESTS_EXAMINATION_ARCHITECTURE_BASELINE.md](FACULTY_TESTS_EXAMINATION_ARCHITECTURE_BASELINE.md). Repository-wide searches and reads covered existing test/result migrations, Phase 6.8 result services/repositories/APIs, TestResultsManager, ResultsManager, Faculty and Student pages, academic hierarchy, offerings and sections, assignments, responsibilities, central authorization, attendance rosters/reconciliation, imports/upload/security, private storage/R2, audit, pagination and tests.

Existing `test_results` stored per-student scores. `student_results` and `student_result_items` stored semester summaries. There was no shared scheduled assessment entity or timetable engine. Faculty Results was a placeholder. The existing academic hierarchy, identity model and permission vocabulary could support this workflow without another result or enrollment system.

Before the new migration, the existing **34 migrations** were actually replayed in a clean disposable Docker database, with existing responsibility/attendance contracts and attendance concurrency checks passing. Evidence: `attendance-database-baseline-examination.log`.

## 3. Existing test/result systems reused

- Existing `test_results` stores workflow scores as well as legacy scores; historical IDs and marks are preserved.
- Existing semester results, grading fields, ResultsManager and TestResultsManager retain their established functions. This phase does not synthesize semester grades, GPA or consolidated results from tests.
- Existing attendance rosters, student identifiers, approval/lifecycle state and reconciliation provide assessment identities, including unregistered students.
- Existing `faculty_responsibilities.authorize_section`, `authorization.effective_authorization`, Faculty context and teaching assignment model resolve authority.
- Existing private attendance import/staging tables, bounded spreadsheet readers and upload validation support marks review.
- Existing append-only `admin_audit_log`, paginated repository helpers, API conventions, authentication, FacultyShell, Student shell and dark portal components are reused.

No second student, roster, section, subject, result, authentication, permission, assignment, storage or audit system was introduced. No core role or runtime dependency was added.

## 4. Conceptual model

The model is institution/department/program -> academic year/semester -> existing course offering and subject-specific section -> assessment -> existing roster-backed test result.

An assessment stores its tenant and section anchor. Subject, offering, program, academic year and semester are derived through the existing section relationship. Server/database guards validate the active academic chain. Class monitoring and overlap checks group the existing program/year/semester/section code across subjects.

Assessment metadata includes title, configurable type, instructions, maximum/passing marks, date, optional start/end time and duration, lifecycle, marks state, optimistic version, actors and timestamps. `test_types` is a small extensible configuration catalog, seeded with existing types and class test/model/practical options. Adding a type does not require a new assessment table.

## 5. Database changes

[20261013000000_faculty_tests_examination.sql](../../supabase/migrations/20261013000000_faculty_tests_examination.sql) adds shared `faculty_tests` metadata and the `test_types` catalog. It extends existing `test_results` with assessment/roster references, explicit mark status and private teacher remarks, and permits safe roster-only identities. Legacy student linkage and legacy uniqueness remain enforced for legacy rows. New assessment/roster and safely linked assessment/student uniqueness prevent duplicate workflow results.

Existing private `faculty_attendance_imports` gains nullable `test_id`; a null value retains attendance semantics. Its existing staging rows store reviewed marks. Guards prevent either workflow from committing the other's imports.

Constraints and triggers protect score/status consistency, historical roster references, academic context, publication projection and immutable workflow identity. Historical assessment result deletion and roster deletion with assessment history are denied. The backend returns a conflict if a concurrent historical write races roster deletion.

Atomic metadata, marks, lifecycle, staging, review and commit RPCs enforce live teaching authority, ownership, version/timestamp checks and transactional audits. The existing attendance transaction guard is generalized for its existing `attendance.manage` permission and `results.manage`; the original attendance signature delegates to it. Responsibility definitions gain explicit `results.read` mappings for HOD/Class In-Charge only.

New metadata/catalog tables use private RLS. Anonymous/authenticated direct assessment/result access and mutation RPC execution are revoked; trusted backend service-role entrypoints provide access. The legacy result trigger retains its legacy branch and derives all workflow result context from authoritative relationships. No historical migration was edited for this phase; prior pending migrations remain in the replay chain.

## 6. API changes

Paths are under `/api/v1/faculty/tests`, using the existing authenticated Faculty dependency and API error conventions.

| Method/path | Behavior |
| --- | --- |
| GET `/resources` | Authorized academic selectors with independent teaching capability |
| GET `/types` | Active configurable assessment types |
| GET `/sections/{section_id}` | Paginated tests and recorded scope statistics |
| POST `/sections/{section_id}` | Create an authorized draft |
| GET `/{test_id}` | Authorized metadata, existing roster, marks and review statistics |
| PATCH `/{test_id}` | Version-checked owner metadata update |
| POST `/{test_id}/transition` | Explicit server-validated lifecycle/marks action |
| PUT `/{test_id}/marks` | Atomic bounded marks batch |
| POST `/{test_id}/corrections` | Explicit locked correction with reason and previous/new audit values |
| POST `/{test_id}/imports` | Bounded deterministic upload and staging |
| GET `/imports/{import_id}` | Authorized review and row issues |
| PATCH `/imports/{import_id}/rows/{number}` | Owner correction and full revalidation |
| POST `/imports/{import_id}/commit` | Fresh validation and atomic version/timestamp-checked commit |
| GET `/{test_id}/history` | Authorized import and lifecycle/marks audit history |

Business logic resides in the service layer and database transactions. Existing Student results endpoints receive a safe status/outcome projection. No redundant endpoint set or admin portal was created.

## 7. Authorization

Reads repeat existing active account, institution, Faculty role, permission, academic chain and exact resource-scope checks. Resource selectors contain authorized sections only. Every detail, marks, history and import review operation resolves its own backend scope.

Mutation requires a valid exact subject/section teaching assignment and `results.manage`. Updates, marks, lifecycle and imports additionally require the assessment owner; import changes require its uploader. A co-teacher may read an authorized assessment but cannot take over its owner mutations. HOD/Class In-Charge responsibility is excluded from mutation resolution.

Actor and tenant come from authenticated context. Payload models forbid authority/identity override fields. The database rechecks active accounts, permissions, academic relationships and assignment validity after acquiring transaction locks. Expired or revoked teaching scope fails closed. The frontend refreshes capabilities on context/focus changes and clears stale private state.

## 8. Test lifecycle

The enforced lifecycle is `DRAFT -> SCHEDULED -> ONGOING -> COMPLETED -> PUBLISHED -> LOCKED`; completion may proceed directly from scheduled. Cancellation is available before publication. The frontend sends named actions rather than arbitrary state values.

Marks have independent `DRAFT` and `SUBMITTED` states. Submission requires a complete valid active roster. Submitted marks may be explicitly returned to draft before publication. Publishing requires completed/submitted marks and fresh roster/identity validation. Locking requires published results.

Metadata changes are restricted to owner draft/scheduled assessments before any marks exist. A scheduled date is required beyond draft/cancelled. Dates must fall within the existing semester and academic year; times must be paired and ordered. Duplicate titles/dates in the same section and concrete time overlaps for the same existing class context are rejected atomically.

## 9. Marks workflow

Authorized existing rosters show register number, optional university roll, name, maximum marks, score, explicit mark status, percentage/outcome and private remarks. Unregistered/pending identities remain on the same roster without fake accounts. Inactive historical entries remain available for monitoring.

`present` requires a finite score from zero through the assessment maximum, with at most two decimal places. `absent`, `exempt`, `not_attempted` and `missing` require an empty score. Zero is a real present score. Missing is explicit and blocks submission/publication; it is never converted to zero.

One request saves 1-500 distinct changed roster rows atomically. Every roster ID, identity agreement, tenant, section, status, score and ownership is checked again in the database. A bad row rolls back the entire batch and its success audits. Larger classes can save successive batches.

Review reports actual total/entered/missing/absent/exempt/not-attempted/conflicting students, pass/fail where configured and the mean percentage of present scores. Percentage is scored/max * 100; non-present statuses do not contribute synthetic zeroes. No new grade policy was invented.

## 10. Import workflow

Upload -> validate -> review/correct -> explicit import uses deterministic CSV/XLSX/binary XLS. The shared attendance parser and filename/MIME/signature/archive checks are reused. The values-only XLS path additionally rejects BIFF formula/array/shared-formula records before using cached cells. Normal spreadsheets invoke neither AI nor OCR.

Required identity/status columns are `register_number` and `mark_status`; present rows require `scored_marks`. Optional columns are `university_roll_number` and `remarks`. Unknown columns, including authority IDs, are rejected. Identifiers resolve only against the existing authorized roster; unknown/outside-section students and conflicting identifiers cannot be imported.

Review separately displays valid rows, warnings, errors, conflicts and duplicates. Unregistered/pending valid roster entries carry a warning and preserve their identity. Missing marks, malformed/out-of-range/over-precision scores, invalid statuses, absent-with-score, duplicate identities and formulas block commit.

Correction revalidates the whole staging set. Final commit validates stored raw rows against current server roster/maxima, then the transaction repeats identity/lifecycle/version/score checks. Upload creates no marks before commit. Completed imports are read-only and cannot commit again. Private staging retains provenance; raw files are not uploaded to R2 or exposed publicly.

Limits reuse attendance infrastructure: 10 MB upload, 500 rows, 20 columns and 50 MB expanded XLSX. Inline/bulk edits and imports are bounded to 500 rows per transaction.

## 11. Result publication/locking

Publication is explicit and requires valid submitted marks. Ordinary editing stops after submission and remains denied for published/locked assessments. Students receive published results only after safe linkage. No automatic publication occurs on save/import.

A locked correction is a dedicated authorized owner workflow requiring a reason of 10-1,000 characters. It records previous/new scores, mark status and remarks, actor, tenant, roster/resource and reason in the existing audit transaction. The assessment stays locked. Normal editing, direct legacy updates, conversion to a legacy row and historical deletion cannot bypass the workflow.

## 12. Student result visibility

The existing Student result service and `ResultsDetail` show subject, assessment title/type/date, score/maximum, percentage and status/outcome. An absent label remains distinct from present zero. Existing semester result presentation is retained.

Queries and projection restrict results to the authenticated linked student, tenant and published row state. Workflow parent state must be published/locked. Database projection additionally requires an approved active compatible student, an active safe roster link and no reconciliation conflict. Teacher remarks, actor IDs, internal workflow metadata and other students' marks are absent from the safe Student response.

Existing attendance reconciliation links later approved registration without changing marks or IDs. Pending/unregistered students remain unlinked; withdrawn approval, inactivity, conflicting identifiers or incompatible program/year hide the result while preserving history. Existing result visibility behavior for legacy records remains intact.

## 13. HOD behavior

Active HOD mappings grant `results.read` for the authorized department through the central responsibility resolver. HOD can select department resources and monitor schedules, completion, mark entry, review, publication, results and history. This does not grant University Admin authority or assessment mutation.

A separate valid teaching assignment and owner relationship can independently authorize the HOD's own teaching work. Other departments remain outside its responsibility scope.

## 14. Class In-Charge behavior

Active Class In-Charge mappings grant monitoring across subjects for the existing authorized program/year/semester/class code. Other classes remain excluded. Schedule/result/mark-entry states and review/history use the same scope.

This responsibility cannot create or change another teacher's assessment, submit their marks, publish or lock it. Any teaching mutation must independently satisfy the exact assignment, permission and ownership rules.

## 15. Security

All resource operations are tenant-bound. Unknown/foreign assessment/import IDs use safe not-found behavior; public errors do not expose SQL/schema details. Client payloads cannot assign institution, actor, owner, student or academic relationships. Existing rosters and safe matching determine identity; ambiguous or incompatible links fail closed.

Private RLS and revoked table/RPC privileges prevent anonymous/authenticated direct database bypass. Workflow triggers protect identities, marks/history and publication projection even through legacy result paths. Trusted mutation RPCs enforce the same live authority and owner invariants inside the transaction.

Upload validation rejects unsafe names/control characters/traversal, unsupported MIME/signatures, malformed spreadsheets, unsafe/duplicate archive paths, excessive expansion/cell references/rows/columns and formulas. React renders uploaded values and audit content as text. Import reading is bounded and parsing runs in a thread pool. No provider, public raw file URL or storage secret is exposed.

Passing tests and local ACL checks are not an external penetration-test claim.

## 16. IDOR/tenant testing

Backend tests exercise forged authority fields, unknown/foreign assessment IDs, independently denied API routes, exact teaching subject/section/tenant boundaries, revoked assignments, HOD department scope, Class In-Charge class scope, monitoring-only capabilities, foreign roster identities and safe Student projection. Existing responsibility regression tests remain part of the complete suite.

Actual database contracts exercise tenant/scope denial, co-teacher owner denial, responsibility mutation denial, stale version rejection, outside-roster/identity denial, unpublished/pending/inactive/conflicted result projection, history protection and failed batch/import rollback. Catalog/table/RPC privilege assertions and actual `SET LOCAL ROLE authenticated` direct assessment/result read denials passed. Anonymous direct privileges are also checked.

## 17. Audit logging

The existing append-only `admin_audit_log` records create/update, schedule/start/complete/cancel, marks saves/corrections, submission/return, publication/lock and import creation/review/commit. Actors, institutions and resource IDs are server-derived. Lifecycle audits retain before/after state; marks audits retain previous/new values; locked corrections include their reason.

Audits and changes commit in one transaction. Failed writes cannot leave partial successful records or success audits. Registration reconciliation continues to use the existing audited identity system. History does not expose passwords, tokens, raw files or provider secrets.

## 18. Frontend implementation

The existing dark FacultyShell Results entry opens Tests & Assessments. Its views are Overview, My Tests, Create Test, Enter Marks, Results, Import and History. Existing six academic selectors and real recorded metrics are reused; navigation/capabilities come from backend scopes. No demo assessments/students/counts were added.

The structured form supports draft creation, scheduling, owner metadata changes and clear numeric/date validation. Tests paginate at 50; searchable student tables render 25 rows. Marks support inline statuses/scores/remarks, Enter-to-next-score navigation, one batch save, visible errors and explicit dirty state. Saving 500 changed rows is required before changing more students.

Result review shows completeness, conflicts, outcomes and actual class averages, with explicit submit/publish/lock actions. Controlled corrections disclose audit/history and require a reason. Import review has safe text rendering, issues, correction/revalidation and a completed read-only state. History shows existing import and audit records.

Unsaved marks trigger in-workspace, Faculty-shell and browser navigation protection. Busy writes disable dependent controls. Context/focus refreshes re-fetch capabilities; context generations prevent old asynchronous responses from restoring stale private data. Revocation clears scope/details. Loading, empty/no authorized scope, read-only monitoring, permission, validation, network and success states are covered. Responsive grids/scrollable tables use existing styling and labeled controls. No production browser screenshot audit is claimed.

## 19. Backend tests

Final **complete** backend suite: **2,986 passed, 27 skipped, 6 warnings**, 80.79 seconds. Evidence: `backend/examination-backend-tests-final.log`. Existing skipped tests and warnings remain visible; no failing module was excluded.

The new assessment module contributes **113 passing tests** covering schema forgery, decimal/absence/zero semantics, batch/correction contracts, exact teaching and responsibility boundaries, independent API denial, tenant/ownership containment, server-derived RPC arguments, safe error mapping, deterministic file handling/formula denial, identity conflict annotation, stored-row commit revalidation, Student safe visibility and roster deletion/history races. Lifecycle, transactional rollback/audit, publication/locking/reconciliation and concurrent database behavior additionally run against actual PostgreSQL contracts.

An earlier complete backend run also passed (2,984 passed before the two final roster-deletion tests). Production auth/registration/chat behavior was not changed for this phase. The test environment overrides inherited nonboolean `DEBUG=release` with `DEBUG=true`, matching existing diagnostic tests.

## 20. Frontend tests

Final **complete** frontend suite: **71 files passed, 612 tests passed**, 210.31 seconds. Evidence: `frontend/examination-frontend-tests-final.log`. The assessment module contains **27 passing interaction tests** for dashboard/selectors, creation/schedule, marks/bulk/keyboard/pagination/validation, dirty protection, review/submission/publication/lock/correction, monitoring/revocation/context refresh, import/correction/errors/history and safe text. Existing shell/navigation tests were updated for the implemented Results surface, with additional shell/navigation and Student absent/zero/outcome coverage.

Initial focused assessment tests exposed schedule-button intent and stale context-state problems; production code was corrected and all 27 then passed. An initial complete run had **2 failures and 610 passes**: the added Student test expected a spaced score label while the existing renderer uses `0/100`, and an existing FacultyAssignmentManager loading assertion timed out under concurrent heavy verification. The new expectation was corrected to actual rendering. A subsequent focused run also encountered an existing dashboard loading timeout. Existing assertions/timeouts were retained; the final complete run used two workers without concurrent heavy suites and passed. No test was deleted or weakened.

## 21. TypeScript/build/static checks

Final `npx.cmd tsc -b` passed. Final `npm.cmd run build` passed TypeScript and Vite, transforming 2,067 modules. Main JavaScript is **632.90 kB**, **160.98 kB gzip**. Vite's chunk-size warning remains; native stderr redirection appears as PowerShell `NativeCommandError` formatting in the log, but the checked process exit code is zero and Vite completed successfully. Evidence: `frontend/examination-build-final.log`.

Targeted Ruff passed for assessment API/schema/service/tests and changed integration files. `B008` is excluded for the existing FastAPI dependency-default convention; `BLE001` is excluded for the existing optional-label fallback and safe historical-FK race error mapping. Python application compilation passed.

`pglast` parsed **all 35 migrations and all three Faculty database contract fixtures**. Both Faculty concurrency scripts compiled. `git diff --check` passed; Git emits existing CRLF conversion warnings. Verification tooling was already available locally and is not a new runtime dependency. No separate whole-project Python type checker or Pylance verification is claimed.

## 22. Migration verification

**Actual execution: PASS.** After the successful 34-migration baseline, the final verifier replayed **all 35 migrations** from a clean local Docker Desktop database using the cached Supabase `public.ecr.aws/supabase/postgres:17.6.1.166` image. It executed responsibility, attendance and assessment rollback-only database contracts, privilege/RLS checks and both concurrency scripts.

The runner permits only the local `desktop-linux`/`docker-desktop` engine, refuses an existing fixed verification-container name, publishes no ports, mounts no project/production volumes and cleans only its created container. It waits for final PostgreSQL readiness after image bootstrap. No remote application database was accessed or migrated. Evidence: `examination-database-verification-final.log`.

Assessment contracts execute metadata/date/type/duplicate validation, complete lifecycle, valid zero/absence/bulk save, bad-row rollback with no success audit, owner/co-teacher/tenant/version denial, import stage/review/correction/commit and failed commit rollback, missing/fresh conflicting identity denial, publication/locking, ordinary/direct locked-update and deletion denial, controlled correction with previous/new audit and reason, pending/approved/withdrawn/inactive/conflicted registration projection, historical preservation and actual authenticated direct-read denial. Existing attendance and responsibility contracts continue to pass.

Initial contract execution exposed a fixture missing the established trusted service-role context; the fixture was corrected. A later real run exposed a PL/pgSQL loop-variable/table-alias ambiguity in publication validation; the variable was renamed. Both were replayed successfully. The final exact migration, including corrected-mark remarks in audit before/after data, was replayed again successfully.

## 23. Concurrency verification

**Actual execution: PASS.** The disposable PostgreSQL assessment script verifies concurrent duplicate creation, co-teacher versus owner changes, simultaneous submission, simultaneous publication, simultaneous locking, marks updates versus locking, double commit of one import and assignment revocation while a mutation waits.

Transactions use the existing tenant attendance/reconciliation advisory mutex, assessment/import row locks, optimistic versions and live assignment/permission/academic row locks. Losing stale operations fail without duplicate assessments/results/import-commit audits or partial marks. Revocation while waiting is rechecked after the lock and denied.

The existing attendance concurrency script also passed, covering one successful import commit, same-owner session marking uniqueness, atomic audit and revocation after waiting. These are real separate PostgreSQL writes, not only mocked frontend/service tests.

## 24. Known limitations

- Pending migrations have not been applied to a remote/production tenant; deployment remains a separate step. Prior pending migrations, including the earlier-timestamp permission-key convergence migration, must be accounted for when applying the chain.
- No production tenant acceptance walkthrough, browser screenshot review or external penetration test was performed. Frontend behavior is verified by interaction/regression tests and compilation/build.
- Imports support deterministic CSV/XLSX/XLS only. No PDF/image/OCR/AI extraction was introduced or required for this phase.
- Imports and individual marks transactions are limited to 500 rows. Larger classes must save successive batches/split imports. Existing parsers enforce file/expansion limits.
- Reporting/marks/identity/history use complete paginated repository reads and in-memory aggregation within an authorized section. SQL aggregation and server pagination of large history/rosters are future scale improvements.
- Scheduling covers the existing academic period, duplicate metadata and concrete same-class time overlaps. There is no room/timetable/timezone engine; times are existing local wall-time values and upcoming counts use the UTC current date.
- The current authorized roster is reused rather than creating a frozen exam enrollment snapshot. Historical marks are retained and protected; later roster changes affect current completeness review.
- Corrections require the same active assigned owner. No administrator takeover, academic reassignment policy or new coordinator role was invented. Conflicted identities remain quarantined for administrator resolution through a future dedicated UI.
- Type catalogs can be extended through trusted configuration, but this phase adds no catalog administration UI. Semester grade/GPA calculation remains the existing separate system.
- History displays uploader/actor UUIDs without adding a private Faculty-name directory. No new public raw-file storage or rollback/delete workflow was introduced.
- Vite's bundle-size warning, the six existing backend warnings and 27 existing skips remain.

## 25. Future extensions

Move large-scope statistics/filtering/history pagination into SQL; add deployment-level tenant/browser acceptance fixtures; extend the existing administrator identity-resolution and academic ownership policy when required; optionally enrich actor labels and route-level bundle splitting through established conventions. Future Exam Coordinator responsibilities should use existing definitions, permission mappings and academic scope. Preserve explicit absence, safe identities, central authorization, atomic audit and historical marks.

## 26. Exact commands and actual results

Backend PowerShell, from `backend` (temporary directory was created for these runs and removed afterward):

```powershell
$env:DEBUG='true'
$env:ENVIRONMENT='testing'
$env:TEMP='F:\Git Project\CollegeAIChatbot\backend\.examination-test-temp'
$env:TMP=$env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests
```

Actual final result: **2,986 passed, 27 skipped, 6 warnings in 80.79 seconds**, exit 0. Full output: `backend/examination-backend-tests-final.log`.

Frontend PowerShell, from `frontend`:

```powershell
npm.cmd test -- --run --maxWorkers=2
npx.cmd tsc -b
npm.cmd run build
```

Actual final results: **71 files/612 tests passed in 210.31 seconds; TypeScript passed; build passed in 16.71 seconds with the bundle warning**, all exit 0. Evidence: `frontend/examination-frontend-tests-final.log`, `frontend/examination-build-final.log`.

Backend static checks, from `backend`:

```powershell
.\.venv\Scripts\python.exe -m ruff check --ignore B008,BLE001 app/api/faculty_tests.py app/api/faculty.py app/schemas/faculty_tests.py app/schemas/student_results.py app/repositories/admin_academics.py app/services/faculty_tests.py app/services/faculty_attendance.py app/services/student_results.py tests/test_faculty_tests.py
.\.venv\Scripts\python.exe -m compileall -q app
@'
from pathlib import Path
from pglast import parse_sql
import py_compile
root = Path.cwd().parent
files = sorted((root / 'supabase/migrations').glob('*.sql'))
for file in files:
    parse_sql(file.read_text(encoding='utf-8-sig'))
fixtures = sorted((root / 'scripts/validation').glob('faculty_*_database.sql'))
for file in fixtures:
    parse_sql(file.read_text(encoding='utf-8-sig'))
scripts = sorted((root / 'scripts/validation').glob('faculty_*_concurrency.py'))
for file in scripts:
    py_compile.compile(str(file), doraise=True)
print(f'PASS: {len(files)} migrations, {len(fixtures)} contract fixtures and {len(scripts)} concurrency scripts parsed/compiled')
'@ | .\.venv\Scripts\python.exe -
```

Actual results: **Ruff passed; application compiled; 35 migrations/three contract fixtures parsed; two concurrency scripts compiled**, exit 0.

Repository-root PowerShell, with local Docker Desktop:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/validation/verify_faculty_tests_database.ps1
git diff --check
```

Actual result: **DATABASE PASS: 35 migrations replayed; responsibility, attendance, assessment and concurrency contracts passed**, exit 0. Final log: `examination-database-verification-final.log`. Expected PostgreSQL NOTICE output is stderr; command exit status is checked. Diff check passed. The PowerShell execution-policy flag is needed for this local script environment.

Logs are ignored local verification artifacts. The user's running server was not stopped. No deployment, publishing, commit or remote database migration was requested or performed.
