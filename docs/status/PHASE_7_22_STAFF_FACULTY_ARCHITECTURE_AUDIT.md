# Phase 7.22 — Staff & Faculty Architecture Audit

## Status

**AUDIT COMPLETE** — 2026-10-04

This phase is an audit and scope lock. It adds no role, permission model, user
model, invitation system, migration, or production operation. One narrow
runtime security defect discovered by the audit was fixed by applying the
existing Phase 7.20 institution-authorization boundary to authenticated chat.

## Scope Lock

- Keep the single identity chain: Supabase Auth JWT -> `get_current_user` ->
  `public.users` -> active `user_roles`/`roles` grants.
- Keep `require_institution_roles(...)` as the entry guard for every future
  institution operation. A URL, request body, query parameter, frontend value,
  or student profile must not establish staff/faculty scope.
- Keep `public.users`, `roles`, and `user_roles`; do not add role-specific user
  tables merely to represent identity.
- Keep the Phase 7.14–7.18 invitation, verification, outbox, provider, and
  webhook infrastructure. It is currently pinned to University Admin and is a
  reusable delivery/lifecycle design, not an already-supported staff/faculty
  invitation API.
- Do not infer institution-wide student or academic access from the `staff` or
  `faculty` role. Add resource relationships before adding capabilities that
  require them.

## Existing Staff Architecture

The `staff` role is an active canonical role. `/auth/me` resolves it from the
database grant, and `App.tsx` selects `StaffShell` only from that server result.
The shell has Dashboard, Student Approvals, AI Assistant, and Profile views.

| View | Component | Purpose / API | Authorization and scope | State / tests | Status |
| --- | --- | --- | --- | --- | --- |
| Staff shell | `features/staff/StaffShell.tsx` | Role-specific navigation and view state | Frontend role is `/auth/me` output; backend remains authoritative | Controlled unsupported identity state; shell/navigation/cross-role/session tests | COMPLETE |
| Dashboard | `StaffDashboard.tsx` | Identity plus static, audited capability map; no data request | Staff shell only | Honest unavailable states; component tests | COMPLETE |
| Student Approvals | `StaffApprovals.tsx` | `GET /admin/students/pending`; `POST /admin/students/{id}/approve|reject` | `require_institution_roles("admin", "staff")`; rows and decisions pinned to caller institution | Loading, empty, error, retry and mutation states; frontend and backend tests | COMPLETE |
| AI Assistant | existing `ChatShell` | Authenticated conversations and generation | Authenticated user/owner boundary; institution context remains server-derived | Shared chat tests and cross-role tests | COMPLETE |
| Profile | `StaffProfile.tsx`, `StaffIdentityCard.tsx` | Safe `/auth/me` identity fields | User-scoped; institution presence only, not tenant authority | Shell/component tests | COMPLETE |
| Ingestion pipeline | No staff UI | `/documents/ingest`, `/{run}/extract|chunk|embed` | `require_institution_roles("admin", "staff", "faculty")` plus source/run tenant checks | Backend ingestion and staff security tests | PARTIAL |

There is no staff profile/domain table, staff roster, employee identifier,
department assignment, suspension endpoint, or staff-to-student assignment.
The optional designation/department values collected in a membership request
are onboarding metadata, not an authorized staff profile contract.

## Existing Faculty Architecture

The `faculty` role is also canonical and institution-scoped. `/auth/me` selects
`FacultyShell`, whose views are Dashboard, AI Assistant, and Profile.

| View | Component | Purpose / API | Authorization and scope | State / tests | Status |
| --- | --- | --- | --- | --- | --- |
| Faculty shell | `features/faculty/FacultyShell.tsx` | Role-specific navigation and view state | Frontend role is `/auth/me` output; backend remains authoritative | Controlled unsupported identity state; shell/navigation/cross-role/session tests | COMPLETE |
| Dashboard | `FacultyDashboard.tsx` | Identity plus static, audited capability map; no data request | Faculty shell only | Honest unavailable states; component tests | COMPLETE |
| AI Assistant | existing `ChatShell` | Authenticated conversations and generation | Authenticated user/owner boundary; no faculty academic personalization | Shared chat tests and cross-role tests | COMPLETE |
| Profile | `FacultyProfile.tsx`, `FacultyIdentityCard.tsx` | Safe `/auth/me` identity fields | User-scoped; institution presence only, not tenant authority | Shell/component tests | COMPLETE |
| Ingestion pipeline | No faculty UI | `/documents/ingest`, `/{run}/extract|chunk|embed` | `require_institution_roles("admin", "staff", "faculty")` plus source/run tenant checks | Backend ingestion and faculty security tests | PARTIAL |

There is no faculty profile, faculty ID, teaching assignment, subject/class
ownership, department relationship, or faculty-to-student scope. Consequently,
student lists, attendance, results, notices, and resource listing fail closed
for faculty and are not shown as usable navigation.

## Existing Authentication

- Staff and Faculty use the existing email/password endpoint
  `POST /api/v1/auth/login`; credentials remain in Supabase Auth.
- `GET /api/v1/auth/me` verifies the JWT, loads the application user and active
  database role grants, resolves primary role priority as `super_admin > admin
  > staff > faculty > student`, and derives non-student institution scope only
  from the selected role's institution grant.
- Frontend `AuthProvider` is the single session/identity source. Login routes
  exist for `/login/staff` and `/login/faculty`; neither shell performs a
  second role probe or trusts local storage for authority.
- Account inactivity is enforced by `require_institution_roles`; inactive or
  missing institutions fail closed. Pending staff/faculty accounts have no
  role and receive no privileged shell.
- There is one public backend registration contract,
  `POST /api/v1/users/register`, whose schema permits only `student`, `staff`,
  or `faculty`. The current frontend registration form is student-only, so
  staff/faculty self-registration is backend-only.

## Existing Role Assignment

`roles.name` is unique and `user_roles` has primary key `(user_id, role_id)`.
`assign_user_role_scope` upserts on that key, preventing duplicate grants for
the same user/role. It writes `scope_type`, `scope_id`, and
`scope_organization_id`; database checks and the Phase 6.13 trigger ensure an
institution scope belongs to the stated organization.

The existing membership workflow restricts requested roles to `staff` or
`faculty`, creates no grant while pending, and on approval calls
`assign_membership_role` -> `assign_user_role_scope` with the request's
server-stored institution and organization. It cannot request `admin` or
`super_admin`. The service checks that the deciding actor may manage that
institution and that the tenant is active.

An existing account can structurally hold staff and/or faculty grants. Primary
role priority chooses staff before faculty. However, because the primary key is
only `(user_id, role_id)`, one user cannot hold the same role in two institutions:
an upsert would move that role's scope. This is safe against duplicate grants
but is not a multi-institution employment model. Ambiguous same-primary-role
institution grants also fail closed in `require_institution_roles`.

The repository/service implementation for deciding staff/faculty membership
requests exists and is tested, but no mounted HTTP endpoint exposes it. There
is also no University Admin UI for the request queue. It is therefore not an
operational University Admin management capability yet.

## Existing Invitation Infrastructure

Phase 7.14–7.18 provides token hashing, one-time acceptance, expiry,
cancellation, resend, email verification, durable outbox processing, Mailgun
transport, signed webhooks, compensation, audit records, and a frontend
acceptance page. It reuses Supabase Auth, `public.users`, and
`assign_user_role_scope`.

That implementation is deliberately fixed to `role_name='admin'`, is exposed
only under Super Admin platform routes, and uses `/admin-invite/{token}`. It
must not be described or called as a staff/faculty invitation flow today.
Future work may generalize its shared lifecycle and delivery primitives behind
strict server-owned role templates (`staff`/`faculty` only for a University
Admin), while preserving the existing table/user/auth/outbox/provider systems.

The separate existing staff/faculty onboarding path creates the Auth and
application user first, then records a pending institution membership request.
It is self-registration, not invitation. These paths should be deliberately
integrated in a future phase rather than duplicated.

## Existing Staff Capabilities

| Area | Actual behavior |
| --- | --- |
| Identity | Login, `/auth/me`, primary role, institution scope, account/institution active checks |
| Students | Can list only pending student registrations and approve/reject them in own institution; cannot search/list all students, read profiles, or modify records |
| Attendance | No read/create/update/delete access; admin endpoints deny staff |
| Results/tests | No read/create/update/delete access; admin endpoints deny staff |
| Knowledge | Tenant-safe ingestion pipeline is authorized, but no source-list contract or UI makes it independently usable; no FAQ or document-management authority |
| Communication | AI/conversations are available; notice and FAQ read/manage surfaces are unavailable |
| Administration | Cannot invite users, assign roles, manage settings, manage institutions, or access platform APIs |

## Existing Faculty Capabilities

| Area | Actual behavior |
| --- | --- |
| Identity | Login, `/auth/me`, primary role, institution scope, account/institution active checks |
| Students | No student list/search/profile/approval/edit contract |
| Attendance | No read/create/update/delete contract and no faculty assignment scope |
| Results/tests | No read/create/update/delete contract and no subject/class ownership scope |
| Knowledge | Tenant-safe ingestion pipeline is authorized, but no source-list contract or UI makes it independently usable; no FAQ or document-management authority |
| Communication | AI/conversations are available; notice and FAQ read/manage surfaces are unavailable |
| Administration | Cannot invite users, assign roles, manage settings, manage institutions, or access platform APIs |

## University Admin Management Capabilities

University Admin currently manages institution students, student approvals,
attendance, results/test results, notices, FAQs, knowledge sources/documents,
and the operational dashboard through `require_institution_roles("admin")`.

For people management:

- Staff/faculty registration and membership-decision repository/service logic
  exists, but the University Admin has no mounted list/decision API and no UI.
- No institution staff/faculty roster, search, activation, deactivation,
  revocation, or role-change API/UI exists.
- The `AdminRosterPanel` is a **Super Admin** component for University Admins;
  its platform endpoints and fixed `admin` invitation are not reusable as-is
  by a University Admin.
- University Admin cannot create `super_admin`, alter platform roles, manage
  other institutions, or use platform settings/billing APIs.

## API ↔ Frontend Coverage

| Capability | Backend API | Frontend UI | Role | Tenant Scope | Tests | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Staff/faculty login and identity | `POST /auth/login`, `GET /auth/me` | Shared login/AuthProvider; role shells/profile | staff, faculty | Grant-derived institution; user-scoped identity | Auth, role gateway, shell/session tests | COMPLETE |
| Staff/faculty self-registration | `POST /users/register` | Student-only registration form | public -> pending | Server resolves active institution code | Registration/backend security tests | PARTIAL |
| Membership request approval | Service/repository only; no route | None | intended admin | Service validates institution/active tenant | Approval/RBAC service tests | PARTIAL |
| Staff dashboard/profile | No extra API beyond `/auth/me` | Staff shell/dashboard/profile | staff | User + grant scope | Staff/frontend/cross-role tests | COMPLETE |
| Faculty dashboard/profile | No extra API beyond `/auth/me` | Faculty shell/dashboard/profile | faculty | User + grant scope | Faculty/frontend/cross-role tests | COMPLETE |
| Student approval queue | `/admin/students/pending`, `/{id}/approve|reject` | `StaffApprovals`; also Admin approvals | admin, staff | Institution and resource scoped | Staff, admin, Phase 7.20 tests | COMPLETE |
| General student management | `/admin/students*` | Admin Student Manager only | admin | Institution/resource scoped | Admin and tenant tests | COMPLETE for admin; MISSING for staff/faculty |
| Attendance management | `/admin/*attendance*` | Admin Attendance Manager only | admin | Institution -> student -> attendance | Attendance/admin tests | COMPLETE for admin; MISSING for staff/faculty |
| Results/test results | `/admin/results*`, `/admin/test-results*` | Admin result managers only | admin | Institution -> student -> result | Results/admin tests | COMPLETE for admin; MISSING for staff/faculty |
| Knowledge ingestion | `/documents/ingest|{run}/extract|chunk|embed` | No staff/faculty surface | admin, staff, faculty | Institution -> source/run | Ingestion and role tests | PARTIAL |
| Knowledge/doc/FAQ management | `/admin/knowledge-sources`, `/admin/documents`, `/admin/faqs` | Admin managers only | admin | Institution/resource scoped | Admin knowledge/document/FAQ tests | COMPLETE for admin; MISSING for staff/faculty |
| Notices | `/admin/notices`; student own-institution read | Admin manager/student UI | admin/student | Institution/resource or student scope | Admin/student tests | MISSING for staff/faculty |
| AI and conversations | Generation/chat and `/conversations*` | Shared `ChatShell` | active institution roles | Institution scope plus conversation owner | Chat/cross-role tests | COMPLETE |
| Staff/faculty roster | None | None | intended admin | Not implemented | None | MISSING |
| Staff/faculty invite/resend/revoke | Admin-only platform invitation endpoints | Super Admin `AdminRosterPanel` only | super_admin -> admin | Target institution resource | Phase 7.14–7.18 tests | MISSING for staff/faculty |
| Platform administration | `/platform/*` | Super Admin shell | super_admin | Platform grant only | Platform/security tests | COMPLETE and correctly denied to staff/faculty |

No capability is classified DUPLICATE at the full feature level. The overlap
listed below is implementation duplication or adjacent lifecycle machinery.

## RBAC / Tenant Isolation

The required chain is preserved:

```text
verified JWT
  -> get_current_user
  -> active public.users + user_roles + roles
  -> resolve_institution_authorization_context
  -> require_institution_roles(allowed roles)
  -> AuthorizationContext(institution_id, role, active)
  -> scope_tenant / assert_tenant_object / resource relationship checks
```

`require_institution_roles` rejects an inactive account, disallowed role,
missing/non-institution scope, ambiguous institution grants, and inactive or
missing institution. It returns a copy pinned to the authoritative tenant.
Staff approvals then validate student rows against that tenant; ingestion
validates the knowledge source and each processing run. Staff/faculty cannot
reach admin-only or `require_super_admin` platform endpoints.

Institution A/B behavior is covered by the focused staff/faculty, cross-role,
Phase 7.20, role-scope, tenant-isolation, and ingestion tests: an A principal
cannot redirect a request to B, access B resources, or use missing scope as
platform authority. No cross-tenant test was weakened.

Resource chain summary:

- Staff approval: Staff -> institution grant -> pending Student.
- Staff/faculty ingestion: principal -> institution grant -> Knowledge Source
  -> Processing Run.
- AI conversations: authenticated principal -> owned Conversation -> Messages.
- Attendance/results currently stop at Admin -> institution -> Student ->
  resource. No Faculty -> assignment -> Student chain exists.

## Staff vs Faculty Boundary

The distinction is implemented at both authorization and current capability
levels:

- Staff has one operational exception: tenant-scoped student approval.
- Faculty does not have that exception.
- Both can authenticate, use the AI assistant, and invoke the tenant-safe
  ingestion stages at the backend.
- Neither has institution-wide student, attendance, results, notices, FAQ,
  document-management, user-management, role-management, or platform access.
- Faculty has no academic assignment model, so teaching capabilities cannot be
  authorized safely yet.

The roles are therefore not identical, but the intended broader operational
versus teaching distinction is only minimally implemented.

## Duplications

- Canonical authentication is Supabase Auth plus `get_current_user`; no second
  staff/faculty authentication implementation was found.
- Canonical role storage/assignment is `roles` + `user_roles` +
  `assign_user_role_scope`; platform admin assignment and membership approval
  both correctly delegate to it.
- Canonical institution authorization is `require_institution_roles`; legacy
  `require_roles` still exists for non-institution/general use, but protected
  admin and ingestion paths audited here use the scoped dependency.
- `user_tenant_id` is defined twice identically in `core/security.py`. This is
  dead-definition duplication with no observed behavior difference; removal is
  deferred because this phase is audit-only.
- Student approval presentation exists separately in `AdminApprovals` and
  `StaffApprovals` over the same API. Their role-specific shells and copy differ,
  but shared queue/action logic could be extracted later if it can preserve the
  separate UX and tests.
- `services/tenancy.register_staff_or_faculty` and the newer unified
  `services/user_registration.register_user` overlap for staff/faculty
  onboarding. The mounted canonical public API is `/users/register`; the older
  service is not mounted and should not become a second endpoint.
- The admin invitation lifecycle and staff/faculty membership lifecycle overlap
  conceptually but have different order (invite-before-account versus
  account-before-approval). Do not copy either; choose and integrate shared
  lifecycle/delivery primitives in the next phase.

## Security Findings

One small cross-tenant defect was found and fixed in scope; no remaining
exploitable cross-tenant, role-escalation, or platform-isolation defect was
found in the audited reachable paths.

1. **Pass:** `staff`/`faculty` registration literals cannot express `admin` or
   `super_admin`; no role is granted at registration.
2. **Pass:** role approval uses server-stored request scope and the canonical
   role grant primitive; schema/trigger constraints reject malformed scope.
3. **Fixed:** authenticated generation chat previously used plain
   `get_current_user` plus legacy `scope_tenant`. A staff/faculty principal
   whose institution projection was missing could therefore supply an
   institution in the body and enter the old platform-passthrough branch.
   `/generation/chat` now uses the existing
   `require_institution_roles("admin", "staff", "faculty", "student")`
   dependency. Missing, non-institution, inactive, and cross-institution scope
   now fails before chat processing. Focused tests cover staff and faculty.
4. **Pass:** staff approval and both-role ingestion require active institution
   grants and resource tenant checks.
5. **Pass:** staff/faculty are denied all platform APIs and cannot assign a
   platform role.
6. **Pass:** missing or inactive institution scope fails closed across the
   audited staff/faculty capabilities.
7. **Gap, not reachable vulnerability:** membership approval logic has no HTTP
   route, so University Admin cannot currently complete onboarding through the
   product.
8. **Design limitation:** `(user_id, role_id)` uniqueness means one same-named
   role cannot be held across several institutions. Future work must not silently
   reinterpret this as multi-institution support.
9. **Defense-in-depth limitation:** tenancy is enforced by service-role-backed
   application code and database integrity triggers rather than end-user RLS,
   consistent with the existing architecture.

## Staff/Faculty Lifecycle

Currently supported in code:

```text
self-registration
  -> Supabase Auth account + public.users(status=active)
  -> institution_membership_requests(status=pending; no role)
  -> tested service-level approve/reject
  -> institution-scoped staff/faculty role on approval
  -> login + role shell
```

Operationally missing: the Admin queue/decision API and UI. Also missing are a
staff/faculty invitation entry point, roster, explicit suspension/deactivation,
reactivation, revocation, resend/cancel for staff/faculty, and lifecycle audit
UI. Admin invitation lifecycle states exist only for University Admins and must
not be conflated with membership-request state.

## Missing Capabilities

- University Admin staff/faculty pending-request queue and decision API/UI.
- Institution staff/faculty roster with safe status, role, and scope projection.
- Safe grant revocation/deactivation/reactivation and audit trail.
- Staff/faculty invitation using the existing email/outbox/provider/webhook
  infrastructure without broadening admin/platform authority.
- Frontend staff/faculty registration or invite acceptance UX, depending on the
  chosen canonical onboarding path.
- Faculty profile and explicit teaching assignment/resource model.
- Faculty-scoped student, attendance, and results contracts.
- A usable staff/faculty knowledge workflow (authorized source listing plus
  ingestion UI) if product policy confirms it.
- Any staff notice/FAQ/read policy; none should be inferred from role names.

## Recommended Implementation Phases

1. **Phase 7.23 — University Admin Staff/Faculty Onboarding & Roster.** Mount
   institution-scoped list/approve/reject APIs over the existing membership
   services, add a safe roster and lifecycle actions, and add the University
   Admin UI. Reuse `require_institution_roles("admin")`, `user_roles`, and the
   existing audit patterns. Decide explicitly whether self-registration remains
   canonical or whether the existing invitation lifecycle is generalized; do
   not ship two competing paths.
2. **Faculty Academic Scope Foundation.** Add faculty profile/assignment
   relationships and prove Faculty A cannot reach unassigned or Institution B
   resources before exposing students, attendance, or results.
3. **Scoped Academic Operations.** Add the smallest separately authorized
   attendance/results capabilities based on those assignments, with resource
   chain tests.
4. **Staff/Faculty Knowledge Experience.** If policy approves, expose a
   tenant-safe source list and ingestion management UI over the existing
   pipeline; keep publish/delete/FAQ permissions explicit.

## Verification

Commands used local/test infrastructure only. The host exported an invalid
`DEBUG=release`; the first focused collection therefore stopped with 17 config
errors and no tests executed. The actual audit runs explicitly set
`DEBUG=true`, matching the repository's development-test baseline.

| Check | Exact result |
| --- | --- |
| Focused backend audit (17 files: staff, faculty, cross-role, Phase 7.20, RBAC/scope, registration/approval, auth, invitation 7.14–7.18, tenant, ingestion, attendance, results) | **577 passed, 6 skipped**, 5 warnings, 43.58 s |
| Focused chat/cross-role remediation regression (4 files) | **136 passed**, 3 warnings, 28.35 s |
| Complete backend suite: `uv run pytest -q tests` | **2495 passed, 27 skipped**, 6 warnings, 95.81 s |
| Frontend: `npm.cmd test -- --run` | **58 files / 519 tests passed**, 184.37 s |
| TypeScript: `npx.cmd tsc -b --force` | **PASS** (exit 0) |
| Production build: `npm.cmd run build` | **PASS**, 112 modules transformed, Vite 7.3.6 |
| Migration | **NONE** |

Warnings were existing Starlette/httpx, Supabase client deprecations, and two
Pydantic test-class collection warnings; there were no test failures.

## Remote Safety and Artifact Hygiene

- Remote Supabase changed: **NO**
- Migration pushed or created: **NO**
- Production users, roles, institutions, or data changed: **NO**
- Production email sent / Mailgun invoked: **NO**
- Broad runtime/architecture rewrite: **NO**; one scoped authorization fix
- Only local unit/integration mocks and build tooling were used. No local or
  remote Supabase mutation command was run.

