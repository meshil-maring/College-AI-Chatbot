# RBAC documentation

**CAI-RBAC-001 · Version 1.2 · 21 October 2026 · DRAFT — REVIEW ONLY**

Role-Based Access Control (RBAC) combines roles, permissions, account eligibility, institution membership, resource ownership, and academic assignments. This documentation separates proposed policy from selected behavior observed in the local source. It does not certify a deployment or approve permission changes.

## Read only what the task needs

Start with this index and [shared rules](shared-rules.md), then read the affected role. Open the longer references only when they are relevant. Do not load every role document by default. For a shared-component change, include each role whose behavior changes.

| Task or user | Role document | Additional reading when needed |
|---|---|---|
| Add a permission check in code | Affected role | [Shared permission helper](permission-checking.md). |
| Public visitor or anonymous chat | [Public](roles/public.md) | [Module policies](module-policies.md) for public retrieval. |
| Student account or personal academic data | [Student](roles/student.md) | [Student registration](workflows/student-registration.md) for onboarding. |
| Faculty, Teacher, HOD, or coordinator | [Faculty](roles/faculty.md) | [Student registration](workflows/student-registration.md) or [route permissions](route-permissions.md). |
| Staff approval or delegated duties | [Staff](roles/staff.md) | [Student registration](workflows/student-registration.md) for approval boundaries. |
| Institution or University Admin | [Admin](roles/admin.md) | The relevant workflow and route entries. |
| Platform administration | [Super Admin](roles/super-admin.md) | Platform entries in [route permissions](route-permissions.md). |
| Permission comparison across roles | Affected roles only | [Permission catalog](permission-catalog.md). |
| Authorization review or policy approval | Affected roles and modules | [Verification and open decisions](verification.md), then relevant [sources](source-references.md). |

## File ownership

| File | Owns |
|---|---|
| `permission-checking.md` | How to use the implemented shared helper and regenerate its backend-derived role reference. |
| `shared-rules.md` | Common authorization, scope, session, enforcement, and audit rules. |
| `roles/*.md` | Role-specific actions, restrictions, scope, bootstrap summaries, and review cases. |
| `permission-catalog.md` | The complete source-defined permission vocabulary and bootstrap comparison matrix. |
| `workflows/student-registration.md` | Shared Students navigation, class registration, invitations, and account approval. |
| `module-policies.md` | Module-specific controls, formal identity verification, and AI retrieval requirements. |
| `route-permissions.md` | Representative API role/permission requirements; not an exhaustive route audit. |
| `source-references.md` | Repository evidence IDs used throughout the documentation. |
| `verification.md` | Future verification scenarios, unresolved decisions, and approval/change control. |

## Evidence labels

- **Source-observed:** Found in the cited local source; deployment and effective live grants remain unverified.
- **Session requirement:** An explicit product decision from this work, including preserving Staff's existing Students access.
- **Proposed requirement:** A reviewable rule. MUST is required by the proposed policy; SHOULD permits a documented exception. Neither asserts that implementation is complete.
- **Unverified:** Evidence has not been established by this documentation review.

Source IDs such as S01 refer to [source references](source-references.md). Executable guards take precedence over historical reports or stale code comments. Canonical roles are `student`, `faculty`, `staff`, `admin`, and `super_admin`; Public is not an authenticated role. Faculty and Teacher are the same role.

## Maintenance and approval

Edit common rules in their owning file and link to them from role documents. Keep source-derived role summaries and the permission catalog synchronized with `backend/app/core/permissions.py`. Document discrepancies as open decisions; documentation must not silently grant a capability.

This split supersedes the standalone version 1.1 for future documentation maintenance. The original attachment and standalone exports remain unchanged. The reorganization changed documentation only; the [shared helper](permission-checking.md) was implemented under a later explicit request. The specification does not independently authorize permission provisioning, migrations, live database access, deployment, or restricted B05/E23 review. Application tests for the helper do not certify the broader draft policy. Policy owner and approver remain unassigned.
