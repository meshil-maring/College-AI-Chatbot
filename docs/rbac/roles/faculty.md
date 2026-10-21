# Faculty / Teacher

**Status: DRAFT — REVIEW ONLY. Canonical role: `faculty`.** Faculty and Teacher are the same role. Read [shared rules](../shared-rules.md).

## Academic scope

An operation needs the required permission and a valid teaching assignment or explicit academic responsibility that covers the resource and action. A teaching-only operation requires the teaching path. Institution, resource ownership, assignment validity, and revocation checks still apply.

## Allowed actions and Students workspace

| Action | Relevant permission / restriction |
|---|---|
| Roster and student details | `students.read` and relevant attendance permissions; authorized academic scope. |
| Record history | `attendance.read` in service authorization; scoped student/workflow history. |
| Waiting approval | View pending students in assigned scope; this does not grant approval/rejection authority. |
| Single Student / Bulk Import registration | Current Faculty routes require `attendance.manage` and eligible teaching scope. |
| Send saved-registration invitations | Same registration authority plus saved-record/recipient scope checks. |
| Attendance marking and corrections | `attendance.manage`; valid teaching scope and supported workflow controls. |
| Examination/test management | Relevant `results.read/manage` permission, valid academic scope, and workflow state. |
| Teaching resources and AI | Applicable document/knowledge/chat permission plus resource visibility and ownership. |

Registration and invitations use the [shared student workflow](../workflows/student-registration.md). Faculty registration's use of `attendance.manage` is source-observed, not a proposed permission rename.

## Restrictions

- No automatic access to unrelated departments, classes, sections, subjects, or institutions.
- No ordinary student approval/rejection, institution-wide role/permission administration, or self-approved privileged access.
- No authoritative student identity repair through ordinary roster access.
- A responsibility title alone must not bypass its permission, scope, or validity controls.

## Scoped academic responsibilities

HOD and Class In-Charge are scoped academic responsibilities, rather than additional primary roles. **Source-observed:** Responsibility access uses a responsibility definition, permitted scope type, valid resource scope, active status, validity interval, and revocation state. Responsibility permissions remain scoped; they are not added as unrestricted role grants. **S07, S08, S09**

| Responsibility | Proposed permitted scope | Proposed capabilities | Exclusions |
|---|---|---|---|
| Head of Department | Explicitly assigned department. | Department reports, assignment oversight, and only the management operations granted by the responsibility definition. | Other departments and institution-wide user/security administration. |
| Class In-Charge | Explicitly assigned class/section and validity period. | Class student lists, attendance oversight, and permitted class reports or operations. | Unrelated classes and automatic authority to assign Faculty or manage user roles. |

Responsibility names alone must not grant actions. Exact permissions and allowed scopes must be reviewed against their definitions. Assignment management itself must require the appropriate management permission and a valid management scope. **S08**

The inspected migration files also declare scoped coordinator responsibilities. They are not additional primary roles. The following summarizes the declared migration baseline, not current live database grants. **S23**

| Responsibility code | Declared scope | Declared scoped permissions |
|---|---|---|
| `hod` | Department | `academic.department.read`, `academic.reports.read`, `attendance.overview.read`, `attendance.read`, `students.read`, `faculty.read`, `courses.read`, `departments.read`, `results.read`, `faculty.assignments.manage` |
| `class_in_charge` | Section | `academic.class.read`, `academic.reports.read`, `attendance.overview.read`, `attendance.read`, `students.read`, `results.read` |
| `program_coordinator` | Program | `faculty.assignments.manage` |
| `semester_coordinator` | Semester | `faculty.assignments.manage` |
| `course_coordinator` | Course | `faculty.assignments.manage` |

Scoped teaching management checks the actual responsibility permission and resource containment. Its service also rejects assigning oneself teaching duties. Class In-Charge does not receive assignment-management permission in these declarations. **S08, S23**

## Bootstrap permissions

**Source-observed (S02):** 18 codes in the local bootstrap map. These are not effective live grants or proof of endpoint availability. The [complete matrix](../permission-catalog.md) is the cross-role reference.

- **Profile:** `profile.own.read`, `profile.own.update`.
- **Notifications:** `notifications.own.read`, `notifications.own.update`.
- **Students:** `students.read`.
- **Attendance:** `attendance.read`, `attendance.manage`, `attendance.own.read`.
- **Results:** `results.read`, `results.manage`, `results.own.read`.
- **Documents:** `documents.read`, `documents.create`.
- **Notices:** `notices.read`.
- **AI:** `ai.chat`, `ai.knowledge.read`, `ai.knowledge.create`.
- **Faculty:** `faculty.assignments.read`.

## Relevant review cases

V03–V08, V10–V14, and V18 cover missing permissions, endpoint roles, foreign resources, assignment expiry/revocation, responsibility containment, separation of duties, imports, invitations, and commit/audit behavior. See [verification](../verification.md).

## Sources

S01–S03, S05, S07–S12, S15, S18, and S23 in [source references](../source-references.md). Use [route permissions](../route-permissions.md) when working on a particular API.
