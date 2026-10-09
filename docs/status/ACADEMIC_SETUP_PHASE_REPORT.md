# IMPLEMENTATION STATUS

**COMPLETE for the setup workflow and deployed schema.** Academic Setup is implemented inside the existing Admin shell, and the new migration is deployed to Supabase project `rjnfmjcvkfotneswpygr`. Real-data Faculty Assignment and Student Academic Experience browser verification remains pending institution data/enrollment. No real institution master records, students, rosters or teaching assignments have been fabricated.

# EXISTING ACADEMIC DATA MODEL

The pre-implementation audit is in `ACADEMIC_SETUP_AUDIT.md`. Existing tables remain authoritative: `institutions`, `departments`, `programs`, `academic_years`, `semesters`, `courses`, `program_courses`, `course_offerings`, `sections`, `students`, `faculty_attendance_rosters`, `users` and `faculty_section_assignments`.

Departments belong to institutions; programs and subject definitions belong to departments. Years belong to institutions; semesters belong to years. Program curriculum links connect programs to subjects. Offerings join subject/program/year/semester; subject-specific sections belong to offerings. Existing class scope groups sibling subject sections by program/year/semester/section code. No additional hierarchy or cohort table was introduced.

# ACADEMIC MASTER DATA MANAGEMENT

Admin -> Academic Setup provides tabs for all seven requested master entities and the existing Program Curriculum links required by the offering composite FK. Create, view, edit and activation/deactivation use the existing design system, HTTP client, session-expiry behavior and token/mount-scoped query caching. Active parent selectors cascade through program, year, semester and curriculum subject. Empty states report missing records honestly. The entry guide is `docs/ACADEMIC_SETUP.md`.

API: `GET /api/v1/admin/academic-setup`, `POST /api/v1/admin/academic-setup/{entity}`, `PATCH /api/v1/admin/academic-setup/{entity}/{record_id}`. No deletion endpoint exists. Academic ancestry remains fixed after creation; section code is fixed because it participates in responsibility scope. Deactivation retains dependent records and history.

# DEPARTMENTS

Manage existing `departments` with official name/code, description and active state. Database uniqueness prevents codes differing only by case/whitespace within an institution. Dependent programs, subjects, sections and history are retained on deactivation.

# PROGRAMS

Manage existing `programs` under an active tenant-owned department, including degree type, duration and total credits. Program codes are unique within a department. Parent IDs cannot be moved to another institution or department.

# ACADEMIC YEARS

Manage existing `academic_years` with dates, active and current state. Existing one-current-year uniqueness is preserved. An exclusion constraint prevents overlapping active years, including concurrent inserts. Inactive years cannot remain current; edits cannot exclude existing semester dates.

# SEMESTERS

Manage existing year-owned `semesters`, with code/number, dates and active/current state. Dates must fit the year. Existing year/code, year/number and one-current-term indexes remain authoritative. Programs use these shared terms through offerings; no duplicate program-specific semester model was added.

# COURSES / SUBJECTS

Manage existing department-owned `courses` with descriptions, credits and contact hours. Existing `program_courses` curriculum links support course type, required/optional state and an optional term restriction. Cross-department subjects are permitted only within the same institution. Leave the optional term unset for a reusable curriculum link.

# COURSE OFFERINGS

Manage existing offerings using active program, year, semester and curriculum subject. Semester/year equality and curriculum membership retain their existing foreign keys; tenant/activity checks run in the database. The original course/program/year/semester unique constraint prevents duplicate teaching occurrences.

# SECTIONS

Manage existing offering-owned sections with name, section code, capacity and active state. Normalized code uniqueness is per offering, preserving legitimate sibling subject sections with a shared class code. Metadata/capacity can change; academic parent and section code cannot be rewritten.

# STUDENT ENROLLMENT DEPENDENCY

Student identities remain in `students`, linked to real `users` accounts, institution and optional program/year. Existing registration/approval and Admin Student management remain unchanged. Actual subject enrollment/reconciliation uses `faculty_attendance_rosters` and its existing linked-student, section/offering/semester and eligibility rules. Setup creates neither students nor rosters. Real student provisioning and roster enrollment are deployment/data dependencies.

# AUTHORIZATION

Reuse the existing active institution Admin dependency, canonical role/tenant resolution and granular permissions. `departments.*` covers departments/programs; `academic_years.*` covers years; `semesters.*` covers semesters; `courses.*` covers subjects/curriculum/offerings/sections. The catalogue projects only readable entities; management controls follow server-returned permissions. The database rechecks the existing institution-admin primitive and active permission mappings. Faculty, Students, Staff, Class In-Charge responsibilities and platform-only grants gain no master authority.

# TENANT ISOLATION

Every read follows tenant-owned ancestors. Mutations derive actor/institution from authenticated server state; control fields are rejected in payloads. Foreign record IDs return not-found, foreign parents/subjects are rejected, and parent IDs are immutable. API tests and physical SQL contracts cover manipulated tenant IDs, IDOR, cross-tenant links and revoked permissions.

# AUDIT

One service-only RPC performs each mutation and inserts before/after state into existing `admin_audit_log` in the same transaction. Actor, tenant, record and create/update/activation/deactivation action are retained. An injected audit failure in a disposable rollback contract proved that the academic mutation does not persist without its audit. No additional audit system was created.

# CONCURRENCY

Database constraints and transaction locks protect concurrent creation. Five disposable two-admin races passed: department, program, offering, section and overlapping academic year. Each race produced one committed record, one rejected duplicate/date conflict, and exactly one audit event. These fixtures were confined to a labelled disposable local container, subsequently removed.

# FACULTY ASSIGNMENT INTEGRATION

The existing assignment architecture, permission checks and source tables are unchanged by this phase. A local database contract creates a section through the new setup RPC and passes that exact identifier to the existing teaching-assignment RPC successfully. Remote real-data browser verification is pending because the institution has no real sections; do not interpret the local fixture contract as a verified live assignment flow.

# STUDENT ACADEMIC INTEGRATION

Existing student identity, eligibility, attendance and published-result services remain authoritative. Full backend/frontend regressions include Student Academic Experience and session isolation. No alternate enrollment identity, marks store or timeline store was introduced. Positive live student verification requires actual students and subject enrollment.

# DATABASE CHANGES

One additive migration: `20261016000000_academic_master_data_management.sql`. It creates no tables and seeds no academic records. It adds six normalized code indexes, the active-year date exclusion, two current/active checks, an internal tenant resolver, one shared validation trigger on eight existing tables, and one audited write RPC. RLS is enabled on those tables; anonymous/authenticated table and RPC privileges are denied. Service reads remain available; destructive table DELETE/TRUNCATE privileges are revoked. Existing assignment, attendance, assessment and student storage are preserved.

# DATABASE VERIFICATION

Clean disposable replay: **38/38 PASS**. Academic mutation/rollback, audit, tenant/IDOR, hierarchy/date/current-state, archive, assignment and privilege/RLS contracts passed. Existing responsibility, attendance and assessment SQL contracts also passed. New SQL function lint passed for the tenant resolver, write RPC and validation trigger against each of its eight table types. This is a phase-specific SQL lint result, not a claim that unrelated legacy functions have no lint debt.

Remote deployment: **38/38 migrations match the repository**, latest `20261016000000`, with no pending or remote-only versions. The reviewed dry run and deployment each listed only the new migration, with empty seed/role lists. Its source SHA-256 did not change during deployment.

Post-deployment remote catalog verification passed: all three new routines exist with service-only execution; eight validation triggers, six normalized code indexes and the year exclusion are present; all eight master tables have RLS enabled and deny anonymous/authenticated reads/writes while preserving service reads and denying service DELETE. Before/after counts for every master entity and students remained **0**. The real remote catalogue loads all eight manageable entities; existing assignment options still show **1 Faculty, 0 sections, 0 assignments**.

PostgREST RPC availability passed using the real server-resolved Admin actor/tenant and an empty payload. The database returned the expected `22023` validation error before any academic/audit mutation. Probes use process-local identity injection with actual remote role/permission/tenant resolution; they do not claim browser/JWT login or successful real-data creation.

# BACKEND TESTS

**3,102 passed, 0 failed, 27 existing skips**. This includes **62 new academic setup tests**. Existing tests, authentication clocks, assertion behavior and skip markers were preserved. The final run used the repository's DEBUG=true default and a fresh writable pytest base/cache directory. The initial attempt inherited an invalid DEBUG=release environment value; that collection failure was corrected before the complete run.

# FRONTEND TESTS

**628 passed, 0 failed, 0 skipped, 73 files**, including **12 new Academic Setup tests**. The final complete run used `node node_modules/vitest/vitest.mjs run --pool=forks --maxWorkers=1`, preserving all tests, assertions and timeouts. No existing test was skipped or weakened.

The configured VM-worker harness returned 627 passes and one timeout in the existing Faculty Tests async UI wait in two complete runs; its isolated file passed all 27 tests, and the final full process-worker run passed it too. This runtime sensitivity remains documented; the repository's worker configuration was preserved. An earlier run also encountered a navigation expectation while its source was being updated; the final navigation tests cover the completed permission behavior. Existing React `act` and legacy AcademicsPanel mock warnings remain in the passing run's log.

# TYPESCRIPT

PASS. The forced TypeScript check passed; the final production build also completed `tsc -b` against the final frontend source.

# BUILD

PASS. Production Vite build completed, and the existing build-security scan passed against all four generated distribution files with only the allowed public frontend environment key. Vite retained its bundle-size advisory; it did not fail the build.

# SECURITY

Academic authorization, inactive account/institution, permission revocation, tenant/IDOR, payload controls, relationship immutability, database grants/RLS, audit atomicity and duplicate/date races passed. Authentication/RBAC, attendance, assessment and student regressions are included in the full backend suite. No browser key or service credential was added to frontend source or build assets.

# REMAINING DEPENDENCIES

Enter actual institution departments, programs, years, semesters, subjects, curriculum links, offerings and sections. Then verify a teaching assignment with the existing real Faculty account. Provision/approve real students and enroll/reconcile them through existing rosters before positive live Student Academic Experience verification. Authenticated browser completion is pending real data and credentials; process-local read probes do not substitute for it.

# FINAL VERDICT

**PASS for Academic Setup implementation, schema deployment and the documented verification commands.**

**Schema/setup workflow is ready; real institution master data must be entered.**

Faculty Assignment and Student Academic Experience are not claimed fully verified against live real data: remote sections and students remain absent. Enter actual records through Admin -> Academic Setup, then complete the existing assignment and student enrollment workflows. No fake data was inserted to supply a successful screen or dropdown.

The final corrections, new frontend tests, SQL lint contract and documentation remain in the working tree for review/commit. An intermediate user commit made during this work was preserved; no Git commit was made by this agent.

Detailed logs/status reports are in `supabase/.temp/academic-setup-verification/` (git-ignored).
