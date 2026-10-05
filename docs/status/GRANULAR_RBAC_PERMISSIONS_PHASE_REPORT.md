# Granular RBAC Permissions Phase Report

Date: 2026-10-05

## PHASE STATUS

**INCOMPLETE**

This increment adds a database-backed permission catalogue and role-grant
projection, permission checks on selected backend surfaces, and permission-aware
role navigation. It is not a complete RBAC rollout: endpoint coverage is
partial, permission administration and some UI controls are missing, and the
database migration could not be replayed locally.

## Audit and architecture

The existing authentication and tenancy architecture remains authoritative:

```text
Verified Supabase JWT
  -> get_current_user()
  -> public.users
  -> active user_roles -> roles -> role_permissions -> permissions
  -> effective_permissions
  -> permission check + existing role/tenant/ownership checks
  -> /api/v1/auth/me -> frontend role shell
```

- The existing `admin` role remains the University Admin role; it was not
  renamed.
- Existing institution scope, role checks, resource ownership, and tenant
  guards remain in place. A permission grant does not replace those controls.
- `permissions` and `role_permissions` are reused. No direct-user override
  table or second role-resolution mechanism was introduced.
- The default permission matrix is used only by internal/dependency-overridden
  contexts without a resolved database grant projection. Real requests use the
  database-resolved set, and an empty set remains denied.

## Permission catalogue and role grants

- Added a canonical permission-code catalogue and default role matrix in
  `backend/app/core/permissions.py`.
- The matrix covers profile, user and role administration, academic records,
  attendance, results, documents, notices, AI, institution, platform, and audit
  capabilities.
- Added an idempotent migration to seed permission records and initial
  `role_permissions` grants for the established roles.
- Role grants are unioned from the active role assignments returned for a
  user. Inactive roles and inactive permissions do not contribute grants.
- Wildcard permission matching supports exact permission codes and
  resource-level `resource.*` grants.

## Backend authorization

- Added permission-aware dependencies and direct authorization helpers with
  structured denial logging.
- Added explicit permission policies to the University Admin and Platform
  routers. A route without a policy fails closed; existing role/scope and
  tenant checks remain active.
- Added checks for selected student-owned profile, academic, attendance,
  results, notice, and learning-resource surfaces; authenticated chat and
  conversation reads; knowledge ingestion; notifications; and development
  password-reset functionality.
- The general database identity projection retains its prior default contract.
  The authentication dependency requests the additive permission projection
  only where required.
- `/api/v1/auth/me` adds `effective_permissions`; it does not expose internal
  role assignments, scope metadata, or the permission-resolution flag.
- Student self-service permission checks run after their existing own-resource
  lookup. This preserves established missing-profile, invalid-identifier, and
  ownership response behavior; the services continue to resolve the resource
  from the authenticated user's identity and enforce tenant/ownership rules
  before a result is returned.

## Tenant and resource scoping

- Effective permissions are resolved from active server-owned role grants, not
  from client-supplied role, institution, or permission values.
- Admin and platform route policies supplement rather than bypass existing
  institution/platform authorization.
- Student services continue to bind self-service access to the authenticated
  identity and own institution.
- Permission records currently use global scope in the migration. There is no
  University Admin permission-management API/UI, and no institution-specific
  role-grant administration surface was added.
- The schema has no authoritative faculty-to-class/course/student assignment
  relation. Tenant membership alone is not treated as assigned academic scope.

## Frontend changes

- Added a client-side permission helper and permission-aware navigation models
  for the existing role shells.
- Role shells filter navigation and visible views from the effective grants
  returned by `/auth/me`.
- Client checks are for presentation only; backend authorization remains the
  security boundary.
- Individual action controls are not comprehensively permission-gated, and
  role/permission management and per-user permission-source screens are not
  implemented.

## API changes

- `GET /api/v1/auth/me` now returns an additive `effective_permissions` list.
- Existing endpoint paths and tenant/ownership contracts remain unchanged.
- No endpoint for mutating global permission definitions or role grants was
  added.

## Audit logging

- Permission denials are logged with the user identifier and denied permission
  code; permission grants and changes do not yet have a dedicated durable audit
  event path.
- No direct-user permission override or permission-source history is available.

## Testing results

Commands were run from the repository on 2026-10-05:

| Command | Result |
| --- | --- |
| `cd backend; ..\.venv\Scripts\python.exe -m pytest tests -q` | **2,613 passed, 27 skipped**, 7 warnings |
| `cd frontend; npm.cmd test -- --maxWorkers=1` | **536 passed / 61 files** |
| `cd frontend; npm.cmd run build` | **PASS**, TypeScript and Vite build (116 modules transformed) |
| `git diff --check` | **PASS** (line-ending notices only) |
| Pylance diagnostics on changed backend authorization files | **No errors found** |

The backend suite is invoked with `pytest tests` rather than root-level
collection because the backend tree also contains a live Phase 6.22 demo
script that calls a running backend and writes evidence.

## Migration verification

MIGRATION VERIFICATION: BLOCKED
Reason: Docker/Supabase runtime unavailable.

No migration replay or remote migration push was performed. Migration source
and related unit tests were checked, but clean-database and existing-database
replay remain unverified.

## Known limitations (Definition-of-Done gaps)

1. **Authorization coverage is partial.** The Admin and Platform routers have
   explicit route policies, and several related surfaces have permission
   checks, but not every protected backend route has been mapped to granular
   permissions.
2. **Permission management is not implemented.** No safe, tenant-aware
   University Admin workflow exists to view or change role grants. Because the
   existing role-permission tables are global, tenant administrators must not
   be allowed to change them through an unscoped interface.
3. **Frontend action-level gating is incomplete.** Navigation and view
   filtering are present, but individual controls do not all hide/disable
   actions based on permissions.
4. **There are no direct-user overrides or permission-source records.** The
   current schema has role grants only; effective permissions cannot explain
   per-user overrides because those overrides do not exist.
5. **Faculty academic assignment scope is undefined.** The current schema
   lacks authoritative teaching-assignment relationships. Tenant membership
   alone cannot safely authorize class-, course-, or student-level academic
   actions.
6. **Permission-change auditing is incomplete.** Denials are logged, but there
   is no dedicated durable audit trail for permission or role-grant mutations;
   no such mutation UI/API was added.
7. **Physical migration replay is unverified.** Local Docker/Supabase runtime
   availability prevented clean and existing database replay.

## Follow-up

1. Map every protected endpoint to an explicit permission and add tests that
   verify both policy coverage and the existing tenant/ownership boundary.
2. Design a tenant-safe role-grant administration model before exposing
   permission mutation to University Admins; the current grants are global.
3. Add action-level frontend gating as a usability layer, with backend checks
   retained as the security boundary.
4. Define the Faculty assignment data model before granting academic
   visibility or mutation beyond the currently justified scope.
5. Add durable, redacted audit events for permission and role-grant changes.
6. Replay the migration against both a clean database and an existing local
   Supabase database when Docker/Supabase runtime is available.
