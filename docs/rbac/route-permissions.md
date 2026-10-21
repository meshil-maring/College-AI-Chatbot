# Representative route permissions

**CAI-RBAC-001 v1.2; DRAFT - REVIEW ONLY; 21 October 2026.** Read the [reading guide](README.md) and relevant role first. Source observations are not live-deployment certification.

All paths below have the `/api/v1` prefix. This inventory is representative, not a complete route audit. A list of permissions in a cell means that all named checks apply. Service checks can impose further eligibility, ownership, state, and academic-scope requirements.

| Operation | Endpoint role / scope gate | Named permission(s) | Additional source-observed boundary |
|---|---|---|---|
| `GET /admin/student-workspace/sections` | Institution Admin | `students.read` | Active institution sections. |
| `GET /admin/student-workspace/sections/{section_id}/students` | Institution Admin | `students.read`, `attendance.read` | Authorized institution and academic resource. |
| `GET /admin/student-workspace/sections/{section_id}/history` | Institution Admin | `students.read`, `attendance.read` | Student history within authorized class scope. |
| `GET /admin/student-workspace/sections/{section_id}/registrations` | Institution Admin | `students.read` | Saved registrations in the authorized class. |
| `POST /admin/student-workspace/sections/{section_id}/registrations` | Institution Admin | `students.create` | Saved class placement, active matching batch, identity checks. |
| `POST /admin/student-workspace/sections/{section_id}/registrations/{registration_id}/invitation` | Institution Admin | `students.create` | Saved registration and recipient must match authorized class and tenant. |
| `GET /admin/students/pending` | Institution Admin or Staff | `students.read` | Institution-scoped approval queue. |
| `POST /admin/students/{student_id}/approve` | Institution Admin or Staff | `students.approve` | Approval workflow and institution ownership. |
| `POST /admin/students/{student_id}/reject` | Institution Admin or Staff | `students.reject` | Rejection workflow and institution ownership. |
| `POST /faculty/student-registrations/sections/{scope_section_id}` | Institution-scoped Faculty | `attendance.manage` | Eligible teaching scope and matching active batch. |
| `POST /faculty/student-registrations/sections/{scope_section_id}/{registration_id}/invitation` | Institution-scoped Faculty | `attendance.manage` | Teaching scope plus saved-record/recipient validation. |
| `GET /faculty/attendance/sections/{section_id}/registration-history` | Institution-scoped Faculty | `attendance.read` in service authorization | Authorized academic section and history scope. |
| `POST/PATCH /admin/academic-setup/batches[/{record_id}]` | Institution Admin | `departments.manage` | Valid institution/program/batch relationships. |
| `GET /admin/audit-logs` | Institution Admin | `audit.read` | Institution audit context. |
| `POST /admin/staff/{user_id}/permissions` | Institution Admin | `permissions.manage` | Active Staff member in the same institution and allowlisted permission codes. |
| `GET /platform/me` | Active platform Super Admin | `platform.read` | Fresh platform authorization check. |
| `POST /platform/institutions` | Active platform Super Admin | `platform.manage` | Platform institution-management workflow. |
| `GET /platform/audit` | Active platform Super Admin | `platform.audit.read` | Platform audit context. |
| `/platform/institutions/{institution_id}/faculty-responsibilities` management routes | Active platform Super Admin | `faculty.assignments.manage` | Explicit institution-targeted responsibility management; not general academic-record access. |

**Final status: DRAFT — REVIEW ONLY.** Approval, implementation, deployed-grant verification, and restricted governance reviews remain separate, explicitly authorized activities.
