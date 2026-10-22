# Unified setup and institution academic reset

Updated: 2026-10-22, Asia/Calcutta.

## Confirmed scope

The user requested one coherent Academic Setup flow and deletion of existing
academic setup and related academic records for their institution. They explicitly
excluded accounts, roles, and other modules from deletion.

The configured backend and linked Supabase project both identify
`rjnfmjcvkfotneswpygr` (College AI Chatbot). Read-only preflight found one
institution: **Quest**, code **QUEST123**, ID
`93d79749-0164-4cbf-b378-5fdff295d7af`. It has two departments, two programs,
one academic year, and no student profiles. No target is inferred from a section
name or a browser-supplied institution ID.

## Unified administrator workflow

1. **College basics:** departments, programs/branches, and admission batches.
2. **Calendar:** academic years and dated teaching terms.
3. **Subjects:** reusable subject definitions.
4. **Curricula & packages:** named versions, study semesters, classifications,
   shared core, and fixed subject combinations.
5. **Classes:** batch and term, curriculum, section, enabled packages, selection
   rules, deadline, and prepared subject teaching groups.
6. **Assignments:** placements, complete package assignment, requests, and history.

The former nine-entity tab bar and standalone legacy curriculum editor are
retired from this flow. Subject offerings and teaching sections remain normalized
records for attendance, examinations, and faculty assignments; Class Setup owns
their preparation and mappings.

Preparing teaching groups retains the existing institution-administrator
requirement and needs both class-management and course-management authority.
It prepares core and enabled-package subjects
atomically, reuses canonical offerings, retains valid existing mappings, and
rejects invalid or foreign mappings without partial writes.

## Reset boundaries

The reset removes only the target institution's academic structure and dependent
academic records: curricula/packages/classes, package assignments and requests,
placements and registrations, teaching groups and memberships, attendance,
assessments/results, teaching assignments/responsibilities, imports, subject
definitions, batches, programs, departments, and calendar records.

Auth accounts, application users, roles, permissions and per-user grants remain.
Institution/organization records, nonacademic content and communications, and
other institutions remain. Student and faculty identity profiles remain; academic
foreign keys may be cleared where required by the deleted structure. Existing
security/administration audit history is retained.

This is an operational reset, never a migration seed or a global TRUNCATE.
It does not export authentication records or create a sensitive data backup.
The historical global-reset scripts have a different scope and must not be used.

## Execution and verification

The reset must pin the institution ID, inspect real foreign keys and triggers,
reject unexpected dependencies, and perform all academic deletes in one
transaction. A rollback rehearsal and preservation checks precede commit;
independent postchecks confirm the final state. Unknown schema differences stop
execution instead of widening deletion scope.

The initial live ledger contained 42 earlier migrations. Named curriculum/class
tables were absent. The academic migration was validated against that exact
baseline, then installed with its migration-ledger entry in one transaction.
The unrelated B05 invitation draft and student-approval repair remain absent.

The live rollback rehearsal and permanent operation matched the reviewed plan:
**53 academic rows removed**, with preservation fingerprints verified across
**104 accessible public/Auth/migration tables** and trigger states restored.
An independent postcheck found **zero** remaining academic rows across the
36-table scope. Accounts, role grants, other modules, and retained audit history
passed preservation checks. No demo or replacement academic data was inserted.

Execution status and verification evidence are recorded in
[Implementation and validation](implementation.md). The local read-only
preflight evidence is `logs/backend/academic-cleanstart-preflight.json`.
Release evidence is `academic-schema-{rehearsal,commit}.json`; reset evidence is
`academic-reset-{rehearsal,commit,postcheck}.json`, all under `logs/backend/`.
