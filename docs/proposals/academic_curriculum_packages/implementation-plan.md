# Implementation plan and acceptance criteria

Status: original implementation plan, with delivery status updated after local
implementation. Read [Implementation and validation](implementation.md) for the
actual source paths, policy decisions, evidence, and release requirements.

The [preimplementation audit](audit/README.md) records source defects,
normalization tradeoffs, compatibility blockers, and verification limits. Its
findings must be addressed in the relevant stages; no fixes are applied here.

## Current source and required changes

These observations concern the local source, including existing workspace
changes. They are not assertions about a deployed database.

| Current implementation | Difference required by the proposal |
| --- | --- |
| `programs` represent degrees/branches; `courses` represent individual subjects. | Preserve internal contracts and use clear product labels. |
| `program_courses` links one program to one subject with type/required flags and optional dated `semester_id`. | Add a named curriculum parent, study-semester organization, and package membership. |
| `semesters` are dated terms owned by academic years. | Represent curriculum study semesters separately and map them through class setup. |
| `course_offerings` schedule subjects for a program/year/term. | Connect the required occurrences to a shared class and its offered packages. |
| `sections` belong to individual subject offerings. | Preserve these teaching groups while introducing an explicit shared class identity. |
| Class registrations group students independently from individual subject memberships; batch is recorded on registration. | Map registrations to explicit classes without guessing or changing student identity. |
| Subject Assignment handles an individual subject roster at a time. | Add complete package assignment, student initial choice, requests, and deadline-controlled changes. |
| HOD/class incharge responsibilities provide scoped capabilities. | Design explicit new capabilities and scope checks; titles alone cannot authorize package changes. |

### Source entry points

- [Academic definitions](../../../frontend/src/features/admin/academic-setup/academicSetupDefinitions.ts)
  and [workspace](../../../frontend/src/features/admin/academic-setup/AcademicSetup.tsx).
- [Academic contracts](../../../backend/app/schemas/academics/academic_setup.py)
  and [setup service](../../../backend/app/services/academics/academic_setup.py).
- [Class registration reference](../../status/STUDENT_CLASS_REGISTRATION.md).
- [Existing subject assignment service](../../../backend/app/services/students/subject_assignments.py)
  and [student workspace UI](../../../frontend/src/features/students/subject-assignment/SubjectAssignment.tsx).
- [Faculty responsibility review](../../rbac/roles/faculty.md#scoped-academic-responsibilities).
- [Backend structure](../../../backend/STRUCTURE.md) and
  [frontend structure](../../../frontend/docs/STRUCTURE.md).

## Proposed conceptual records

The following are responsibilities, not final table names, SQL, or API routes.

| Record | Responsibilities |
| --- | --- |
| Curriculum and version | Institution, program applicability, name/code, study semesters, lifecycle. |
| Curriculum subject | Existing subject reference, study semester, classification, shared-core/required status. |
| Subject package and membership | Name/code, curriculum version/study semester, complete subject set, lifecycle. |
| Shared class | Institution, program/branch, batch, academic year/dated term, study semester, section identity, curriculum version. |
| Class package availability and policy | Allowed package versions, selection codes, student initial-choice flag, change cutoff. |
| Class subject mapping | Exact subject offering and teaching section used for each required subject. |
| Temporal class placement | Persistent registration/student identity linked to each class/period, with progression/history separate from institutional identifier uniqueness. |
| Subject participation and episodes | Effective enrollment, end/rejoin history and provenance, separate from account/approval status; preserve existing roster/event identities. |
| Student package assignment and revision | Registration/class, package/version, effective history, actor, subject memberships, retry identity. |
| Change request and decision | Source assignment revision, target package, student reason, status, reviewer, decision time, audit. |

Shared class membership and subject teaching membership remain distinct. Package
selection changes a student's subjects while retaining their class placement.
Offerings and teaching groups may be reused only where their academic context
matches; the final cardinalities must follow a verified compatibility design.

## Compatibility and migration requirements

- Keep existing identifiers and references used by faculty assignments, student
  registration, identity reconciliation, attendance, tests, marks, and results.
- Do not reinterpret a subject `section_id` as the new shared class identifier.
- Map existing class groups using their full verified institution/program/year/
  term/section context and registration batch. Equal section codes across
  offerings, batches, programs, or institutions are insufficient evidence.
- Preserve current subject classifications and curriculum applicability. Mapping
  dated legacy links to curriculum study semesters requires explicit review.
- Treat legacy students without a known package as unresolved/legacy records.
  Do not fabricate a package from current roster subjects or guessed codes.
- Resolve ambiguous or mixed legacy data before enabling a class for packages.
  Existing enrollment remains usable while migration decisions are outstanding.
- Version API contracts or provide compatible adapters for affected clients.
  Document how individual subject assignment behaves in package-managed classes
  so it cannot add/remove subjects outside the approved package workflow.
- Use controlled migrations and transactional assignment operations. Preserve
  tenant isolation, database write guards, account approval, and audit behavior.

## Delivery stages

1. **Settle policy and mapping decisions.** Record the decisions below, define
   terminology, temporal placement, effective subject participation and scoped
   capabilities, and inventory real legacy classes. Plan the deletion,
   eligibility, audit and retention fixes identified by the source audit.
2. **Curriculum foundation.** Add named/versioned curricula, study semesters,
   classifications, shared core subjects, and fixed packages. Preserve old links.
3. **Class setup and readiness.** Connect batches, calendar terms, curriculum,
   offered packages, teaching groups, and selection/change policy. A class with
   incomplete mappings must show what is missing before assignment is enabled.
4. **Administrative package assignment.** Deliver one atomic operation for the
   complete subject set, capacity/identity checks, retries, scope, and history.
5. **Student initial selection.** Expose only the student's available class
   packages, and enforce the admin setting on the same authoritative write path.
6. **Changes and requests.** Add direct authorized changes, student requests,
   scoped review, stale-request handling, hard cutoff checks, and history views.
7. **Workflow and visual integration.** Organize the Academic Setup stages and
   Student Management screens described in the overview. Keep the dark/yellow
   style and preserve accessible, responsive, permission-aware interactions.
8. **Verified migration and release.** Validate legacy mappings in a disposable
   environment, run the relevant regression/security/concurrency checks, then
   enable only classes with complete policy and data mappings.

Stages 1 through 7 have local implementations. Stage 8 now has complete disposable
validation, an exact remote-baseline replay, and a live schema installation with
transactional ledger recording. The user's later fresh-start request superseded
legacy backfill for Quest: its academic records were reset while preserving
accounts, roles, audit history, and unrelated modules. See the
[fresh-start record](fresh-start.md) for the authorized scope and completed checks.

## Acceptance and verification plan

| Area | Required evidence before enabling the feature |
| --- | --- |
| Basic assignment | Package ABC assigns DSA, ML, A, B, C together; package EFG assigns DSA, ML, E, F, G in the same class context. |
| Completeness | Every selected package subject is assigned; partial selections and mixed packages are rejected. |
| Shared core | Common subjects are reused without duplicate students, rosters, or attendance/mark history. |
| Atomicity | A missing/full/conflicting subject group causes the entire operation to leave the original state unchanged. |
| Student setting | Enabled permits an initial own-class choice; disabled rejects student writes; toggling never changes existing assignments. |
| Later student changes | Direct replacement is rejected even while initial choice is enabled; the student must submit a request. |
| Authority and scope | Required capabilities and active responsibility scope are checked; foreign classes, departments, students, and tenants are rejected. |
| Requests | Pending/rejected requests do not alter subjects; approved changes apply atomically; stale requests cannot overwrite a newer assignment. |
| Cutoff | Cover immediately before, exactly at, and after the cutoff for direct changes, requests, approvals, queued operations, and retries. |
| No late bypass | Earlier submission, admin access, delayed expiry, cutoff/calendar edits, and package-content edits cannot apply a late package change. |
| History | Retained subjects keep identities; removed-subject history remains available; marks never transfer to unrelated subjects. |
| Concurrency | Simultaneous selections/approvals, capacity races, duplicate retries, and permission revocation cannot create competing assignments. |
| Migration | Legacy identifiers and academic behavior survive mapping; ambiguous cases remain visible and unresolved without fabricated packages. |
| Existing workflows | Registration, approval/reconciliation, faculty responsibilities, attendance, examinations, published results, and subject assignment remain correct. |
| User experience | Package/context previews, complete subject lists, clear deadlines/statuses, keyboard access, mobile layout, and genuine empty/error states. |

Follow the existing layer-specific validators and regression suites when
implementation begins. Record verification output under `logs/frontend/` or
`logs/backend/`; keep files within 250 physical lines and folders within 15
direct maintained files. Database migration evidence must distinguish disposable
validation from deployed-state checks.

## Decisions used in this version

| Decision | Implemented policy |
| --- | --- |
| Cutoff | Administrator-set timestamp, capped at the calendar term midpoint; default midpoint. |
| Time boundary | UTC dated-term boundaries; reject changes at or after cutoff using the live database clock after locks. Edit/display deadlines in explicitly labeled IST. |
| Policy editing | Cutoff can only shorten; captured teaching dates and class identity stay fixed. Choice toggling never changes existing assignments. |
| Initial assignment | Choice defaults off. Authorized first assignment, or own initial choice when enabled, may occur after the change cutoff. |
| Packages | One complete package per placement; packages belong to a curriculum study semester. Shared core is added automatically. |
| Programs | Reuse existing degree/branch program records. |
| Curriculum revisions | Freeze a curriculum as soon as a class references it; use a new version for future changes. |
| Requests | One pending request per assignment. Approval/rejection carries a reason; stale requests supersede and late requests expire. No cancellation or notifications in this version. |
| Participation | End/rejoin episodes retain roster IDs, attendance and marks. Date-only attendance/test events use inclusive UTC episode dates. |
| Capacity | Validate each subject offering/section before committing the whole package; rollback all subjects on failure. |
| Authority | Exact institution capabilities; explicit staff delegation; HOD follows the program department; incharge requires an explicit class bridge. |
| Legacy migration | Explicit placement and teaching mappings; no guessed package or mass backfill. Old individual writers cannot bypass a managed package. |

Independent elective slots, automatic credit transfers, retakes, request
notifications, and automatic legacy resolution require separate product work.
