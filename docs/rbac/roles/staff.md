# Staff

**Status: DRAFT — REVIEW ONLY. Canonical role: `staff`.** Read [shared rules](../shared-rules.md). Preserve current role permissions when reusing interface components.

## Institution and job-function scope

Staff operations require active institution-scoped Staff eligibility, the endpoint's permitted role, and the relevant permission. A permission listed in the bootstrap map does not prove that the Staff panel exposes the corresponding module or that an Admin/Faculty endpoint accepts Staff.

## Current Students access

**Session requirement and source-observed — S04, S13:** The Staff Students workspace remains approval-only.

| Action | Boundary |
|---|---|
| Waiting approval | Institution-scoped queue; `students.read`. |
| Approve | `students.approve`, supported approval state, and institution ownership. |
| Reject | `students.reject`, supported rejection state, and institution ownership. |
| Roster / Record history | Not exposed in the current Staff Students workspace. |
| Single / Bulk student registration | No access through the current Admin or Faculty registration routes. |
| Send class-registration invitations | No new Staff access. |

Shared navigation, filters, and approval components do not expand Staff authority. See [student registration](../workflows/student-registration.md) for shared state definitions.

## Direct permission delegation

**Source-observed:** The direct-Staff delegation allowlist contains:

- `ai.knowledge.create`
- `attendance.read`, `attendance.manage`
- `results.read`, `results.manage`
- `students.read`, `students.update`
- `documents.read`, `documents.create`, `documents.update`
- `notices.read`, `notices.create`, `notices.update`

It does not include role management, permission management, student creation, or student approval/rejection delegation. Some approval permissions already appear in the Staff role bootstrap set; inherited permissions and direct grants are different mechanisms. Removing a direct grant does not remove the same permission inherited from a role. A listed permission still needs an endpoint that accepts the caller's role and scope. **S02, S10**

## Restrictions

- No unrelated institution's records or administrative operations outside the assigned job function.
- No self-approval of a registration, identity decision, or privileged grant.
- No role/permission management by virtue of being Staff.
- No implicit official-register verification or identity repair from a generic student/document permission.

## Bootstrap permissions

**Source-observed (S02):** 19 codes in the local bootstrap map. These are not effective live grants or proof of endpoint availability. The [complete matrix](../permission-catalog.md) is the cross-role reference.

- **Profile:** `profile.own.read`, `profile.own.update`.
- **Notifications:** `notifications.own.read`, `notifications.own.update`.
- **Students:** `students.read`, `students.update`, `students.approve`, `students.reject`.
- **Attendance:** `attendance.read`, `attendance.manage`.
- **Results:** `results.read`.
- **Documents:** `documents.read`, `documents.create`, `documents.update`.
- **Notices:** `notices.read`, `notices.create`, `notices.update`.
- **AI:** `ai.chat`, `ai.knowledge.create`.

## Relevant review cases

V03–V05, V09–V10, and V17 cover revoked grants, disallowed endpoint roles, tenant boundaries, unchanged Staff Students access, self-approval, and stale sessions. Inherited role permissions and direct grants must be assessed separately. See [verification](../verification.md).

## Sources

S01–S04, S10, S13, and S16 in [source references](../source-references.md). Read [module policies](../module-policies.md) only for the assigned operational function.
