# Institution / University Admin

**Status: DRAFT — REVIEW ONLY. Canonical role: `admin`.** Read [shared rules](../shared-rules.md). Admin is the highest ordinary institutional role, with explicit institution boundaries.

## Scope and allowed responsibilities

Admin can perform supported user/membership, student, academic setup, teaching-assignment, content, and audit workflows when the required action permissions and institution scope pass. Role membership does not bypass independent account, approval, identity, resource, or audit controls.

| Operation | Relevant permission / boundary |
|---|---|
| Students Roster and Record history | `students.read`, `attendance.read`; authorized institution and academic resource. |
| Waiting approval and decisions | Queue `students.read`; decisions require `students.approve` or `students.reject`. |
| Single Student / Bulk Import registration | `students.create`; valid class placement, batch, and identity checks. |
| Send saved-registration invitations | `students.create`; authorized saved record and saved recipient. |
| Academic Setup batches | Currently `departments.manage`; institution/program/batch relationships remain checked. |
| Faculty assignments and responsibilities | `faculty.assignments.manage`; valid target, scope, and interval. |
| Direct Staff permission grants | `permissions.manage`; active same-institution Staff member and allowlisted codes. |
| Content and academic administration | Applicable action permissions and supported module workflows. |
| Audit records | `audit.read`; authorized institution context. |

Use [student registration](../workflows/student-registration.md) for shared onboarding semantics and [module policies](../module-policies.md) for other operations. Holding a role/permission code does not establish a generic implemented grant-management endpoint.

## Restrictions and compatibility details

- No implicit platform authority, cross-institution academic access, or unrestricted security bypass.
- No self-approval of privileged grants or identity decisions; formal verification/repair needs its separately approved workflow.
- The source bootstrap map contains a `university_admin` alias, but it is not another canonical primary role.
- The legacy `platform.manage` entry below does not satisfy the independent `super_admin` platform gate. Its presence is an open compatibility decision, not permission to use platform routes.

## Bootstrap permissions

**Source-observed (S02):** 60 codes in the local bootstrap map. These are not effective live grants or proof of endpoint availability. The [complete matrix](../permission-catalog.md) is the cross-role reference.

- **Profile:** `profile.own.read`, `profile.own.update`.
- **Users:** `users.read`, `users.create`, `users.update`.
- **Roles:** `roles.read`, `roles.manage`.
- **Permissions:** `permissions.read`, `permissions.manage`.
- **Students:** `students.read`, `students.create`, `students.update`, `students.delete`, `students.approve`, `students.reject`, `students.suspend`.
- **Faculty:** `faculty.read`, `faculty.create`, `faculty.update`, `faculty.approve`, `faculty.suspend`, `faculty.assignments.manage`.
- **Staff:** `staff.read`, `staff.create`, `staff.update`, `staff.approve`, `staff.suspend`.
- **Departments:** `departments.read`, `departments.manage`.
- **Courses:** `courses.read`, `courses.manage`.
- **Subjects:** `subjects.read`, `subjects.manage`.
- **Semesters:** `semesters.read`, `semesters.manage`.
- **Academic years:** `academic_years.read`, `academic_years.manage`.
- **Attendance:** `attendance.read`, `attendance.manage`.
- **Results:** `results.read`, `results.manage`.
- **Documents:** `documents.read`, `documents.create`, `documents.update`, `documents.delete`.
- **Notices:** `notices.read`, `notices.create`, `notices.update`, `notices.delete`.
- **AI:** `ai.chat`, `ai.knowledge.read`, `ai.knowledge.create`, `ai.knowledge.update`, `ai.knowledge.delete`.
- **Institution:** `institution.read`, `institution.update`, `institution.settings.manage`.
- **Organizations:** `organizations.manage`.
- **Platform:** `platform.manage`.
- **Audit:** `audit.read`.

## Relevant review cases

V03–V05, V10–V15, and V18–V20 cover grants, endpoint roles, tenant scope, separation of duties, imports, invitations, session routing, audit/commit behavior, missing policies, and injected authority. See [verification](../verification.md).

## Sources

S01–S04, S07–S12, S14–S19 in [source references](../source-references.md). Consult [route permissions](../route-permissions.md) for the specific operation rather than assuming a catalog permission grants API access.
