# Preimplementation audit: academic schema, normalization, security, and RBAC

Historical baseline: the findings below describe the preimplementation source.
See [Implementation and validation](../implementation.md) for the local fixes,
new schema, settled policy, and current verification evidence.

Reviewed: 2026-10-21 (Asia/Calcutta). Status: source review completed; findings
and design blockers remain open. This is a review of the
[curriculum/package proposal](../README.md), not an implementation or migration.

## Conclusion

The existing model provides useful tenant, permission, identity, academic-master,
and teaching-section safeguards. It cannot support the proposed package workflow
unchanged. Resolve the current issues and settle the relationship/lifecycle
design before coding the package feature.

The academic data is relational, but it is not uniformly in strict second or
third normal form. Some repeated tenant/calendar/context fields are deliberate
and protected by constraints or triggers. Preserve those safeguards while
normalizing new curriculum, package, class-placement, and participation records.

No existing duplicate-row count or live security posture has been established.
Source-defined constraints are evidence of intended protection, not proof that
the current database has applied them or that all existing rows are consistent.

## Scope and evidence limits

- Reviewed local migrations through
  `20261020020000_student_registration_invitation_delivery.sql`, relevant current
  schemas/services/repositories/routes, permission declarations, and the proposal.
- Included existing uncommitted workspace changes in the inspected source.
- Historical status/review documents were context, not proof of deployed state.
- No application, migration, schema export, RBAC grant, student, or database row
  was changed. No database connection, SQL execution, migration replay, email,
  deployment, or remote operation was performed.
- Ran source-only structure/RBAC checks and selected tests with database doubles.
  Passing these tests does not establish live RLS, grants, data quality, or race
  safety. See [verification and remaining evidence](verification.md).

## Reading order

1. [Normalization and duplication](normalization.md): 1NF, 2NF, 3NF, candidate
   keys, controlled redundancy, and target relationship rules.
2. [Security and RBAC](security-rbac.md): existing safeguards, current findings,
   actor/scope gaps, and the required transaction boundary.
3. [Integrity and migration](integrity-migration.md): class identity, progression,
   historical participation, old writers, and compatibility decisions.
4. [Verification](verification.md): checks performed, missing live evidence, and
   required validation before release.

## Current-source findings

Severity reflects consequence in the relevant workflow, not a claim of a known
incident or external exploit. Each finding has source evidence in the linked
detail page.

| ID | Severity | Finding | Required direction |
| --- | --- | --- | --- |
| SEC-01 | High | A separate empty-history check and roster DELETE can race with attendance creation; the roster FK cascades attendance deletion. | Lock and validate history in one authoritative operation; package withdrawal must preserve participation history. |
| SEC-02 | Medium | Manual roster creation omits the program/year eligibility checks used by imports and subject assignment. | Make academic eligibility consistent across membership writers. |
| SEC-03 | Medium | Subject membership commits before its audit event; a retry can skip the missing audit. | Commit assignment, memberships, decision, and audit together. |
| SEC-04 | Medium | Source grant history gives the service role broad audit-table privileges, while the append-only row trigger does not cover TRUNCATE. | Verify effective privileges and harden audit retention; this is privileged access, not a demonstrated browser route. |
| INT-06 | Medium | First-study-semester eligibility is inferred from the dated calendar term number. | Use explicit student/class study progression for progression-dependent rules. |

## Blockers specific to the proposed model

These are incompatibilities or missing planned capabilities. They must not be
misrepresented as defects in a currently implemented package feature.

| ID | Priority | Blocker |
| --- | --- | --- |
| INT-01 | High | One program/subject curriculum link cannot represent named, parallel, versioned curricula or repeated applicability; existing offerings reference its unique pair. |
| INT-02 | High | A persistent institution-unique registration also stores one fixed term/class; it cannot be reused unchanged as per-term placement history. |
| INT-03 | High | Current inferred class scope omits batch; subject-owned section IDs and codes do not identify a new shared class. |
| INT-04 | High | Roster account/approval status is not effective subject participation; no independent end/rejoin lifecycle currently exists. |
| INT-05 | High | Existing single-subject/manual/import/reconciliation paths lack complete package, version, approval, and cutoff integration. |
| RBAC-01 | High | Existing admin/faculty gates and teaching-only assignment do not provide the agreed staff/HOD/class-incharge/student package operations. |
| RBAC-02 | High | The subject's department is currently used in section resources; class/program department must be distinguished for package HOD authority. |

## Normalization and duplication assessment

| Area | Result |
| --- | --- |
| 1NF | Subject relationships are individual rows/scalar keys; no operational CSV subject collection was found in the inspected model. Provenance JSON is not automatically a defect. |
| 2NF | A blanket pass is incorrect. Minimal natural keys expose partial dependencies despite UUID primary keys, such as section-derived context repeated on roster rows. |
| 3NF / BCNF | Not strict throughout: year, tenant, and other context facts can depend on non-key academic references. Some redundancy is explicitly guarded. |
| Actual duplicate rows | Not measured. No live data was queried. Unique/index definitions alone do not certify semantic or historical consistency. |
| Repeated subject memberships | One membership per student/subject teaching section is legitimate. Duplicating shared core sections or memberships per package would be harmful. |
| New subject collections | Use relationship tables with uniqueness and compatible curriculum/class scope; do not encode authoritative subject membership in a name, code, CSV, or JSON payload. |

## Required order before implementation

1. Agree on persistent student/admission identity, temporal class placements,
   curriculum versions, study semesters, and effective subject participation.
2. Specify candidate keys, uniqueness, foreign keys, tenant consistency, and
   ownership of every repeated value.
3. Resolve current findings and define how every membership writer obeys the
   same eligibility, package, deadline, history, and permission rules.
4. Define package capabilities and class/batch/department scope, including
   responsibility-based HOD/class-incharge access and own-student operations.
5. Inventory deployed catalog and aggregate data quality before mapping legacy
   classes/curricula or enabling a class for packages.
6. Validate transaction, capacity, deadline, revocation, and deletion races in a
   disposable environment; then run affected regression checks.

The review does not propose deleting repeated tenant fields merely to claim
3NF, dropping identity uniqueness, guessing legacy package assignments, or
rebuilding old rosters in place. Remaining product choices stay visible in the
[implementation plan](../implementation-plan.md#decisions-still-to-settle).
