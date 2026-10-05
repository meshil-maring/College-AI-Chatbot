# Multi-Role Authentication, RBAC & User Management Phase Report

Date: 2026-10-05

## PHASE STATUS

**INCOMPLETE**

The repository already contained a substantial, tested multi-role and
multi-tenant identity implementation. This increment completed the missing
public Faculty/Staff registration UI path, made pending membership login
feedback actionable, repaired the Staff/Faculty roster projection, and fixed a
public-boundary diagnostic log leak. It does not claim the supplied phase is
complete because several Definition-of-Done items still have no production
implementation (listed under Known limitations).

## Audit and architecture

The existing architecture was retained:

```text
Supabase Auth JWT
  -> get_current_user()
  -> public.users
  -> user_roles + roles (server-owned scope)
  -> resolve_primary_role()
  -> active institution/platform authorization context
  -> endpoint-specific role, tenant, and ownership checks
  -> /api/v1/auth/me
  -> AuthProvider
  -> role shell
```

Canonical precedence remains `super_admin -> admin -> staff -> faculty ->
student`. The existing role name `admin` represents a University Admin; it was
not renamed because doing so would break the established schema and contracts.
Role precedence remains presentation/bootstrap logic and is not used as a
substitute for endpoint authorization.

The audit confirmed the following reusable implementation was already present:

- student, faculty, and staff registration through one strict public contract;
- pending student profiles and pending staff/faculty membership requests;
- student approval/rejection and Staff/Faculty request approval/rejection;
- Super Admin institution and University Admin invitation/lifecycle flows;
- server-derived role/scope resolution and active-tenant checks;
- student `me` endpoints for profile, attendance, results, notices, and
  resources;
- tenant-qualified administrative repositories and cross-tenant tests;
- role-specific frontend shells restored from `/auth/me`;
- administrative and platform audit ledgers;
- invitation email verification and outbox delivery architecture.

## Architecture changes

- No second authentication, role, invitation, email, or tenant-resolution
  mechanism was introduced.
- Pending Staff/Faculty registration is now resolved after credential
  verification from the authoritative membership request row.
- The frontend's registration type is now the backend's full public allowlist:
  `student | faculty | staff`. Admin and Super Admin remain unrepresentable.

## Database changes

- No new migration or table was added in this increment.
- The existing Phase 7.23 migration remains the Staff/Faculty approval,
  invitation, roster, and lifecycle migration.
- The roster query was corrected to use the actual `user_roles.assigned_at`
  column instead of nonexistent `created_at`/`updated_at` role-grant fields.

## Backend changes

- Added a tenant-repository lookup for a user's pending Staff/Faculty
  membership request.
- Email login now returns `403 REGISTRATION_PENDING` only after credentials are
  verified (including the Auth provider's verified-password
  `email_not_confirmed` path). Invalid passwords retain the generic
  `INVALID_CREDENTIALS` response.
- Pending users still receive no application role and no token from the
  application login response.
- Public chat unexpected failures now log coarse event metadata without
  exception text that could contain database/provider diagnostics.

## Frontend changes

- Student, Faculty, and Staff registration all use the existing shared form and
  `/api/v1/users/register` endpoint.
- Faculty/Staff forms show designation and department instead of student
  identifiers.
- Landing-page entry points were added for Faculty and Staff registration.
- Role-specific login pages open the correct registration type, including
  direct `?register=1` links.
- Pending login errors use a role-neutral, actionable message so Staff are not
  mislabeled as Faculty.
- Vitest keeps a bounded 15-second timeout for full-field `user-event` tests on
  constrained parallel CI workers; the platform-effect assertion now waits for
  the asynchronous request it verifies.

## API changes

No endpoint was duplicated. Existing contracts were extended in use only:

- `POST /api/v1/users/register` accepts the already-supported server-validated
  `student | faculty | staff` discriminator.
- `POST /api/v1/auth/login` can additionally return
  `403 REGISTRATION_PENDING` after successful credential verification.

## RBAC and permission changes

- No role is accepted from login input.
- Public registration cannot represent `admin` or `super_admin`.
- Faculty/Staff registration creates a pending membership request and grants no
  role.
- Existing tenant-scoped endpoint guards and Super Admin platform-scope guard
  remain unchanged.
- No new granular permission enforcement was added; this is an explicit
  remaining gap.

## Registration and approval flows

- Student: shared registration form -> pending student profile -> existing
  institution approval/rejection -> student role.
- Faculty/Staff: shared registration form -> pending membership request with no
  role -> University Admin review -> existing invitation/outbox -> one-time
  acceptance -> institution-scoped role.
- University Admin: existing Super Admin invitation/assignment lifecycle.
- Super Admin: existing controlled bootstrap/assignment process only; never a
  public registration choice.

## Security changes

- Client-supplied role, permission, tenant, institution, user, or approval
  fields remain rejected by strict backend schemas.
- Pending-state disclosure occurs only after successful password verification.
- Public failure logs no longer include raw exception diagnostics.
- No secret, password, access token, refresh token, or invitation token is
  returned or logged by the new paths.

## Audit logging

Existing privileged mutation audit ledgers were preserved and the public chat
failure log was hardened. Authentication success/failure/logout and public
registration events are not yet persisted in a unified security audit ledger;
this remains incomplete.

## Testing results

Commands run from the repository on 2026-10-05:

| Command | Result |
| --- | --- |
| `cd backend; $env:DEBUG='true'; uv run pytest -q tests` | **2603 passed, 27 skipped**, 6 warnings |
| `cd frontend; npm.cmd test -- --run` | **532 passed / 60 files** |
| `cd frontend; npx.cmd tsc -b --force` | **PASS** |
| `cd frontend; npm.cmd run build` | **PASS**, Vite 7.3.6, 115 modules transformed |
| `node scripts/verify_frontend_build_security.mjs` | **PASS**, 4 build files scanned |
| `git diff --check` | **PASS** (line-ending warnings only) |

Focused verification also passed:

- 199 authentication/RBAC/tenant tests before the final changes;
- 110 pending-login, membership-roster, and public-log security tests after the
  final changes;
- 102 authentication/registration frontend tests;
- 29 shared/university registration tests in isolated verification.

## Migration verification

- Migration/source-contract tests in the backend suite passed.
- No remote migration was pushed and no remote Supabase data was changed.
- A physical clean/existing database replay was **not** run. `supabase status`
  reported that Docker Desktop's Linux engine pipe was unavailable, so no local
  Supabase stack was running. This item therefore remains unverified.

## Regression results

- Existing student login/registration, `/auth/me`, RBAC, tenant isolation,
  attendance, results, notices, documents, learning resources, authenticated
  AI, public AI, administration, invitation, and email-outbox tests pass in the
  full suites above.
- Cross-role, cross-tenant, IDOR, privilege-escalation, inactive-tenant, and
  deactivated-user coverage remains part of the passing backend suite.
- Production frontend build and secret scanning pass.

## Known limitations (Definition-of-Done gaps)

1. **Granular permission enforcement is incomplete.** `permissions` and
   `role_permissions` exist in the baseline schema, but runtime endpoint
   authorization is still primarily explicit role/capability based. `/auth/me`
   does not return an effective permission set, and University Admins cannot
   assign per-user Staff permissions.
2. **Production password recovery/change and session revocation are
   incomplete.** Recovery/change-password helpers are deliberately DEV/TEST
   only; there is no production reset-link completion route or all-device
   revocation mechanism.
3. **Authentication abuse controls are incomplete.** Public AI and invitation
   acceptance have abuse controls, but login, public registration, recovery,
   and verification do not share a production rate-limit/lockout policy.
4. **Security-event auditing is incomplete.** There is no unified durable
   ledger for login success/failure, logout, password change/reset, and public
   registration events.
5. **Account lifecycle vocabulary is not fully unified.** Student approval,
   membership request state, invitation state, `users.status`, and institution
   state are intentionally separate existing models; they do not expose one
   universal `pending|active|rejected|suspended|deactivated|locked` state
   machine.
6. **Faculty academic scope is undefined.** The schema has no authoritative
   faculty-to-course/class/student assignment relation, so attendance/results
   management cannot be safely granted to Faculty without a product/data-model
   decision.
7. **Physical migration replay is unverified** because the local Docker-backed
   Supabase stack was unavailable.
8. The existing public university onboarding flow creates a pending initial
   admin behind institution/organization approval. It is not an unrestricted
   active admin registration, but it differs from a strict "Super Admin invite
   only" policy and needs an explicit product decision before removal.

## Future work

Prioritized follow-up:

1. Define and seed the effective permission catalogue, resolve permissions from
   active role grants, add a `require_permissions` dependency, return safe
   effective permissions from `/auth/me`, and build bounded Staff permission
   assignment with escalation tests.
2. Add production Supabase recovery-link completion, authenticated password
   change, and documented session-revocation semantics.
3. Apply the existing abuse-control architecture to login, registration,
   recovery, and verification.
4. Add a tenant-aware security-event ledger with redaction rules and retention.
5. Define the faculty academic-assignment model before exposing student,
   attendance, or result mutation capabilities.
6. Start Docker Desktop and run clean-database plus existing-database migration
   replays before deployment.

