# Academic integrity, lifecycle, and migration compatibility

Status: source review and design requirements. Read the
[audit summary](README.md), [normalization](normalization.md), and
[security findings](security-rbac.md) together.

## INT-01: curriculum identity and applicability

The [current curriculum key](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L675)
allows one row per program/subject pair. Its optional semester references a
dated calendar term; there is no named curriculum parent or version.
[Offering validation](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L116)
requires an active link whose dated semester is unrestricted or matches.

A link restricted to one dated term cannot gain another row for a later term,
independent curriculum version, or repeated study-semester placement without a
different identity/constraint design. Existing
[offerings reference that unique pair](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L868).
Changing or dropping the key in place is not a compatible curriculum upgrade.

Add a named/versioned curriculum responsibility with explicit study-semester and
subject relationships. Preserve old offering references until a verified mapping
replaces each dependency. Keep subject classifications contextual.

The [convergence migration](../../../../supabase/migrations/20261016010000_academic_curriculum_semester_convergence.sql#L24)
preserves any legacy `semester_number` values while making that column optional.
Inventory deployed columns/applicability before mapping; do not equate an old
number, a dated term UUID, and a curriculum study stage.

## INT-02: registration identity and temporal class placement

[student_registrations](../../../../supabase/migrations/20261020000000_subject_independent_student_registrations.sql#L4)
contains program, year, dated semester, section code, cohort, and identity fields,
but register/roll uniqueness is institution-wide. Service-role grants allow
SELECT/INSERT, not a documented placement-progression lifecycle.

The same student cannot simply receive another registration with the same
institutional identifier next term. Rewriting the old class context would lose
the original placement and break exact-context assignment reads.

Separate persistent registration/admission identity from temporal class
placements. Package assignments should reference the appropriate placement and
period. Decide progression, transfers, repeats, nonoverlap, historical authority,
and migration states. Retain institutional identity uniqueness.

## INT-03: shared class, batch, and teaching-group compatibility

Current classes are inferred from program/year/dated term/section code. Exact
[subject-assignment lookup](../../../../backend/app/repositories/students/subject_assignments.py#L6)
does not carry batch; [class lists](../../../../backend/app/services/students/student_registrations.py#L103)
may apply it as an optional filter. A subject section and code cannot establish
a new batch-specific shared class on their own.

[Offering uniqueness](../../../../supabase/migrations/20250717000000_reconstructed_pre_phase_3_6_baseline.sql#L560)
is subject/program/year/term, with
[section-code uniqueness](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L11)
inside each offering. Two batch-specific classes called Section A can map to
the same existing subject teaching group or collide when creating a new one.

Define explicit class identity and exact class-to-subject teaching mappings.
Decide when combined teaching across cohorts is legitimate versus when separate
groups are required. Preserve section IDs, faculty appointments, roster IDs and
academic history. Ambiguity needs review, not grouping by matching text.

## INT-04: an independent subject-participation lifecycle does not exist yet

[Roster status](../../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L16)
describes account/approval state. The
[update guard](../../../../backend/app/services/faculty/faculty_attendance.py#L504)
prevents editing it as ordinary attendance data, and
[account reconciliation](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L294)
can reset it to ACTIVE. Setting INACTIVE cannot safely mean "dropped this subject".

Other consumers need lifecycle-aware integration:

- [Attendance marking](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L140)
  validates the roster in the section, without a separate participation interval.
- [Exam completeness](../../../../supabase/migrations/20261013000000_faculty_tests_examination.sql#L293)
  considers the existing roster/account-status model.
- [Student assessment projections](../../../../backend/app/services/students/student_academic_experience.py#L346)
  consume linked rosters, without a separate package withdrawal history.

Introduce effective subject-participation history independently from account
activity. Define start/end applicability and allowed drop/rejoin episodes;
preserve roster/event IDs and the provenance of each requirement. Retained core
subjects must keep the same academic history. Ending one package requirement
must not remove a subject still required by another valid enrollment reason.

Update marking eligibility, imports, exam completeness, student pages, reporting,
and attendance denominators. Historical marks must not silently transfer to
another subject. Resolve recognition and retake policy explicitly.

## INT-05: complete packages and existing membership writers

The [current assignment service](../../../../backend/app/services/students/subject_assignments.py#L67)
creates one roster using an independent database call. Looping over it cannot
make five subject writes atomic; earlier commits survive later failures.

Inventory all paths that modify the same participation:

| Path | Integration needed |
| --- | --- |
| Administrative/faculty subject assignment | Same package, scope, eligibility, revision, cutoff, and history authority. |
| Manual roster create/update/delete | Prevent partial package membership and unsafe historical deletion. |
| Import validation and commit | Revalidate approved package/class participation at commit; preserve raw evidence. |
| Account reconciliation | Update identity/account facts without reopening ended subject participation. |
| Privileged database mutation | Restrict write surfaces and enforce invariants below the UI. |
| Attendance, examination, results projections | Read participation applicable to the event date and retain historical views. |

Evidence includes [manual writers](../../../../backend/app/services/faculty/faculty_attendance.py#L478),
[import upserts](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L250),
and [reconciliation](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L294).
Define behavior of old per-subject actions for package-managed classes; retaining
unrestricted manual edits would bypass the fixed bundle.

## INT-06: study progression and dated term number

The [roll-number requirement](../../../../backend/app/services/students/subject_assignments.py#L80)
uses a [dated semester number](../../../../backend/app/repositories/students/subject_assignments.py#L22).
[Manual roster creation](../../../../backend/app/services/faculty/faculty_attendance.py#L482)
uses the same interpretation. A later-year student in a calendar Term 1 can
receive the first-study-semester exemption under that calendar setup. Actual
deployed effect depends on term numbering and was not measured.

Identify every progression-dependent rule and base it on the student's class
study semester. Keep the academic term for dates, availability and teaching
context; the two references have different meanings.

## Required atomic package operation

1. Resolve authenticated actor, student identity, class placement, and requested
   package/version. Reject foreign or incompatible references.
2. Acquire assignment and affected capacity locks in a defined order. Recheck
   live authority/revocation, source revision, eligibility and availability.
3. For a change, check authoritative current time after waits and immediately
   before mutation. Submission/transaction start before cutoff is insufficient.
4. Calculate retained, added and ended participation using stable identities;
   preserve shared memberships and previous event history.
5. Commit complete membership changes, assignment revision, request decision,
   and audit together, or leave all original state unchanged.
6. Enforce one active package in the agreed scope, idempotent retries, stale
   request detection, and capacity uniqueness in the authoritative write path.

This is a future design requirement. No such package operation exists in the
inspected source, and no lock/transaction behavior was runtime-validated.
