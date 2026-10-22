# Security, RBAC, tenant boundaries, and current findings

Status: local-source review. See the [summary](README.md). Live grants, policies,
routine owners, exposures, and deployed behavior have not been inspected.

## Existing controls to preserve

| Control | Source evidence / limit |
| --- | --- |
| JWT identity resolves to database user, role, and institution state. | [Identity resolution](../../../../backend/app/core/security/identity.py#L43). |
| Real resolved requests use current effective permissions rather than falling back to role defaults. | [Permission check](../../../../backend/app/core/security/permissions.py#L17). |
| Institution roles and academic scope fail closed on missing/foreign context. | [Scope containment](../../../../backend/app/services/auth/authorization.py#L57); [institution dependency](../../../../backend/app/core/security/dependencies.py#L47). |
| Academic reads traverse institution-owned ancestors and project readable entities. | [Catalogue reads](../../../../backend/app/services/academics/academic_setup.py#L74). |
| Academic master writes check actor, institution, permissions, ancestry, and immutable relationships; write and audit share an RPC transaction. | [Master mutation](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L155), [write/audit](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L225). |
| Academic RLS is enabled; browser-role table/RPC privileges are revoked. | [Table policy/grants](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L142), [RPC grants](../../../../supabase/migrations/20261016000000_academic_master_data_management.sql#L242). |
| Registrations and batches have tenant checks and restricted grants. | [Registration guard](../../../../supabase/migrations/20261020000000_subject_independent_student_registrations.sql#L27), [batch grants](../../../../supabase/migrations/20261020010000_academic_batches.sql#L133). |
| Batch selection is protected against concurrent deactivation. | [Active-batch lock](../../../../supabase/migrations/20261020010000_academic_batches.sql#L57). |
| Student identity and academic eligibility derive from authenticated context. | [Student context](../../../../backend/app/services/students/student_context.py#L52). |

The backend [service-role client](../../../../backend/app/db/supabase.py#L20)
intentionally bypasses RLS. Browser revokes do not replace server filtering,
operation permissions, reference validation, or restricted transactional writers.

## SEC-01: high, attendance can be lost during roster deletion

**Current issue.** [delete_roster](../../../../backend/app/services/faculty/faculty_attendance.py#L512)
reads attendance at line 518 and marks at line 521, then issues a separate DELETE
at line 526. The attendance [roster foreign key](../../../../supabase/migrations/20261010000000_phase_10_faculty_attendance_management.sql#L45)
uses `ON DELETE CASCADE`. The application's earlier empty-history check cannot
protect records committed between that read and the delete.

A concurrent [attendance write](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L140)
can lock the roster, insert attendance, and commit after the empty-history read;
the later delete can cascade those new records. Marks have
[restrictive FK protection](../../../../supabase/migrations/20261013000000_faculty_tests_examination.sql#L39);
that does not protect attendance. This is a source-inferred
race mechanism, not a reproduced incident in the live database.

Resolve deletion authorization/history checks in one locked transaction and
define database-level preservation. For packages, end subject applicability
through a separate participation lifecycle; do not delete/recreate rosters.

## SEC-02: medium, manual creation has weaker academic eligibility

**Current issue.** [create_manual](../../../../backend/app/services/faculty/faculty_attendance.py#L478)
checks teaching scope, tenant-local identifiers, and account state, then links
an approved student. Its [identity match](../../../../backend/app/services/faculty/faculty_attendance.py#L299)
does not compare the student's program/year to the target section.

Imports [explicitly reject those mismatches](../../../../backend/app/services/faculty/faculty_attendance.py#L446),
as does the [subject-assignment identity check](../../../../backend/app/services/students/subject_assignments.py#L16).
The [database context guard](../../../../supabase/migrations/20261012000000_faculty_attendance_workflow.sql#L10)
checks the linked student's tenant, not their program/year.

An assigned teacher knowing another student's identifiers can therefore link a
same-institution student from a different program/year through manual creation.
This is an academic-scope/integrity gap, not evidence of a cross-tenant leak.
Make eligibility consistent across every membership writer, with explicit
exceptions only where the academic policy deliberately permits them.

## SEC-03: medium, assignment and audit commit separately

**Current issue.** The [subject roster insert](../../../../backend/app/repositories/students/subject_assignments.py#L28)
commits before the [admin route audit](../../../../backend/app/api/admin/student_records/student_workspace.py#L84)
or [faculty route audit](../../../../backend/app/api/faculty/registrations.py#L62).
An audit failure leaves the membership intact; an idempotent retry returns
`already_assigned` and skips the missing event. The same separate-write pattern
also exists in class-registration routes.

Use a transaction covering assignment, complete memberships, request decision,
and audit. The existing academic-master RPC is a useful atomic pattern, although
its admin-only authority is not a complete authorization model for new actors.

## SEC-04: medium, privileged audit retention needs hardening

**Current source hardening gap.** The [initial grants](../../../../supabase/migrations/20260909000000_phase_admin_1_admin_student_schema.sql#L566)
give `service_role` ALL on `admin_audit_log`. A later
[INSERT grant](../../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L123)
does not revoke earlier privileges. The
[append-only trigger](../../../../supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql#L516)
covers row UPDATE/DELETE, not TRUNCATE. The inspected migration chain has no
corresponding audit-table TRUNCATE revocation/guard.

This concerns the trusted service role's effective privilege surface; it does
not establish an ordinary browser/API route capable of truncation. Check actual
grants, defaults, routine exposure, ownership and approved retention needs before
changing privileges. The separately protected B05 lifecycle table does not prove
equivalent protection of `admin_audit_log`.

## Package authorization gaps

These are new-model integration requirements, not evidence of existing package
endpoints that can already be exploited.

### RBAC-01: current route gates do not implement the agreed actor matrix

[Academic Setup](../../../../backend/app/api/academics/academic_setup.py#L13)
and admin workspace routes require institution admin. Faculty assignment uses
[teaching_only](../../../../backend/app/services/students/subject_assignments.py#L68),
which [omits responsibility grants](../../../../backend/app/services/faculty/faculty_responsibilities.py#L146).
Staff delegation and the permission catalogue have no package capabilities.
HOD/class incharge are responsibilities, not new base roles.

| Operation | Proposed authority and scope |
| --- | --- |
| Configure curricula/packages and class rules | Explicit management capability; institution/program/class scope as appropriate. |
| Initial administrative assignment | Explicit assignment capability, eligible student placement, allowed class package. |
| Student first selection | Authenticated own-student identity, eligible own placement, admin choice flag, no existing assignment. |
| Student change request | Own current assignment and available target; before cutoff; cannot apply the change. |
| Review/apply change | Explicit capability plus active institution/class/department responsibility; before cutoff and against current revision. |
| View history | Own-student history or explicitly permitted academic/audit scope. |

Final permission codes/grants remain to be designed. Do not turn all teachers
into package managers or add unscoped role defaults to satisfy a UI button.

### RBAC-02: class department and subject department must be separate

[Section resources](../../../../backend/app/services/auth/phase81_rbac.py#L81)
currently take `department_id` from the subject. An open elective can be owned
by a different department from the student's program. Define class/program
department explicitly for package HOD authority and preserve subject ownership
for teaching/subject administration; do not reuse one ambiguous department field.

### Class and batch identity

[Current section containment](../../../../backend/app/services/auth/authorization.py#L61)
uses program/year/term/section code, with no batch. The
[exact registration lookup](../../../../backend/app/repositories/students/subject_assignments.py#L6)
uses the same class tuple. Optional batch list filters do not change authority.
Package operations must resolve explicit class, batch and student placement
relationships before authorizing or assigning subjects.

## Required write boundary and bypass inventory

One authoritative operation must lock the relevant assignment and capacity
resources, then revalidate live authority, ownership, current revision, package
version/class availability, subject mappings, eligibility, and current deadline.
Use authoritative current time after waits, immediately before mutation; a
transaction-start timestamp cannot establish that a queued change is still timely.

Commit complete memberships, assignment revision, request state and audit
together. Enforce retries, uniqueness, and capacity races at that boundary.
Once the deadline passes, no admin override, stale request, package-content edit,
or policy/date edit may reopen an ordinary change path.

Include manual roster create/update/delete, imports, reconciliation, admin
subject assignment, faculty subject assignment, and any direct privileged writer
in the integration inventory. A new secure package endpoint alone does not keep
those old writers from drifting away from the chosen package.
