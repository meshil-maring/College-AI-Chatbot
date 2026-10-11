# ADR-ENROLLMENT-002: Student Identity, Enrollment Episodes, and Academic Placement

- **Status:** Proposed; awaiting product/design approval
- **Date:** 2026-10-11
- **Scope:** College AI Chatbot student identity, academic membership, placement history, and historical access
- **Implementation status:** Not implemented. No SQL or database operations were performed to prepare this record.

## Context

The current application uses one `students` row as both the stable account-linked student identity and the source of current institution/program/year context. Registration may create a pending student before program or academic-year details are known. Attendance, results, faculty-roster reconciliation, and result visibility also use the current student row.

A table-only enrollment migration would create a second source of truth. The design must represent readmission, transfers, promotions, semester repeats, historical identifiers, and published records without changing `students.student_id` or silently rewriting history.

## Proposed decisions

### D1. Stable identity

Keep `students` as the stable person/profile record and preserve its one-to-one `user_id` relationship. Admission, readmission, transfer, and program changes do not create a second student identity.

### D2. Enrollment scope

One `student_enrollments` row represents one admission episode at one institution for one verified program. Institution and program are immutable for that episode. A program change creates a new episode linked to its predecessor. Institution transfers close the source episode and create a destination episode.

### D3. Enrollment lifecycle and approval

Keep enrollment approval separate from account/registration approval and from lifecycle status.

Proposed lifecycle values:

- `pending_admission`
- `active`
- `on_leave`
- `graduated`
- `withdrawn`
- `transferred_out`
- `cancelled`

Proposed approval values: `pending`, `approved`, `rejected`.

An episode can become `active` only after the enrollment decision is approved, required identifiers and academic ancestry are verified, and an explicit effective date is supplied. A future effective date does not grant current academic authority before activation. Rejection closes an unactivated application as `cancelled`; reconsideration creates a new episode with provenance.

### D4. Operational cardinality — requires explicit approval

Recommended initial rule: at most one approved enrollment per student may be in `active` or `on_leave` state at a time. Pending applications and terminal historical episodes may coexist. This reduces ambiguity in the existing single-context authentication and frontend contracts. It intentionally does not support concurrent active dual-program enrollments in the first release.

This is a product policy recommendation, not a verified institutional rule. Do not implement the partial unique constraint until approved.

### D5. Academic placement history

Store semester/year placement separately in `student_academic_placements`. An enrollment describes admission; a placement describes an academic period and attempt. Promotion or a repeated semester creates another placement instead of overwriting the previous year/semester. Use half-open effective intervals (`starts_on` inclusive, `ends_on` exclusive).

Do not put `section_id` on a placement as the canonical class identifier: sections in the existing model are subject-offering-specific. Store an optional class/section code as a label if required. Continue using faculty attendance rosters for subject-section membership; a placement must not automatically enroll a student into every subject.

### D6. Institutional identifier ownership

Use `student_institution_identifiers` to preserve institutional identifiers independently of enrollment episodes. Candidate kinds: `student_number`, `register_number`, and `university_roll_number`. An institution/kind/normalized value belongs to one student identity; the same identity can reference the same identifier in a readmission episode. A different student cannot inherit a previously assigned value in the initial release.

Normalize by trimming surrounding whitespace while preserving original display text and leading zeros. Do not case-fold values until the institution's rules are confirmed. Account email is not an institutional identifier. Identifier changes create a new assignment record; events retain the previous and new identifier references.

### D7. Event history

`student_enrollment_events` is append-only from application paths. Events record state transitions, approvals, placements, identifier changes, corrections, transfer correlation, actor, source, reason, effective date (nullable only where the historical date is genuinely unknown), and recorded timestamp. Each event has a per-enrollment sequence and an idempotent operation ID.

State changes, events, security audit entries, and required reconciliation must commit or roll back together. Actor accounts should be retained or anonymized rather than deleted; use restrictive actor foreign-key deletion behavior so FK-driven updates do not conflict with an append-only trigger.

### D8. Historical access

A student may read their own published records from approved historical episodes while the account and institution-access policy permits it. Graduation, withdrawal, transfer, or promotion must not automatically turn published historical results into drafts. Historical access does not confer current roster membership or staff permissions. Faculty/admin access remains scoped to the institution and record they are authorized to manage.

### D9. Legacy compatibility

Preserve `students.student_id` and existing attendance, result, test-result, roster, and notification keys. Add enrollment associations only after deterministic mapping rules are approved. Keep legacy fields and reads during a compatibility period; compare old and new projections before cutover. Never infer an academic admission date from the current registration timestamp.

### D10. Security boundary

No browser role receives direct table writes to the new enrollment objects. RLS and explicit grants must be verified, and write operations should use reviewed, narrowly scoped routines. Backend service-role use still requires server-side tenant, identity, enrollment, resource, and role checks because privileged service access can bypass RLS.

## Required invariants

1. Program ownership is validated through `programs.department_id -> departments.institution_id`.
2. Academic year and semester ancestry is validated and cannot cross institutions.
3. Enrollment institution/program are immutable after creation; transfers create new episodes.
4. Historical record ownership and result publication do not derive solely from the student's current enrollment.
5. Enrollment/event/identifier/placement writes are atomic and concurrency-safe.
6. Retries with the same operation ID and same payload are idempotent; reuse with different input fails.
7. Ambiguous legacy mappings remain unresolved/quarantined; no dates or academic associations are fabricated.

## Open approval gates

- Approve or amend the single operational enrollment rule.
- Confirm whether `inactive` legacy status means leave, closed enrollment, or another state.
- Confirm institution-specific identifier case/normalization policy and identifier reuse policy.
- Confirm historical access when an institution is inactive or archived.
- Recover and inspect the exact enrollment SQL draft before using it as a basis for a revised migration.
- Reconcile conflicting historical database ACL snapshots against a named database, revision, role, and collection timestamp.

## Consequences

This model adds `student_enrollments`, `student_academic_placements`, `student_institution_identifiers`, and `student_enrollment_events`. It requires coordinated backend, trigger, frontend-contract, and cache changes. It is not a table-only migration and is not approved for execution by this ADR.
