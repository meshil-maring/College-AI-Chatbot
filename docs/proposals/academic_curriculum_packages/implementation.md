# Implementation and validation

Updated: 2026-10-22, Asia/Calcutta. Backend/frontend source and production build
are updated locally. The academic schema is installed in the verified linked
project and Quest's authorized academic-only reset is complete.

## Delivered workflow

Academic Setup retains dark panels, yellow actions, searchable directories, and
detail panels. The unified administrator sequence is **College basics ->
Calendar -> Subjects -> Curricula & packages -> Classes -> Assignments**.
Foundational forms live within their owning stages. The former nine-entity tab
bar, standalone legacy curriculum editor, and duplicate package navigation are
retired. Requests and history are operational views under Assignments.

Classes owns offerings and subject teaching sections. Its atomic teaching-group
preparation requires an institution administrator with class-management plus
course-management authority, reuses canonical offerings, retains valid mappings,
and rejects invalid mappings
without partial writes. Other authorized role workspaces reuse the package
operations according to server permissions.

The setup sequence is basics/calendar/subjects -> curriculum core and packages
-> class and policy -> enabled packages/prepared teaching -> placements -> assignments.
Every selected package assigns all its subjects plus shared core atomically.
Placements for the same registration cannot overlap in captured teaching dates,
even under different term IDs. Later nonoverlapping terms remain supported.

The confirmed deadline is an administrator-set instant capped at the calendar
semester midpoint. Cutoffs can only shorten. Students may choose their first
package only when enabled; later changes require authorized administration.
After cutoff, changes and late approvals are closed for everyone. First
assignments remain possible for late admissions under the same authority.

See [assignment rules](assignment-rules.md) for the exact policy and date-only
event eligibility limitation. Request cancellation, notifications, independent
elective slots, retakes, and credit transfers are outside this version.

## Storage and normalization

| Responsibility | New records |
| --- | --- |
| Named/versioned plan | `academic_curricula`, `academic_curriculum_subjects` |
| Complete bundles | `academic_subject_packages`, `academic_package_subjects` |
| Shared class and mappings | `academic_classes`, `academic_class_packages`, `academic_class_subjects`, `academic_class_responsibilities` |
| Student placement | `academic_class_placements` |
| Assignment and history | `academic_package_assignments`, `academic_package_revisions` |
| Effective subject intervals | `academic_subject_participation` |
| Student requests | `academic_package_requests` |

Subjects and memberships use foreign keys and bridge rows rather than CSV/JSON
subject lists (1NF). Curriculum/package links depend on their complete keys
(2NF). Class program and year are derived through batch and dated term instead
of copied into every class; subject definitions and student identity remain in
their existing owner records (3NF).

Teaching date snapshots intentionally retain the policy used by a class.
Revision/audit snapshots intentionally preserve history. Roster participation
fields are protected projections of authoritative participation episodes, used
by existing current-roster screens. These controlled copies are distinct from
independently editable duplicate masters.

The legacy `program_courses` contract remains intact. This change does not guess
packages from existing roster subjects, reinterpret teaching section IDs as
classes, or rewrite admission registrations. An administrator must explicitly
map the verified batch/class, subjects, and eligible registrations.

Offerings accept either a valid existing legacy program/subject link or an
exact named class/curriculum subject for that program and dated term. The old
offering-to-legacy-pair FK is replaced by this validated applicability rule;
individual program and subject FKs and legacy link keys/rows remain intact.
The offering picker receives computed eligibility metadata, so named-only
subjects and later-term subjects need no copied legacy classification/link.

Class creation requires at least one complete package for its selected study
semester and freezes that curriculum version. Finish all subjects and packages
before creating its first class. Teaching-group mappings can then be completed
before assignment. See the [fresh-start record](fresh-start.md) for the confirmed
Quest-only reset scope and live schema baseline.

## Security and integrity

All new tables use RLS with direct browser and service-role table access
revoked. Only the catalogue and command entry points execute for the service
role; they revalidate the authenticated actor, institution, permission, scope,
identity, academic eligibility, and capacity. Helper functions are private.

The new permission families are `academic.curriculum.*`, `academic.class.*`,
`academic.package.assign/change/requests.review`, and
`academic.package.own.read/select/request`. Staff capabilities use the existing
audited delegation flow. HOD follows the program department; class incharge
requires an explicit class responsibility bridge. Ordinary teachers gain no
package authority.

Commands serialize with existing attendance writers before locking assignment
and roster rows. Change authority and wall-clock cutoff are checked again after
lock waits. Expected revisions prevent stale changes. Assignment, participation,
request decision, revision history, and audit writes share one transaction.

Existing individual assignment/deletion now use audited database RPCs. Managed
groups reject individual roster additions and uncontrolled identity changes.
Attendance history has a restrictive roster FK; roster/audit truncation and
destructive service-role privileges are revoked or guarded. Reconciliation
preserves its canonical identity and account-state responsibilities.

Ended subjects retain attendance and published marks. Current rosters and
upcoming assessments exclude ended participation; history services preserve it.
Marks screens preserve previously entered scores for ended subjects.
Rejoining a subject reuses its prior roster ID with a new participation episode.
When an administrator explicitly adopts an existing legacy roster in its first
package assignment, established attendance/marks dates remain eligible. This
retains historical subject participation; the package assignment and its
revision still begin at the actual assignment instant.

For later terms, attendance imports and assessments derive teaching-year and
study-semester context from an exact managed placement. Canonical student IDs,
admission year, account approval and activation remain unchanged. Legacy groups
retain their strict academic-year checks. Pending/unregistered marks remain
private; account approval reconciles the same preserved results normally.

## Source entry points

- [Package UI](../../../frontend/src/features/academic-packages/AcademicPackagesWorkspace.tsx)
  and [API transport](../../../frontend/src/services/academics/academicPackagesApi.ts).
- [Backend API](../../../backend/app/api/academics/academic_packages.py),
  [typed commands](../../../backend/app/schemas/academics/academic_packages.py),
  and [service](../../../backend/app/services/academics/academic_packages.py).
- [SQL source manifest](../../../supabase/migration_sources/academic_packages/manifest.json).
- [Migration generator](../../../scripts/maintenance/migrations/build_academic_packages.py).
- [Disposable database runner](../../../scripts/validation/academic_packages/verify_database.py)
  and its adjacent executable SQL contracts.
- [Student experience projections](../../../backend/app/services/students/student_academic_experience.py).

## Migration preparation and release

The maintained SQL fragments generate
`20261021000000_academic_curriculum_packages.sql`. Existing migrations are
unchanged. The generated file is intentionally exempt from maintained-source
line and folder limits; its source fragments obey both limits.

```powershell
python scripts/maintenance/migrations/build_academic_packages.py
python scripts/maintenance/migrations/build_academic_packages.py --check
python scripts/validation/academic_packages/verify_database.py
```

The runner requires a cached local Supabase PostgreSQL image and local Docker
Desktop Linux. It creates a fresh owned container with no network, host ports,
binds, or persistent volumes; data lives in a bounded tmpfs. It checks engine,
full container ID, ownership token, labels, storage and network before use and
checks ownership again before cleanup. It never connects to the live database.

The generated foundation was installed after disposable replay and a live
rollback rehearsal. Its source SHA-256 is
`0f819dced1514f2502fe18148227bc101debcc987d148deae82ca3dcd6466eee`.
The schema and migration-ledger entry committed together. The two unrelated
absent B05 invitation/approval migrations were not included. Configure the fresh
institution through the six-stage workflow using the matching application code.

## Verification evidence

Logs are local artifacts in `logs/backend/` and `logs/frontend/`.

- The unified workflow passes **942 frontend tests** across 125 files. A final
  focused run covers the six stages, foundational forms, legacy form contracts,
  package operations, and permissions. Production build and structure checks pass.
  Browser checks confirm one navigation, empty start, prerequisite links, unsaved
  form protection, one strict teaching-preparation command, complete subject
  previews, and desktop/mobile layouts without page errors or viewport overflow.
  Evidence: `academic-unified-{full-tests,tests-recheck,structure,final-build,browser}.txt`.
- **235 backend focused tests pass**, including the new preparation command,
  academic setup, RBAC snapshot, and source structure (`academic-unified-python.txt`).
- Both full **45-migration** and exact remote-like **43-migration** replays pass.
  The latter omits the two unrelated absent migrations and verifies preparation
  and complete assignment without B05 artifacts. Full SQL/security/history and
  actual concurrency contracts pass (`academic-unified-{database,remote-baseline}.txt`).
- The scoped reset passes disposable rollback/commit, wrong-target, changed-plan,
  external-dependency, profile/account/role/audit, institution appointment,
  other-tenant and idempotency checks (`academic-scoped-reset-validation.txt`).
- Quest's live rehearsal and permanent reset removed **53 academic rows** from
  the reviewed 36-table scope. Preservation fingerprints passed across **104
  accessible tables**, with trigger restoration verified. An independent
  postcheck reports **zero** remaining academic rows. Evidence:
  `academic-reset-{rehearsal,commit,postcheck}.json`. Historical audit snapshots
  remain. See [the fresh-start record](fresh-start.md) and
  [scoped maintenance guide](../../../scripts/maintenance/academic_reset/README.md).
- Live catalogue/RBAC verification also passes: all 13 new tables have RLS,
  direct browser/service reads and helper execution are denied, command execution
  is allowed for the service role, and the preserved administrator receives an
  empty catalogue with preparation capability. Account counts remain six Auth
  accounts and two application users, with two role grants and 31 retained audit
  rows (`academic-release-postcheck.json`).

- **705 backend tests passed** in `packages-final-focused-tests.log`: package
  API/validation, legacy subject assignment, attendance/imports, assessments,
  responsibilities, registrations, student experience, bootstrap/public-chat
  contracts, RBAC, source structure, and retrieval evaluator regressions.
- **All 45 migrations replayed successfully** in a fresh disposable database.
  SQL lint, original academic/attendance/exam/responsibility contracts, complete
  package assignment, rollback, requests, cutoff/authority expiry after waits,
  student privacy, later-year approval/publication, historical adoption, legacy
  event guards, and named-only offerings passed. Actual competing selections,
  last-seat capacity, responsibility lock-wait expiry, and five existing master
  creation races passed. Evidence: `packages-database-validation-final.log`.
- Backend structure and generated RBAC checks pass. New/refactored SQL and
  Python feature modules/folders obey the 250-line and 15-file limits. Existing
  tests-root files were edited in place; its pre-existing excess count remains,
  and new tests live inside the focused feature subfolders.
- All **44 earlier migration hashes remain unchanged** against the recorded
  preimplementation inventory.
- Frontend structure and production build pass. Browser checks cover curriculum,
  class/rules, selection codes, complete subject assignment, and desktop/mobile
  layouts using intercepted preview fixtures (no production records).
- The full frontend run passed **940 of 942 tests** across a host interruption.
  Two existing examination loading waits timed out. After setting an explicit
  five-second budget for the initial test-only load waits, that complete
  **23-test examination file passed**, covering both failed scenarios.
  Evidence: `academic-packages-{structure,build,browser,full-tests,examinations-recheck}.txt`.
- The final offering integration adds **31 passing frontend regressions**,
  another successful production build/structure check, and desktop/mobile
  browser checks for named-only creation and legacy/new-term coexistence.
  Evidence: `academic-packages-offerings-{tests,build,structure,browser}.txt`.

The broader backend run is not fully green. Its original log is
`packages-full-regression-tests.log` (3,685 passed, 27 skipped). Environment
rechecks resolved the debug-mode, email-mode, and temporary-directory failures.
Nineteen unrelated failures remain: eighteen approval/legacy student tests with
outdated expectations or incomplete eligibility mocks, and one archived B05
draft whose frozen migration ledger predates later migrations. Source/AST
comparisons are in `academic-packages-legacy-failure-baseline.json`; rechecks are
in `packages-environment-recheck.log` and `packages-configuration-recheck.log`.
Eligibility guards and archived review SQL were preserved.

The original [preimplementation audit](audit/README.md) remains a dated baseline;
its original source hashes and line references describe the earlier workspace.
This document records the implemented response without rewriting that evidence.
