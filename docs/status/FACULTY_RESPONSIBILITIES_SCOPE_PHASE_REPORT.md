# Faculty responsibilities, assignments and academic scope

Date: 7 October 2026. Status: IMPLEMENTATION COMPLETE.

MIGRATION VERIFICATION: BLOCKED. The code and automated application checks are complete. Database migration replay, execution of the transactional database validation script, and live concurrency verification remain unverified because no local Docker/PostgreSQL runtime is running. No remote database was changed.

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

HOD receives no user-management, global permission-management, role-management, appointment-management, attendance-edit or result-edit grant. HOD remains Faculty. Another department or institution is denied.

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
| `/platform/institutions/{institution_id}/faculty-responsibilities` | Super Admin list/create; ID-specific update/revoke |

University Admin tenant comes from authenticated identity, never a body/query tenant. A platform institution path selects a resource; the active Super Admin platform grant and explicit management permission still authorize the request. Platform responsibility management does not grant Super Admin access to student attendance. Teaching management retains its existing institution-admin workflow.

## 13. Frontend

The existing Faculty assignment manager now hosts selected-Faculty responsibility creation, scope/validity/state management and audited revocation history alongside teaching management. Teaching creation can specify validity; existing teaching rows can edit validity/enabled state.

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

## 19. Migration verification

**MIGRATION VERIFICATION: BLOCKED**

Reason: Docker has no running engine accessible at its named pipe. Supabase CLI also fails to write its user-profile telemetry file. A disposable PostgreSQL/Supabase database is therefore unavailable. Syntax parsing is successful, but migration replay, relational execution, extension/operator-class availability, exclusion-constraint concurrency and RPC/trigger execution are not claimed as verified.

`scripts/validation/faculty_responsibilities_database.sql` supplies transactional fixtures and assertions for coexistence, HOD/class conflicts across subject anchors, adjacent appointments, cross-tenant faculty/department rejection, forged definitions, self-assignment, validity edits, audit events, revocation after account deactivation and database privilege boundaries. It ends in ROLLBACK. Its SQL/PLpgSQL syntax is checked; it has not been executed against a database.

Before live use, replay migrations in a disposable local/staging environment, run that script with `psql <local database URL> -v ON_ERROR_STOP=1 -f scripts/validation/faculty_responsibilities_database.sql`, and exercise concurrent appointment creation in two sessions. Applying the migration to a live service was not part of this validation run.

## 20. Known limitations

- Runtime migration/database and concurrency verification remains blocked as described above.
- Faculty home-department/profile-name fields are not invented; displayed academic departments derive from assignments and identity continues to use the existing profile contract.
- Reports cover existing subject rosters/session attendance and active teaching Faculty. They do not fabricate class enrollment, university-wide analytics, results reporting or missing records. Existing Faculty Results/Notices/Resources roadmap pages remain unchanged.
- The 75% report threshold is displayed and fixed initially; institution-specific policy/configuration is a future extension.
- Revocations take effect immediately server-side; already-rendered navigation can take up to 30 seconds to refresh, or refresh sooner on focus. Known end timestamps remove UI links at their boundary. Newly starting appointments are picked up by server refresh.
- New responsibility definitions can use the supported backend scope levels; their presentation/navigation and admin scope selectors need UI work when a new kind of scope or workflow is introduced.
- Report pagination prevents silent REST truncation, but very large department reports may need database aggregation and API pagination as volume grows.
- Teaching management stays with University Admin; the platform APIs added in this phase manage responsibility appointments. No platform academic attendance-reading grant is introduced.

## 21. Future extension model

Add Course/Exam/Program/Lab Coordinator, Mentor, Advisor or Project Coordinator through a trusted responsibility definition, permitted scope levels and mappings to active catalogue permissions. The existing central scope/validity resolver then enforces those grants. Add a relevant UI/workflow where needed. No new core role, authentication mechanism, tenant model or academic/student model is required.

Definition/mapping changes should remain trusted migrations or be given a separately designed, scoped and audited administrative workflow; Faculty must not acquire a general catalogue editor through a position.
