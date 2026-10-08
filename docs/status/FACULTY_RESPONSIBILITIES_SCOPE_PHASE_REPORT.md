# Faculty responsibilities, assignments and academic scope

Date: 7 October 2026. Status: PASS.

MIGRATION VERIFICATION: PASS. Clean local Supabase migration replay, transactional database assertions, catalog/privilege checks and five real concurrent PostgreSQL scenarios passed. The suite-level frontend timing failure was resolved by bounding isolated Vitest workers. SQL lint continues to report unrelated pre-existing issues, with no new phase issues. No remote database was changed.

## 1. Architecture audit before implementation

The existing architecture was inspected before adding tables. The relevant baseline is `20250717000000_reconstructed_pre_phase_3_6_baseline.sql`, the academic/student migrations, the Phase 6.13 tenant migration, Phase 7.12 platform identity, Phase 8 permission catalogue, Phase 8.1 scoped RBAC/faculty assignments, and Phase 10 faculty attendance migration.

Existing model:

- `roles`, `user_roles`, `permissions`, and `role_permissions` provide the RBAC foundation. The production identity projection resolves active database permissions; test-only role defaults do not resurrect revoked production grants.
- `user_permission_grants` provides narrowly delegated, institution-bound Staff capabilities.
- `faculty_section_assignments` already stores teaching assignments, actor, assignment time and revocation history.
- Sections belong to course offerings. Offerings reference a course, program, semester and academic year. Courses and programs have departments; departments and academic years belong to institutions. `program_courses` allows a program to include subjects owned by other departments.
- The five core role names are `super_admin`, `admin`, `faculty`, `staff`, and `student`. `admin` is the stored name for University Admin; presentation aliases do not add another role.
- Tenant resolution, account/institution lifecycle guards, server permission dependencies, student ownership checks, and the append-only `admin_audit_log` already exist.
- Attendance already has course-specific section rosters, sessions, records, staged imports and student attendance synchronization.
- AuthProvider reads `/auth/me`, preserves the server role, and selects the existing Faculty shell. Faculty assignment management and permission-aware navigation already exist. Several Faculty pages intentionally remain roadmap placeholders.

Reuse: all those entities, identity resolution, permission matching, assignment IDs, Staff grants, ownership and audit infrastructure.

Extension: teaching validity/state, data-defined responsibility definitions and permission mappings, scoped appointments, centralized academic authorization, admin lifecycle controls and Faculty monitoring views.

Migration strategy: add teaching columns in place, backfill `start_at = assigned_at`, preserve every identifier and history row, and create empty responsibility tables. No legacy teaching row is converted into HOD or Class In-Charge authority. No existing academic/student entity is duplicated.

Proposed authorization flow: verified identity → current database roles/permissions → active institution dependency → database-derived resource context → valid teaching/responsibility scope → permission and optional ownership checks → allow or deny. Implementation followed this audit; no parallel authentication/RBAC system was introduced.

## 2. Conceptual model and core roles

Authorization combines core role, assignment/position, academic scope, mapped permission and time validity. Teacher means Faculty. HOD and Class In-Charge are responsibility definitions held by Faculty; neither is inserted into `roles` or used to select another shell.

Existing role precedence and all five roles remain intact. Super Admin authority continues to require a platform grant. University Admin authority continues to require the authenticated institution grant.

## 3. Teaching assignments

`faculty_section_assignments` remains the teaching source of truth. A section is already subject-specific through its course offering; teaching is consequently restricted to that exact section/course offering. Additional columns are `start_at`, `end_at`, `is_active`, and `updated_at`.

Existing `assigned_at` and `assigned_by` are the retained creation-time and creator fields, rather than duplicated `created_at`/`created_by` columns. Existing `revoked_at`/`revoked_by` remain authoritative. Old IDs and audit events are preserved.

Legacy create/revoke API and RPC signatures remain functional. Creation can optionally specify validity. An atomic create-with-validity RPC creates/updates the teaching record and audits both actions in one transaction. Validity/enabled-state edits preserve the assignment ID. To change the teaching subject/section, revoke the old assignment and create the new assignment; existing attendance ownership is not reassociated.

The existing rule of one unrevoked assignment for a Faculty/section pair remains. Multiple teachers may teach a subject as allowed by the existing schema; this phase does not invent an exclusive-teacher rule. Expired teaching rows can be updated or revoked before replacement.

## 4. Responsibility definitions and appointments

New tables:

| Table | Purpose |
| --- | --- |
| `responsibility_definitions` | Display name, permitted scope levels, active state and exclusivity rule |
| `responsibility_permissions` | References the existing permission catalogue |
| `faculty_responsibilities` | Faculty, institution, type, normalized scope, validity, state, creation/update and revocation metadata |

Initial definitions: HOD with department scope; Class In-Charge with class/section scope. Teaching, HOD and Class In-Charge can coexist without changing a user's role.

Creation and update derive scope relationships in PostgreSQL. Clients cannot supply actor, institution, normalized parent IDs, permission lists, creator or revoker. Updates cannot silently change the target Faculty member or responsibility definition.

## 5. Academic scope and domain decisions

The resolver supports institution, department, program, semester-with-program, class/section and course scope using existing entities. A semester appointment requires a program; it does not widen to every program in the term. Programs, semesters, years, courses, departments and sections must resolve to active, consistent tenant relationships.

The schema has subject-specific sections and no separate cohort/class table. A Class In-Charge appointment selects one existing section as its anchor. Its class key is `(program_id, academic_year_id, semester_id, section code)`. This covers sibling subject sections for that class, including subjects supplied by another department in the same institution. Class membership is not matched by display names, and scope cannot cross academic years, programs, semester IDs, section codes or institutions.

HOD reporting uses the course-owning department, following the existing course → department authorization chain. A program's cross-department elective does not become a course owned by the program's department. Class monitoring can still include that elective through its program/class key.

Safe defaults, explicitly chosen because no prior position-conflict rule existed:

- One HOD per department during overlapping enabled, unrevoked validity periods.
- One Class In-Charge per class during overlapping periods, even when different subject-section anchors are selected.
- One Faculty member may hold responsibilities for several distinct scopes and may combine different responsibility types.
- Adjacent, non-overlapping successor appointments are allowed.
- Co-HOD/co-Class In-Charge is not enabled. A future shared definition can set `exclusive_scope=false` through a trusted migration; duplicate overlapping appointments for the same user/type/scope remain rejected.

Generic GiST exclusion constraints and tenant transaction locks enforce conflicts, including concurrent writes. Runtime concurrency verification is pending.

## 6. Central permission resolution

`app/services/authorization.py` extends the existing authorization service with `assignment_is_active`, `academic_scope_contains`, and `effective_authorization`. The resolver calls the existing server permission matcher; it does not replace role permissions or Staff delegation.

Decision inputs include active core-role grants, account state, tenant, database-derived resource scope, teaching assignment, responsibility definition/mapped permissions, validity, revocation and optional resource ownership. Missing or inconsistent scope denies access.

Teaching permits only relevant academic actions with the existing role permission and an active exact subject-section assignment. Responsibility mappings permit actions only inside their normalized scope. Scoped responsibility grants are **not** added to the unrestricted `effective_permissions` list. Removing a mapped catalogue permission or disabling the definition removes its grant when the server resolves the next request.

New catalogue capabilities are `academic.class.read`, `academic.department.read`, `academic.reports.read`, and `attendance.overview.read`. Assignment management reuses `faculty.assignments.manage`.

## 7. Validity and revocation

All timestamps are timezone-aware. Authorization uses the UTC half-open interval `[start_at, end_at)`; a null end means no scheduled expiry. Future, expired, disabled, revoked and malformed/naive timestamp assignments do not grant access. End is an exact exclusive timestamp, not an implicitly inclusive calendar day. The UI displays local times and explains this boundary.

Responsibility rows store `created_at`, `updated_at`, `created_by`, `revoked_at`, `revoked_by`, `start_at`, `end_at` and `is_active`. Teaching reuses its existing creator/creation fields. Revocation retains history and can revoke a responsibility after its Faculty account or scope was deactivated.

## 8. HOD behavior

HOD receives department academic overview, courses/sections, roster monitoring, attendance/low-attendance reports and active teaching-faculty overview through explicit scoped mappings. Faculty overview additionally requires `faculty.read` and filters active Faculty institution grants and accounts.

HOD receives no user-management, global permission-management, role-management, responsibility-appointment management, attendance-edit or result-edit grant. An HOD with the explicit `faculty.assignments.manage` responsibility mapping may create, update validity for, and revoke teaching assignments only within the HOD's department scope. HOD remains Faculty. Another department or institution is denied.

## 9. Class In-Charge behavior

Class In-Charge receives class subject sections, roster monitoring, attendance overview, low-attendance students and reports across the class key. It cannot read another class or institution. It does not receive Faculty roster or administrative authority merely from its position.

Editing a subject still requires that subject's valid teaching assignment and `attendance.manage`. A Class In-Charge position alone cannot mark attendance, modify rosters or commit another teacher's imports.

## 10. Attendance integration

Faculty attendance writes now use the centralized resolver with `teaching_only=True`. Roster reads use responsibility-aware scoped resolution. Import review/history remains teaching-scoped with `attendance.read`; import commit requires valid teaching edit authority and ownership by the uploading Faculty member.

Monitoring reports read the existing rosters, sessions and records. Percentages use present records divided by all recorded statuses, matching existing student attendance semantics. Students without records have a null percentage and are excluded from low-attendance classification. The initial report threshold is 75%, displayed explicitly; it is a monitoring threshold, not a new enforcement/eligibility policy.

Imported percentage summaries are not converted to session history or used to calculate report percentages. Reports label subject roster entries so a student enrolled in multiple subjects is not presented as several distinct people. Private addresses and raw import metadata are not projected into these reports.

Database reads paginate beyond the REST row cap and filter authorized sections before reading tenant rows. Attendance write payloads serialize UUIDs to strings. The existing student attendance synchronization and academic ownership invariants remain intact.

## 11. Database changes and migration path

Migration: `supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql`.

It adds teaching validity in place, adds responsibility metadata/mappings/appointments, seeds narrow permissions, installs scope/conflict constraints, and creates audited lifecycle RPCs. Existing Phase 8.1 teaching RPC contracts are retained through a permission/self-assignment/academic-scope guard around the original implementation. The original helper is not callable by service-role/API clients directly.

Tables enable RLS and deny `anon`/`authenticated` access. Responsibility mutations also deny direct `service_role` writes; narrowly granted SECURITY DEFINER RPCs perform validation and audit atomically. Definitions/mappings are configured through trusted migrations, not a Faculty or tenant-admin global-permission editor.

No assignment rows are deleted, no IDs are reassigned, no role grants are converted, and no new student/department/program/semester/course/section model is created. The deterministic backfill is `start_at = assigned_at`; legacy open-ended assignments retain their prior availability unless revoked or academically inactive.

## 12. APIs

| API | Behavior |
| --- | --- |
| `GET /auth/me` | Preserves existing identity/permission fields; adds resolved `faculty_context` for production Faculty identities |
| `GET /faculty/context` | Current responsibilities, teaching assignments and scoped presentation capabilities |
| `GET /faculty/responsibilities/{id}/report` | Own valid, authorized responsibility report; no write actions |
| `GET /admin/faculty-responsibilities` | Institution-scoped definitions, candidates, scope options and appointment history |
| `POST /admin/faculty-responsibilities` | Create an audited appointment |
| `PATCH /admin/faculty-responsibilities/{id}` | Update scope, validity or enabled state |
| `DELETE /admin/faculty-responsibilities/{id}` | Revoke and retain history |
| `PATCH /admin/faculty-assignments/{id}` | Update teaching validity/state |
| Existing teaching create/revoke APIs | Preserved; creation optionally accepts explicit validity |
| `GET /faculty/teaching-assignments/management` | Return assignment history and active faculty/section choices limited to the caller's live assignment-management responsibilities |
| `POST /faculty/teaching-assignments/management` | Create an audited teaching assignment after application and database scope checks |
| `PATCH /faculty/teaching-assignments/management/{id}` | Update validity/state for an assignment in the caller's live scope |
| `POST /faculty/teaching-assignments/management/{id}/revoke` | Revoke an assignment in scope while preserving its historical row |
| `/platform/institutions/{institution_id}/faculty-responsibilities` | Super Admin list/create; ID-specific update/revoke |

University Admin tenant comes from authenticated identity, never a body/query tenant. A platform institution path selects a resource; the active Super Admin platform grant and explicit management permission still authorize the request. Platform responsibility management does not grant Super Admin access to student attendance. University Admin retains institution-wide teaching management. Faculty assignment-management API access additionally requires an active Faculty institution grant and a live responsibility with `faculty.assignments.manage`; the selected academic section is checked in the service and again in the transaction.

## 13. Frontend

The existing Admin Faculty assignment manager continues to host institution-wide assignment creation and validity/revocation actions. The Faculty shell adds a Teaching Assignments view only when the server-resolved responsibility context maps `faculty.assignments.manage`. It offers responsibility-scoped section/faculty choices, assignment validity edits, revocation, history/state display and error/success feedback. Teaching creation requires a validity start; local end-before-start validation is a UX guard, with strict server/database validation authoritative.

Faculty profile displays backend-derived positions, teaching subjects, programs/semesters/sections, associated departments and validity. Faculty keeps the same shell. Active scoped capabilities add Class Management and Department views with overview, subject sections, students, attendance, low attendance, reports and authorized Faculty overview. No client role named HOD or Class In-Charge is introduced.

Faculty context refreshes every 30 seconds, on window focus and at known validity boundaries. Local filtering removes expired links at the boundary; authorization remains server-side on every request. Failed/403 context refresh hides scoped views and stale profile assignments. Report failures display the backend error and a retry action. Scope/permission/validity changes remount report queries, avoiding stale report capabilities.

Auth restoration/refresh reuses the unchanged AuthProvider lifecycle and `/auth/me`. Existing Student/Admin/Staff shells and initial uncommitted Faculty attendance/shell work were preserved.

## 14. Security

Request schemas forbid forged tenant, actor, creator, revoker and permission fields. Target Faculty IDs and academic identifiers are resources validated against database relationships. Faculty cannot self-appoint, including when a management permission is maliciously present in an internal test context. Administrators cannot self-assign a Faculty responsibility/teaching duty.

The database independently checks active actor, management permission, exact tenant grant, eligible target Faculty, definition/scope, academic relationships and validity. University Admin cannot edit another institution's appointments. HOD/Class In-Charge cannot appoint another HOD or mutate global permissions. Cross-tenant teaching/position scope fails closed.

Existing user/student ownership checks, tenant guards, Staff permission delegation, role precedence and permission revocation behavior remain in place. The new internal projection adapters validate database row shapes rather than weakening type checking.

## 15. Audit logging

All lifecycle RPCs insert into the existing append-only `admin_audit_log` in the same transaction as the change. Responsibility create/update/revoke events contain server actor/institution plus target and normalized scope in before/after snapshots. Validity, scope and enabled-state edits are consequently permission-impacting audited changes. Teaching create/revoke events keep their Phase 8.1 vocabulary; teaching validity updates add `faculty.assignment.update` snapshots.

Actor, institution, creator/revoker and timestamps are server/database-derived. No tokens, passwords or secrets are logged. Trusted migration configuration of definition/mapping catalogue rows is not exposed as an unaudited tenant API.

## 16. Backend tests

`backend/tests/test_faculty_responsibilities.py` covers core-role/permission compatibility, exact teaching access, different sections/courses, department/class scope, cross-department class subjects, unrelated classes/departments/tenants, all validity boundaries, revocation, inactive accounts/grants, ownership, forged authorization fields, self-assignment, management scope, safe RPC errors, combined responsibilities, `/auth/me`, admin-route denial and reporting denial.

Report tests execute the real report aggregation against a relational query double: foreign/other-department rows are excluded, only recorded present statuses contribute to percentage, empty attendance remains null, low-attendance classification is explicit, unauthorized Faculty projections are not queried, and removed mappings deny reports. Pagination is exercised beyond 1,000 rows. Migration contract tests pin identifier-preserving backfill, constraints and audit/RLS guards; these are not represented as migration replay tests.

Existing backend tests were not weakened. The legacy RPC exact-contract tests remain intact.

## 17. Frontend tests

New tests cover separate positions/teaching display, HOD/Class In-Charge/combined navigation, inactive/future/revoked/expired removal, exact expiry boundary, refreshed revocation, failed/403 context refresh with stale-profile removal, read-only monitoring, report 403, admin create/update/revoke, conflict handling and server-owned mutation fields.

The existing assignment-manager tests received a fixture for the added management query; their teaching success/failure assertions remain intact. Existing Faculty, authentication/session, Student, Admin and Staff suites remain enabled.

## 18. Commands and actual results

Commands run from `backend` unless stated otherwise. `DEBUG=true` is required by the existing development-diagnostics tests. The initial `DEBUG=false` full run produced two diagnostics failures; that was corrected without changing their assertions. Default temp directories and the existing `.pytest_cache` directory were unwritable in this sandbox; a new workspace-local test directory resolved the fixture failure.

The workspace test parent was created with `New-Item -ItemType Directory -Path 'F:\Git Project\CollegeAIChatbot\backend\phase-validation' -Force` before the full run. Temporary test output was removed after verification. For the `uv` checks, `$env:UV_CACHE_DIR='F:\Git Project\CollegeAIChatbot\.uv-cache'` kept tool caches inside the workspace.

| Command | Actual result |
| --- | --- |
| `$env:DEBUG='true'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp 'F:\Git Project\CollegeAIChatbot\backend\phase-validation\pytest-run' tests` | 2,813 passed, 27 skipped, 6 warnings |
| `$env:DEBUG='true'; .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_faculty_responsibilities.py tests/test_phase_8_1_authorization.py tests/test_phase_8_permissions.py tests/test_faculty_attendance_imports.py` | 147 passed, 1 warning on the final changed authorization/RPC paths |
| `npm.cmd test -- --reporter=dot` from `frontend` | 565 passed across 70 files |
| `npm.cmd test -- --reporter=dot src/features/faculty/FacultyResponsibilities.test.tsx src/features/faculty/FacultyShell.test.tsx src/features/admin/FacultyAssignmentManager.test.tsx src/features/admin/FacultyResponsibilityManager.test.tsx` from `frontend` | 29 passed across 4 files on final UI verification |
| `npm.cmd run build` from `frontend` | TypeScript (`tsc -b`) and Vite production build passed; bundle-size warning remains |
| `uv run --with pyright pyright --pythonpath .venv/Scripts/python.exe app/services/faculty_responsibilities.py app/services/faculty_attendance.py app/services/authorization.py app/services/phase81_rbac.py app/schemas/faculty_responsibilities.py app/schemas/phase81.py app/api/faculty.py app/api/admin.py app/api/platform.py app/main.py app/core/permissions.py app/repositories/query_pages.py` | 0 errors, 0 warnings, 0 information diagnostics across 12 affected production modules |
| `.\.venv\Scripts\python.exe -m compileall -q app` | Passed |
| `git diff --check` | Passed; Git emitted line-ending notices |
| `uv run --with pglast python -c "from pathlib import Path; from pglast import parse_sql; from pglast.parser import parse_plpgsql_json; paths=['../supabase/migrations/20261011000000_faculty_responsibilities_and_validity.sql','../scripts/validation/faculty_responsibilities_database.sql']; [print(p, len(parse_sql(Path(p).read_text())), 'SQL statements; PL/pgSQL parse', parse_plpgsql_json(Path(p).read_text()) is not None) for p in paths]"` | Migration: 42 SQL statements; script: 5 SQL statements; SQL and PL/pgSQL parsing passed |
| `docker info --format '{{.ServerVersion}}'` | Failed: Docker engine named pipe does not exist; config read also denied |
| `supabase status` | Failed: CLI telemetry-file write denied in the sandbox |

Pyright is the static engine underlying Pylance; the CLI check above is the evidence. No claim is made that an IDE Pylance session was run, or that every unrelated repository module has been type-checked. Pyright/pglast were used via temporary `uv --with` environments; project dependency manifests were not changed.

Existing warnings include library deprecations, collection notices for Pydantic classes named `TestResult*`, frontend act/mock-query warnings, and the Vite bundle warning. The 27 skipped backend tests were not enabled or claimed as passing.

## 19. Scoped assignment-management extension and verification (7 October 2026)

Migration `20261014000000_scoped_faculty_teaching_assignment_management.sql` reuses `faculty_section_assignments`, `faculty_responsibilities`, and the existing `faculty.assignments.manage` permission. It adds Program Coordinator, Semester Coordinator, and Course Coordinator responsibility definitions. HOD and those coordinator appointments receive the existing management capability only when explicitly mapped; Class In-Charge does not.

The new Faculty endpoints list the caller's scoped assignment history and support create, validity/state update, and revoke. A server-resolved responsibility is checked against database-derived target scope in the application and revalidated in a SECURITY DEFINER RPC before the write. The transaction enforces active account/Faculty/institution state, active responsibility and half-open validity, permitted scope containment, existing target faculty/section, immutable assignment identity on update, and atomic before/after audit records. Reassignment remains revoke-old/create-successor. University Admin endpoints and permission grants remain unchanged. The scoped RPC now holds a PostgreSQL `FOR SHARE` lock on the matched responsibility row until the assignment transaction finishes, serializing authorization with responsibility updates/revocation.

### Frontend regression

- **Issue:** The full suite times out in `FacultyTests.test.tsx`, “loads real dashboard counts and all academic selectors,” waiting for the mocked `Open Class test` button. The DOM at timeout has the academic scopes and navigation but not the asynchronously loaded test list.
- **Root cause:** Timing/order contention from the default Vitest worker count starved the assessment component's asynchronous mock/API-to-render chain past Testing Library's normal async-query window. The test passed alone (and the full Faculty test file passed 27/27); full runs with default parallel workers varied between 610/616 and 615/616. Inspection found no shared mock, storage, navigation, or React Query state leak: RTL cleanup is active, the failed test resets and configures its mocks before each test, and the relevant fake-timer test restores real timers in `afterEach`.
- **Fix:** `frontend/vitest.config.ts` now uses isolated `vmThreads` with `maxWorkers: 2`, bounding simultaneous jsdom environments without increasing query/test timeouts, adding sleeps, weakening assertions, or changing assessment/assignment production behavior.
- **Verification:** Two full runs with bounded worker settings passed 616/616. After applying those settings as defaults, `npm test` passed twice (72/72 files, 616/616 tests). Four sequential Faculty files passed 70/70 before the fix; after the fix, the Faculty assessment and assignment-focused suites passed 45/45.

### SQL lint

- **NEW SQL ISSUES:** None. Final `supabase db lint --local` returned no diagnostics for migration `20261014000000_scoped_faculty_teaching_assignment_management.sql`; the temporary unused-variable warning from the first lock implementation was removed.
- **Existing SQL issues:** Two pre-existing `42702` errors in `20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql`: ambiguous `grant_id` in `phase81_manage_staff_permission_grants` and ambiguous `role_id` in `phase81_assign_institution_role_audited`. Two pre-existing warnings in `commit_faculty_test_import` for text-to-`jsonb` and text-to-`uuid[]` initializers. These are unrelated and were not modified.
- **Final result:** No new lint errors or warnings in the phase migration; repository SQL lint still reports the above baseline issues.

### Concurrency verification

`scripts/validation/faculty_assignment_concurrency.py` exercised concurrent PostgreSQL sessions against the project's local Supabase container; requests were launched in parallel with transaction barriers/sleeps, not sequentially simulated.

| Case | PostgreSQL result |
| --- | --- |
| Duplicate create race | PASS — two authorized scoped managers created the same Faculty/section pair concurrently; the partial unique index accepted exactly one row and its audit, rejecting the other transaction. |
| Conflicting create race | PASS — concurrent creates for the same Faculty/section with non-overlapping validity windows still produced exactly one unrevoked assignment, as required by the existing one-unrevoked-row business rule; no success audit was written for the rejected request. |
| Revoke versus Faculty mutation | PASS — revocation committed while holding the assignment row lock; the waiting attendance mutation rechecked teaching authority, was denied, and created no session. |
| Update versus revoke | PASS — concurrent scoped update/revoke serialized on the assignment row; final state was revoked/inactive, with exactly one revoke audit and no lost authorization state. |
| Scoped authorization versus responsibility revoke | PASS — a coordinator create waited on the responsibility row lock and was denied after the responsibility revocation committed; no active assignment or success audit resulted. |

### Final verification results

| Verification | Result |
| --- | --- |
| `supabase db reset --local` | PASS — clean replay of every migration through `20261014000000`; repeated after the race run to clear fixtures. |
| `scripts/validation/faculty_responsibilities_database.sql` on local PostgreSQL | PASS — transaction rolled back; HOD same-department create/update allowed, other-department management denied, history/audit and privilege assertions passed. |
| Database catalog checks | PASS — teaching/responsibility tables have RLS enabled; unique active Faculty/section index, scope indexes, validity and responsibility exclusion constraints exist. `service_role` can execute the RPC; `authenticated` cannot; direct `service_role` responsibility updates and authenticated reads are denied. |
| Backend focused assignment/RBAC/authorization/attendance/results tests | PASS — 390 passed, 6 skipped (remediation run). |
| Full backend `pytest tests -q` | PASS — 3,017 passed, 27 skipped, 6 warnings. |
| Assignment-management frontend tests | PASS — 18 passed across Admin manager, scoped manager and navigation suites. |
| Faculty assessment frontend file | PASS in isolation — 27 passed. |
| Full frontend `npm test` after worker-bound fix | PASS — two runs, each 72 files and 616 tests passed. |
| TypeScript and production build (`npm run build`) | PASS — `tsc -b` and Vite build succeeded; existing bundle-size warning remains. |
| Python diagnostics/static checks | PASS for changed Python files — no VS Code/Pylance problems; concurrency script syntax check passed. No repository Python linter is configured. |
| SQL lint (`supabase db lint --local`) | PARTIAL — no new issues; two pre-existing errors and two pre-existing warnings listed above remain. |
| `git diff --check` | PASS. |

### Security, authorization and audit verdict

No new role or authorization system was added. HOD and coordinator management remain scoped responsibilities mapped to the existing permission. Faculty self-administration and Class In-Charge assignment management remain denied; University Admin authority remains institution-wide. The transactional validation and concurrency cases confirmed in-scope access, out-of-scope denial, live revocation behavior, tenant checks, restricted database privileges and atomic audit records. The backend regression suite passed; no separate third-party security scanner was run.

### Files changed

Previous implementation files: `backend/app/api/faculty.py`, `backend/app/schemas/faculty_responsibilities.py`, `backend/app/services/faculty_responsibilities.py`, `backend/app/services/phase81_rbac.py`, `backend/app/services/faculty_schema.py`, `backend/tests/test_faculty_responsibilities.py`, `backend/tests/test_admin_faculty_schema.py`, `frontend/src/features/admin/FacultyAssignmentManager.tsx`, `frontend/src/features/admin/FacultyAssignmentManager.test.tsx`, `frontend/src/features/faculty/FacultyShell.tsx`, `frontend/src/features/faculty/facultyNavigation.ts`, `frontend/src/features/faculty/facultyNavigation.test.ts`, `frontend/src/features/faculty/ScopedTeachingAssignmentManager.tsx`, `frontend/src/features/faculty/ScopedTeachingAssignmentManager.test.tsx`, `frontend/src/services/adminApi.ts`, `scripts/validation/faculty_responsibilities_database.sql`, and `supabase/migrations/20261014000000_scoped_faculty_teaching_assignment_management.sql`.

Remediation files: the migration above (responsibility row locking), this report, new `scripts/validation/faculty_assignment_concurrency.py`, and `frontend/vitest.config.ts` (bounded isolated test workers).

All database operations ran against the local Docker Supabase stack only. The disposable concurrency fixtures were removed by the final local reset; no remote database was changed.

## 20. Known limitations

- SQL lint continues to report the documented pre-existing Phase 8.1 ambiguity errors and assessment-import initializer warnings; none was introduced by this phase.
- Faculty home-department/profile-name fields are not invented; displayed academic departments derive from assignments and identity continues to use the existing profile contract.
- Reports cover existing subject rosters/session attendance and active teaching Faculty. They do not fabricate class enrollment, university-wide analytics, results reporting or missing records. Existing Faculty Results/Notices/Resources roadmap pages remain unchanged.
- The 75% report threshold is displayed and fixed initially; institution-specific policy/configuration is a future extension.
- Revocations take effect immediately server-side; already-rendered navigation can take up to 30 seconds to refresh, or refresh sooner on focus. Known end timestamps remove UI links at their boundary. Newly starting appointments are picked up by server refresh.
- Responsibility presentation and management scope selectors are implemented for department, program, semester and course coordinator definitions; new scope kinds still require an explicit UI/workflow.
- Report pagination prevents silent REST truncation, but very large department reports may need database aggregation and API pagination as volume grows.
- Class In-Charge remains monitoring-only and receives no assignment-management mapping. No platform academic attendance-reading grant is introduced.

## 21. Future extension model

Additional responsibilities such as Exam/Lab Coordinator, Mentor, Advisor or Project Coordinator can reuse the trusted responsibility-definition, scope and permission mapping pattern. The existing central scope/validity resolver then enforces those grants. No new core role, authentication mechanism, tenant model, assignment table or academic/student model is required.

Definition/mapping changes should remain trusted migrations or be given a separately designed, scoped and audited administrative workflow; Faculty must not acquire a general catalogue editor through a position.
