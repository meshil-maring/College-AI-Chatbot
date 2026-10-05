# Phase 8.1 — RBAC Completion Report

Date: 2026-10-06

## Status

**IMPLEMENTATION COMPLETE — MIGRATION VERIFICATION BLOCKED**

The four implementation objectives are complete: protected routes have
permission enforcement, Staff permission administration is tenant-scoped,
Faculty access can be scoped to assigned sections, and role/permission changes
write durable audit events. The existing authentication, role, permission,
tenant-resolution, and audit infrastructure is extended rather than replaced.

The migration has not been replayed. Runtime database verification remains a
separate deployment activity and is not represented as passed here.

This report supersedes the open Definition-of-Done items in
[`GRANULAR_RBAC_PERMISSIONS_PHASE_REPORT.md`](./GRANULAR_RBAC_PERMISSIONS_PHASE_REPORT.md)
as of this date; that earlier report remains a snapshot of the Phase 8
foundation before this increment.

## Authorization matrix

The exact HTTP-method/path-to-permission mappings for every Admin and Platform
route are the `_ADMIN_ROUTE_PERMISSIONS` and `_PLATFORM_ROUTE_PERMISSIONS`
tables. Each route is protected by its router-level authorization dependency;
an unmapped route fails closed. The Phase 8.1 route-inventory test iterates the
registered routes to ensure each has a mapping. The other protected surfaces
listed below enforce permissions in their route handlers or dependencies.

| Endpoint and HTTP method | Authentication / required permission | Allowed role(s) and scope | Resource and ownership rule | Existing tests / remaining test gap |
| --- | --- | --- | --- | --- |
| `GET`, `POST`, `PATCH`, `DELETE /api/v1/admin/...` — concrete method/path keys are enumerated in `backend/app/api/admin.py` | Authenticated; the exact action permission is attached to each key in `_ADMIN_ROUTE_PERMISSIONS` (users, students, results, attendance, documents, notices, AI knowledge, audit, Staff grants, Faculty assignments) | Existing active institution `admin`; existing server-resolved platform scope remains supported where the underlying service allows it | Existing institution checks remain authoritative; row and student resource checks remain in the endpoint/service; no permission bypasses tenant or ownership checks | Route-map coverage, Phase 8.1 authorization, Admin API, and tenant-isolation suites. A dedicated denial/tenant test for every individual route is not exhaustive. |
| `GET`, `POST`, `PATCH /api/v1/platform/...` — concrete method/path keys are enumerated in `backend/app/api/platform.py` | Authenticated; `platform.read`, `platform.manage`, or `platform.audit.read` per route | Active `super_admin` with server-resolved platform scope | Platform-level institution management only; tenant records remain limited to the projections/services already exposed | Route-map coverage, platform authorization and lifecycle suites. Per-route test cases are not exhaustive. |
| `POST /api/v1/organizations/{organization_id}/decision` | Authenticated; `platform.manage` | Platform-scoped authority; organization administrators cannot approve their own organization | The service independently verifies platform scope, organization identity, and pending lifecycle state | Organization decision policy inventory and approval/scope lifecycle tests; tenant mismatch and self-approval are covered. |
| `POST /api/v1/institutions/join-requests/{join_request_id}/decision` | Authenticated; `organizations.manage` | Owning organization admin, or platform admin, under the existing scope guard | Join request and institution are resolved server-side; only the owning organization can decide | Institution decision policy inventory and approval/scope lifecycle tests cover organization mismatch and inactive tenants. |
| `GET /api/v1/students/me/profile`, `/me/academic-profile` | Authenticated; `profile.own.read` | Authenticated student identity | Identity and institution are resolved from the current user; only the caller's profile is returned | Auth, student experience, and Phase 8 permission tests. |
| `GET /api/v1/students/me/results...`, `/me/test-results...` | Authenticated; `results.own.read` | Authenticated student identity | Services resolve only the caller's published results; foreign, missing, or unpublished detail follows the existing non-enumerating behavior | Student result, cross-role, and tenant-isolation suites. |
| `GET /api/v1/students/me/attendance...` | Authenticated; `attendance.own.read` | Authenticated student identity | Services resolve only the caller's attendance; optional query fields narrow but cannot replace identity or tenant | Student attendance and cross-role suites. |
| `GET /api/v1/students/me/notices`, `/me/resources` | Authenticated; `notices.read`, `documents.read` respectively | Authenticated student identity | Existing public-visibility, institution, and safe-projection checks remain in force | Student experience and public visibility suites. |
| `GET /api/v1/students/me/notifications`, `/unread-count`, `/{notification_id}` | Authenticated; `notifications.own.read` | Authenticated student identity | Student ID is server-resolved; detail lookup returns no foreign notification | Notification authorization tests and Phase 8.1 tests. |
| `PATCH /api/v1/students/me/notifications/{notification_id}/read` | Authenticated; `notifications.own.update` | Authenticated student identity | Only the caller's notification read-state can change; no ownership or content fields are accepted | Notification authorization tests cover own/foreign behavior. |
| `POST /api/v1/documents/ingest` and `POST /api/v1/documents/{processing_run_id}/{extract,chunk,embed}` | Authenticated; `ai.knowledge.create` | Active institution `admin`, `staff`, or `faculty` | Knowledge source and processing run are tenant-checked before mutation | Ingestion authorization and tenant-isolation suites. |
| `POST /api/v1/generation/chat` | Authenticated; `ai.chat` | Active institution `admin`, `staff`, `faculty`, or `student` | Requested institution is checked against server-resolved scope; conversation data remains user-owned | Chat authorization, tenant-isolation, and conversation suites. |
| `GET /api/v1/conversations`, `/api/v1/conversations/{conversation_id}/messages` | Authenticated; `ai.chat` | Authenticated account with chat permission | Conversation history queries are constrained to the current user | Conversation ownership and chat authorization suites. |
| `GET /api/v1/faculty/assignments` | Authenticated; `faculty.assignments.read` | Active institution `faculty` | Only active assignments for the authenticated Faculty member are returned | Phase 8.1 assignment API tests and Faculty UI tests. |
| `POST /api/v1/dev/auth/admin/reset-student-password` | Authenticated; `users.update` plus existing `admin` role | Admin role and development/test mode only | Server resolves the target account; endpoint is unavailable outside development/test mode | Dev-auth security tests cover the mode and role gates. |
| `GET /api/v1/auth/me` | Authenticated; safe identity projection; no feature permission required | Any authenticated account, including accounts with no supported application role | Returns only the current caller's server-resolved identity, role, institution, and effective permissions | Auth contract and Phase 8 permission tests. |
| Registration, signup/login, public chat, invitation inspection/acceptance, Mailgun webhook, health/readiness, and development recovery routes | Intentionally public or independently capability/credential/webhook-authorized; no application permission grant is required | Public caller, valid one-time invitation token, verified provider signature, or development/test-only caller as applicable | Each flow retains strict schemas, server-side tenant resolution, token/credential proof, provider signature, or public visibility controls | Existing registration, invitation, public-chat, webhook, and platform readiness suites. |

The source maps above are the exact method/path inventory for Admin and Platform
routes. The matrix groups those route keys by shared policy and inherited
tenant/resource guards; the route-coverage test detects newly added Admin or
Platform routes that lack a policy entry.

## Permission administration

- Added safe Admin APIs to list the delegable Staff permission catalogue,
  inspect a Staff member's effective permission sources, grant, and revoke
  direct permissions.
- Direct grants are limited to an explicit allowlist. The target must be an
  active Staff member with an active Staff role in the same active institution;
  administrators cannot grant to themselves or edit global `role_permissions`.
- Grant and revoke operations use one database RPC per change. The RPC validates
  the actor and target scope, records a revocation rather than erasing history,
  and inserts an audit event in the same transaction.
- Added the University Admin permission-manager UI and API client calls. UI
  visibility is presentation-only; the backend remains authoritative.

## Faculty academic assignment scope

- Added revocable Faculty-to-section assignments with institution and user
  foreign keys. Assignment creation validates the active Faculty role and
  validates that the active section's course offering and department belong to
  the same institution.
- Faculty can read only their own active assignments. University Admins can
  assign and revoke assignments only within their institution.
- Added the Admin assignment-management UI and Faculty “My Sections” view.
- This relation grants visibility to assigned sections only. It does not invent
  a Faculty-to-student enrollment relationship or grant access to student
  records, attendance, or results by itself.

## Durable audit

- Staff direct-permission grants/revocations, Faculty assignment grants/
  revocations, and institution-scoped Staff/Faculty role assignments insert
  append-only `admin_audit_log` events in the same database transaction as the
  mutation.
- Audit rows carry the actor, institution, action, target record, and bounded
  change summary; credentials and invitation secrets are excluded.
- The existing audit API now constrains reads to the current actor and tenant;
  a detail lookup verifies both before returning a row.
- Existing platform-institution audit behavior is retained. No replacement
  audit table or alternate authentication/role-resolution system was added.

## Verification

| Command/check | Result |
| --- | --- |
| `cd backend; .venv\Scripts\python.exe -m pytest tests -q` | **2,632 passed, 27 skipped, 6 warnings** |
| Frontend Vitest, `npm --prefix frontend test -- --maxWorkers=1` | **545 passed across 64 files** |
| Frontend production build, `npm --prefix frontend run build` | **PASS** (TypeScript and Vite build) |
| Focused Phase 8.1 and affected backend regressions | **313 passed**; additional tenant-audit/invitation regressions **46 passed** |
| Pylance diagnostics on changed backend authorization files | **No errors found** |
| `git diff --check` | **PASS** (line-ending notices only) |
| Migration replay | **Not run; Docker Desktop Linux engine unavailable** |

## Migration verification

MIGRATION VERIFICATION: BLOCKED
Reason: Docker/Supabase runtime unavailable.

The Docker CLI is installed, but `docker info` cannot connect to
`npipe:////./pipe/dockerDesktopLinuxEngine`. No local migration replay or
remote migration push was attempted. Migration-source tests pass; this does not
prove clean-database or existing-database application. Replay and runtime SQL
validation remain deployment follow-up work.
