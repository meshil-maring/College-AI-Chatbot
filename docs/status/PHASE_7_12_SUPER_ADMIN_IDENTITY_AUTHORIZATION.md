# Phase 7.12 — Super Admin Identity & Authorization

## 1. Objective

Status: **COMPLETE**

Phase 7.12 establishes a persisted, platform-scoped `super_admin` role, a
server-authoritative authorization dependency, controlled local assignment and
revocation, a minimal protected platform endpoint, and an auditable role-change
trail. It does not add platform management CRUD.

## 2. Existing role model

The existing `roles` and `user_roles` tables remain the only RBAC source of
truth. No role table was duplicated and no existing role was renamed or
replaced.

```text
super_admin -> platform
admin       -> institution/organization (existing Phase 6.13 scopes)
staff       -> institution
faculty     -> institution
student     -> institution/user
```

The additive migration inserts only `super_admin` by name with an idempotent
`ON CONFLICT (name)` clause. It contains no deletion or replacement of
`admin`, `staff`, `faculty`, or `student`. Existing RBAC behavior is covered by
the complete backend regression suite.

## 3. Super Admin role contract

A valid platform principal requires all of the following:

1. a verified Supabase JWT;
2. the JWT subject mapped through `public.users.auth_user_id`;
3. an active `public.users` account;
4. an active `roles.name = 'super_admin'` row;
5. a `user_roles` link with `scope_type = 'platform'`, null `scope_id`, and
   null `scope_organization_id`;
6. the canonical server-resolved role to be `super_admin`.

Multiple users can hold the role because the existing primary key remains
`user_roles(user_id, role_id)`. There is no singleton identity or hardcoded
email.

## 4. Platform vs tenant boundary

`require_super_admin` is separate from `require_roles(...)`. `super_admin` was
not added to any tenant role list and does not satisfy `require_roles('admin')`.
A platform principal receives tenant permissions only if a separate explicit
tenant role is also assigned and the existing tenant authorization accepts it.

The migration trigger `trg_phase712_super_admin_scope` rejects any
non-platform `super_admin` grant. The application performs a second fresh
scope check on every platform request. Institution codes, tenant IDs, query
parameters, headers, URL selection, login cards, frontend state, and client
JWT metadata do not participate in the decision.

The pre-existing Phase 6.13 legacy concept of a platform-scoped `admin` remains
unchanged for its existing organization approval workflows, but it does not
satisfy the new Super Admin primitive.

## 5. Database changes

Migration:

`supabase/migrations/20261001000000_phase_7_12_super_admin_identity_authorization.sql`

It adds:

- the active `super_admin` role definition;
- a database trigger enforcing platform-only scope for that role;
- `platform_role_audit_log` with constrained action, result, role, actor,
  target, metadata, and timestamp fields;
- idempotent service-role-only assignment and revocation functions;
- explicit privilege revocation from `PUBLIC`, `anon`, and `authenticated`.

It does not create an Auth user, assign a person, include credentials, modify a
historical migration, or alter the reconstructed baseline.

## 6. Assignment mechanism

`scripts/validation/manage_local_super_admin.ps1` is the supported Phase 7.12
mechanism:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\validation\manage_local_super_admin.ps1 `
  -Action Assign `
  -TargetEmail user@local.test `
  -ActorIdentifier operator-or-ticket `
  -Environment local
```

The target must already exist as an active `public.users` identity. The script
accepts only `local` or `test`, verifies Docker Desktop Linux, rejects
`DOCKER_HOST`, requires the API endpoint to be exactly
`http://127.0.0.1:54321`, obtains the local credential in memory, and never
prints it. Assignment upserts on the existing composite primary key, so a
repeat produces `already_assigned` and cannot create a duplicate link.

There is no frontend button, registration path, anonymous endpoint, hardcoded
credential, environment-only authorization, or production assignment workflow.
The local Supabase wrapper was also hardened so its `status` action parses CLI
JSON in memory and prints only non-secret health/endpoints.

## 7. Revocation mechanism

The same script with `-Action Revoke` deletes only the target user's
`super_admin` role link. It does not delete or disable the Auth identity or the
application user. A repeated revocation produces `already_revoked`.

`require_super_admin` re-reads account status and the active platform grant on
every request. Therefore an already-issued JWT and stale frontend `/auth/me`
state cannot retain platform API access after revocation. The frontend shell
also requires `GET /api/v1/platform/me` to succeed before rendering platform
content and fails to a restricted screen when that check is denied.

## 8. Authorization primitive

`backend/app/core/security.py` defines `require_super_admin`. Authentication is
delegated to the established `get_current_user`; canonical role selection uses
the established resolver; then a narrow database projection independently
checks `public.users.status`, `roles.is_active`, and `user_roles.scope_type`.

Behavior:

- unauthenticated: `401 AUTH_REQUIRED`;
- authenticated but inactive: `403 ACCOUNT_INACTIVE`;
- authenticated non-Super-Admin: `403 FORBIDDEN`;
- malformed/non-platform/revoked grant: `403 FORBIDDEN`;
- active platform-scoped Super Admin: allowed.

## 9. `/auth/me`

The existing endpoint remains the single canonical role bootstrap and its
response contract is unchanged. No second role-detection API or frontend role
probing was introduced. `/platform/me` is an authorization boundary, not an
alternative identity resolver.

## 10. `/super-admin`

The SPA route continues to use `AuthProvider` and the canonical `/auth/me`
role. It now withholds `SuperAdminShell` content until the protected platform
endpoint returns an allow response. Anonymous visitors receive the existing
login experience; an actual anonymous API request receives 401. Tenant roles
receive the existing restricted experience and a direct platform API request
receives 403.

## 11. Platform API

`GET /api/v1/platform/me` is protected by `require_super_admin` and returns only:

```json
{"role":"super_admin","scope":"platform"}
```

It exposes no internal IDs, other users, student data, credentials, or provider
configuration.

## 12. Auditability

The existing `admin_audit_log` requires an application actor foreign key and
is designed for tenant-admin mutations, so it cannot truthfully represent the
local operator performing the initial platform bootstrap. A small dedicated
ledger was added instead.

Each successful or idempotent controlled operation records:

- who: required bounded `actor_identifier`;
- what: `assign` or `revoke` plus `super_admin`;
- when: database-generated `performed_at`;
- target: `target_user_id` foreign key;
- result: `assigned`, `already_assigned`, `revoked`, or `already_revoked`.

No password, token, email, service-role key, or secret is written to the audit
metadata. Failed SQL transactions are reported to the invoking operator but
cannot retain an audit row because PostgreSQL rolls the transaction back; a
future production workflow should add an external operational failure log.

## 13. Security tests

Focused backend coverage verifies anonymous denial; denial for student,
faculty, staff, and admin; allow for a valid Super Admin; inactive and revoked
denial; malformed tenant-scoped denial; client role/tenant/header/query
manipulation denial; no implicit tenant-admin access; fresh grant resolution;
migration constraints; and local-script safety.

Focused frontend coverage verifies protected endpoint token handling,
fail-closed response validation, allowed shell rendering, and denial of stale
`super_admin` frontend state after the server rejects the platform check.

## 14. Migration validation

Local-only validation completed on 2026-10-01:

- first fresh reset: PASS;
- second fresh reset: PASS;
- ledger: 17 ordered migrations (16 existing + Phase 7.12), no manual ledger
  edits;
- `super_admin` exists and is active after each reset;
- no Super Admin user is seeded or retained;
- live local cycle: `assigned`, `already_assigned`, `revoked`,
  `already_revoked`;
- duplicate assignment link count: one during assignment;
- final grant count before second reset: zero;
- audit cycle: four correctly attributed result rows;
- clean state after second reset: zero grants and zero audit rows;
- Phase 6.11 `student_notifications`: present;
- Phase 7.2 visibility constraint: present;
- Phase 7.4 hardened public search RPC: present.

No remote command was executed.

## 15. Regression results

- focused Phase 7.12 backend security: 15 passed;
- focused authorization/auth/tenancy compatibility run: 77 passed, 4 skipped;
- maintained backend production suite: 2,144 passed, 15 skipped, 2 documented
  debug-only tests deselected;
- debug-only backend tests with `DEBUG=true`: 2 passed;
- frontend serialized full suite: 53 files, 443 tests passed;
- TypeScript `npx tsc --noEmit -p tsconfig.json`: PASS;
- frontend production build: PASS, 104 modules transformed;
- `git diff --check`: PASS (line-ending warnings only).

An unscoped `pytest` invocation was also attempted. It collected six live/manual
scripts outside the maintained `backend/tests` boundary and failed collection
because no separate backend API was listening. This known non-automated
boundary is reported rather than hidden; the maintained suite results above
are authoritative.

Two parallel frontend reruns encountered unrelated five-second interaction
timeouts under CPU contention (10 failures, then 4 failures). The affected
registration file passed 25/25 in isolation, and the complete suite passed
443/443 with one worker. No timeout thresholds or unrelated tests were changed.

## 16. Remote safety

```text
Remote database modified: NO
Remote migrations applied: NO
Remote Auth modified: NO
Remote Super Admin assigned: NO
Remote data modified: NO
Production deployment: NO
```

## 17. Known limitations

- No production assignment/revocation operator workflow exists.
- SQL transaction failures cannot be retained in the database audit ledger;
  future production operations need an external failure audit sink.
- The Super Admin UI remains a read-only placeholder.
- No institution CRUD, university-admin management, billing, subscription,
  provider management, platform analytics, WhatsApp, support inbox, or full
  platform settings are implemented.
- The existing Phase 6.13 platform-scoped legacy `admin` behavior remains for
  its old workflows, separate from `super_admin`.

## 18. Future Super Admin dashboard work

Future work may add narrowly authorized platform features behind
`require_super_admin`, but each capability must define its own data exposure,
audit event, and tenant-crossing rules. The role must not be added wholesale to
tenant `require_roles(...)` lists.

Recommended next phase: production-grade Super Admin operator lifecycle and
break-glass design (multi-operator approval, durable failure audit, recovery,
and deployment runbook) before any institution-management CRUD.

