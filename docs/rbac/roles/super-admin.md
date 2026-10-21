# Platform Super Admin

**Status: DRAFT — REVIEW ONLY. Canonical role: `super_admin`.** Read [shared rules](../shared-rules.md). Platform authority is distinct from institution Admin and is not inherited from a missing institution ID.

## Platform scope

**Source-observed — S01, S06:** Protected platform routes require the canonical Super Admin role, an active account and platform grant, a fresh platform authorization check, and the operation's named permission. An institution ID in a platform path identifies a target resource; it does not establish the caller's authority.

## Supported responsibilities

| Operation | Relevant permission / scope |
|---|---|
| Read platform identity and institution information | Endpoint-specific `platform.read`. |
| Institution lifecycle and supported administrator/invitation workflows | Endpoint-specific `platform.manage` and workflow controls. |
| Platform audit | `platform.audit.read`; authorized platform investigation context. |
| Explicit institution-targeted Faculty responsibilities | `faculty.assignments.manage` through the protected platform workflow. |
| Other platform configuration or user/permission functions | Only where an implemented endpoint and its policy authorize them. Catalog presence alone is insufficient. |

## Restrictions

- No implicit right to every student's private academic records or every tenant endpoint.
- No bypass of independent identity, approval, audit, or resource controls.
- No public registration that selects a Super Admin role. The existing platform onboarding design uses its separate controlled invitation/provisioning workflow.
- Explicit platform management of Faculty responsibilities does not grant general attendance, results, or student registration access.

## Bootstrap permissions

**Source-observed (S02):** 19 codes in the local bootstrap map. These are not effective live grants or proof of endpoint availability. The [complete matrix](../permission-catalog.md) is the cross-role reference.

- **Profile:** `profile.own.read`.
- **Users:** `users.read`, `users.create`, `users.update`, `users.delete`.
- **Roles:** `roles.read`, `roles.manage`.
- **Permissions:** `permissions.read`, `permissions.manage`.
- **Faculty:** `faculty.assignments.manage`.
- **Institutions:** `institutions.read`, `institutions.create`, `institutions.update`, `institutions.delete`.
- **Platform:** `platform.read`, `platform.manage`, `platform.settings.manage`, `platform.audit.read`.
- **Audit:** `audit.read`.

## Relevant review cases

V03–V05, V10, and V17–V20 cover permissions versus role eligibility, target institution scope, separation of duties, revoked platform grants, commit/audit behavior, missing policies, and injected authority. See [verification](../verification.md).

## Sources

S01–S03, S06–S08, S16, and S22–S23 in [source references](../source-references.md). Use the platform entries in [route permissions](../route-permissions.md) for operation-specific checks.
