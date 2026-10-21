# Using the shared permission helper

This is an implementation guide for the shared UI helper. The broader RBAC specification remains a review draft. Backend role, tenant, academic-scope, ownership, and workflow guards still decide API access.

## Check the signed-in user in React

```tsx
import { usePermissions } from './features/auth/access/usePermissions.ts'

const { can, canAll, canAny, permissions } = usePermissions()

can('students', 'update')
can('students.update')
can('profile', 'own', 'read')
can('platform', 'audit', 'read')
canAll('students.read', 'attendance.read')
canAny('students.approve', 'students.reject')
permissions.students.delete // Current user's boolean, including false values.

// Example inside a component:
// {can('students', 'update') && <button>Edit student</button>}
```

Checks use the authenticated user's `effective_permissions` supplied by the server. Missing permissions, an unauthenticated/restoring session, unknown permission paths, and empty combined checks are denied. A new server grant list updates both `can(...)` and the nested boolean tree. This does not introduce a new permission-refresh mechanism.

Faculty responsibility grants remain in their existing scoped context. This hook does not merge HOD/coordinator grants into institution-wide permissions; retain the relevant academic-scope checks for those operations.

## Inspect role defaults

```ts
import { permissionsByRole } from './features/auth/access/rbac.ts'

permissionsByRole.admin.students.update // true
permissionsByRole.admin.students.delete // true
permissionsByRole.staff.students.create // false
permissionsByRole.faculty.students.approve // false
permissionsByRole.student.attendance.own.read // true
```

This read-only map is a bootstrap reference derived from existing backend defaults. Use `usePermissions()` for a real user's buttons and actions; direct grants, revocation, role eligibility, and scope can differ from bootstrap defaults. The map is not permission to call an otherwise restricted endpoint. Public visitors have no authenticated role entry.

## Use outside React

```ts
import { createPermissions } from './features/auth/access/rbac.ts'

const access = createPermissions(serverUser.effective_permissions)
access.can('students', 'update')
access.permissions.students.update
```

This creates an immutable snapshot. Create a new snapshot after the server grant list changes. Existing `hasPermission(grants, code)` imports from `features/auth/access/permissions.ts` delegate to the same central implementation, preserving existing exact/resource-wildcard matching.

## Maintain one source

| File | Responsibility |
|---|---|
| `backend/app/core/permissions.py` | Canonical permission vocabulary and existing bootstrap role defaults. |
| `backend/scripts/generate_frontend_rbac.py` | Generates the typed frontend snapshot without settings or database access. |
| `frontend/src/features/auth/access/rbacPolicy.generated.ts` | Generated vocabulary and defaults; do not edit manually. |
| `frontend/src/features/auth/access/rbac.ts` | Nested role reference, typed effective-permission checks, and compatible string checker. |
| `frontend/src/features/auth/access/usePermissions.ts` | Authenticated React adapter with memoized current-user access. |

After changing the canonical catalog/defaults, run from `backend/`:

```powershell
uv run python scripts/generate_frontend_rbac.py
uv run python scripts/generate_frontend_rbac.py --check
```

The backend parity test detects a stale frontend snapshot. Changing bootstrap defaults does not automatically change effective database grants. Grant changes require their existing authorized workflow. Backend code continues using `authorize_permissions(current_user, 'students.update')` together with the endpoint's existing role and resource guards.
