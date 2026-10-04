# Phase 7.23 — Staff & Faculty Onboarding & Roster

## Status

**COMPLETE**

University Admins can now operationally manage institution Staff and Faculty
through a request queue, decisions, invitations, a roster, and activation
lifecycle — all built on the existing Phase 6.13 membership workflow and the
existing Phase 7.14–7.18 invitation/email architecture. No second user system,
authentication system, token system, invitation system, or email provider was
introduced.

## Existing Workflow Reused

Phase 7.22 audited the existing workflow. Every integration point below is
pre-existing and was reused rather than duplicated:

| Existing asset | Reused for Phase 7.23 |
| --- | --- |
| `institution_membership_requests` table | Request queue, decision state machine |
| `MEMBERSHIP_REQUEST_COLUMNS` (`app/repositories/tenancy.py`) | Safe request projection |
| `tenancy_repo.assign_membership_role` | Acceptance-time role grant |
| `assign_user_role_scope` + Phase 6.13 scope trigger | Structural cross-organization grant prevention |
| `platform_admin_invitations` table | Invitation storage (extended, not replaced) |
| `phase717_create_invitation_with_outbox` | Invitation + outbox creation (added an overload) |
| `email_outbox` + `email_outbox_crypto` | Encrypted delivery payload |
| `invite_repo.generate_invitation_token` / `hash_invitation_token` | Raw-token generation / hashing |
| `invite_repo.claim_invitation` | One-time acceptance gate |
| `resend_invitation` (Phase 7.15–7.18) | Resend rotation |
| `abuse.enforce_accept_rate_limit` | Acceptance abuse budget |
| `record_admin_action` (`admin_audit_log`) | Lifecycle audit events |
| `users.status` | Account activation state |

New files are limited to a thin service/repository/schema/API/UI layer over
those primitives.

## Request Lifecycle

```
Membership Request (staff|faculty, pending)
   -> University Admin Review
      -> Reject (no role, no invitation)
      -> Approve
         -> Institution invitation + encrypted outbox row
            -> Mailgun delivery + webhook reconciliation
               -> Applicant sets password
                  -> Atomic one-time claim
                     -> Institution-scoped role grant
                        -> Active Staff/Faculty on roster
                           -> Deactivate / Reactivate
```

## Approval / Rejection

Endpoints (mounted on the existing `/api/v1/admin` router):

- `GET /api/v1/admin/memberships/requests`
- `POST /api/v1/admin/memberships/requests/{request_id}/approve`
- `POST /api/v1/admin/memberships/requests/{request_id}/reject`

Approval verifies, in order: request exists in the admin's institution; the
current status is `pending`; `requested_role` is `staff` or `faculty`; the
institution is `active` and `is_active`; the applicant user row exists, matches
the request email, and is `status = 'active'`. Tenant, role, institution, and
applicant checks are re-verified **inside** the database transaction, so a
service-side check can never be bypassed by a race.

Rejection performs a pending-only conditional update, assigns no role, and
sends no invitation. Both decisions record audit events.

## Invitation Architecture

The generic Phase 7.14–7.18 architecture was **extended**, not duplicated:

- `platform_admin_invitations.role_name` CHECK widened from `{admin}` to
  `{admin, staff, faculty}`. `super_admin` remains structurally impossible.
- `phase717_create_invitation_with_outbox` gained a **seven-argument overload**
  (the six-argument Phase 7.17 function is untouched, so existing callers and
  deployments remain compatible). The overload independently re-checks the role
  allowlist and rejects anything else with SQLSTATE `22023`.
- `phase717_resolve_email_outbox_context` now carries `role_name` so the outbox
  worker renders the correct invitation copy.

The applicant never controls role or scope. The role travels to the invitation
from `institution_membership_requests.requested_role` inside the transaction,
and the institution travels from the server-resolved authorization context.


## Acceptance Flow

`accept_invitation` was generalized from the Admin-specific path:

1. Rate-limit budget charged before any credential is touched.
2. Token resolved to the invitation row; status and expiry validated.
3. Institution resolved **from the row**, then required to be active.
4. Email derived **from the row**; the accept schema is `extra="forbid"` and has
   no email, institution, or scope field.
5. Auth account created via the existing GoTrue primitive (or, for
   self-registered staff/faculty, the **existing identity is linked** and only
   its password rotated — no second account is created).
6. `public.users` row created or linked.
7. Atomic `claim_invitation` — losing this race grants nothing.
8. Role granted from the stored `role_name` and stored institution:
   `admin` keeps `assign_institution_admin`; `staff`/`faculty` use
   `assign_membership_role`.
9. Email verification recorded and audited.

## Roster

`GET /api/v1/admin/memberships` returns `staff` and `faculty` entries only,
merging institution-scoped role grants with the institution's own `invited`
invitations so pending members are visible.

Fields are safe by construction: display name, email, role, status, invitation
status, created/updated timestamps, and the user/invitation id needed for
actions. Passwords, hashes, tokens, and internal secrets are never selected.

## Activation / Deactivation

`POST /api/v1/admin/memberships/{user_id}/deactivate|reactivate` uses the
**existing** `users.status` column — no second account-status system.

Guards: the target must hold a `staff`/`faculty` grant scoped to the admin's
own institution; if the user holds any role outside `{staff, faculty}` the
operation is refused with `PROTECTED_ROLE`. This blocks an admin from touching
another institution's user, an `admin`, or a `super_admin`. Writes are
conditional on the expected prior status, and repeating an action returns
`already_applied = true`. Reactivate never recreates a deleted account.

## Authorization

Every endpoint uses the Phase 7.20 locked chain:

```
JWT -> get_current_user -> user_roles -> institution AuthorizationContext
    -> require_institution_roles("admin") -> tenant-scoped service
```

The API accepts **no** `institution_id` parameter on any membership route.
`institution_id` in the request body is rejected (`extra="forbid"` on
`MembershipDecisionBody`). The institution always comes from
`user_tenant_id(current_user)`.

## Tenant Isolation

- Repository queries filter on `.eq("institution_id", <server value>)`.
- `get_request_for_institution` matches on request id **and** institution, so a
  foreign request id resolves to `None` → `404 MEMBERSHIP_REQUEST_NOT_FOUND`
  before any invitation is created.
- The approval RPC's `FOR UPDATE` lookup is itself tenant-qualified and returns

## Role Escalation Protection

- `requested_role` is CHECK-constrained to `{staff, faculty}` at the database
  level.
- Service `_role()` rejects `admin`, `super_admin`, and any other value with
  `422 INVALID_MEMBERSHIP_ROLE`.
- The migration's role allowlist contains no `'super_admin'::text` literal
  (asserted by test).
- The RPC re-checks `requested_role NOT IN ('staff','faculty')` inside the
  transaction.
- Acceptance reads the role from the stored invitation and rejects anything
  outside `INSTITUTION_INVITED_ROLES = {admin, staff, faculty}`.
- Only `require_institution_roles("admin")` reaches these routes — `staff`,
  `faculty`, and `student` receive `403 FORBIDDEN` (verified by test).
- There is no generic `PATCH /users/{id}` role interface.

## Concurrency

Approval is a single database transaction
(`phase723_approve_membership_with_invitation`): `SELECT ... FOR UPDATE` on the
request, state re-checks, invitation + outbox creation, then the status update.

- Approve/approve → the second call observes `already_applied` and returns
  `already_applied = true`. Exactly one invitation is created.
- Approve/reject → the loser receives `409 MEMBERSHIP_REQUEST_CONFLICT`.
- Rejection uses a pending-only conditional update; the loser falls back to a
  re-read and returns `already_applied = true` or `409`.
- Lifecycle writes are conditional on the expected prior status and return
  `409 MEMBERSHIP_STATUS_CONFLICT` on a lost race.

No duplicate accounts, duplicate role assignments, or duplicate active
invitations can result.

## Email Delivery

Delivery remains `invitation -> email_outbox -> worker -> Mailgun -> webhook`.
The approval transaction writes the `email_outbox` row with an **encrypted**
`protected_token` via `email_outbox_crypto`; the raw token is never stored.
Tests use fakes and mocks exclusively — no Mailgun call is made during
verification, and no production email was sent.

## Frontend

`StaffFacultyManager.tsx` is added to the **existing** `AdminShell` (no
redesign) under the nav item "Staff & Faculty".

- Requests section with All / Staff / Faculty / Pending filters, Approve and
  Reject buttons with confirmation dialogs.
- Roster table with Name, Email, Role, Status, Invitation, Actions.
- Actions: Deactivate, Reactivate, Resend invitation.
- UI states: loading, empty requests, empty roster, approval/rejection
  confirmation, per-action loading, success, error.
- No optimistic mutation — every action awaits the server response and then
  reloads, per the security requirement for server-confirmed state.
- No tokens, passwords, or secrets are rendered.

  `not_found` for a foreign id.
- Lifecycle actions require a grant scoped to the caller's institution.
- The roster only reads this institution's grants and invitations; another
  tenant's `admin` invitation is excluded by the role allowlist.
- Filters (`role`, `status`) are applied **after** the tenant scope is fixed and
  are never an authorization input.

## Tests

Focused — `backend/tests/test_phase_7_23_staff_faculty_onboarding_roster.py`:
**22 passed**.

Coverage includes request listing pinned to the server institution; non-admin
roles blocked from approving and from modifying the roster; role-escalation
filter rejection; foreign request id failing without inviting; server-owned role
on approval; rejection assigning no role; invalid applicant blocked before
transition; idempotent repeat decision; approve/reject race conflict; roster
tenant merge; cross-tenant deactivation; protected-role refusal; lifecycle
status transitions; migration allowlist; and staff invitation acceptance linking
the existing identity and granting the stored scope.

Full suites:

| Suite | Result |
| --- | --- |
| Focused Phase 7.23 | 22 passed |
| Backend (`pytest tests`) | **2517 passed**, 27 skipped |
| Frontend (vitest) | **521 passed** across 59 files |
| TypeScript (`tsc --noEmit`) | PASS, no errors |
| Production build (`tsc -b && vite build`) | PASS |
| Frontend bundle/secret scan | PASS — 4 dist files scanned, env allowlist `VITE_API_BASE_URL` |

Six collection errors under `scripts/manual_tests/` and
`scripts/validation/` are pre-existing network-dependent scripts (they attempt
real HTTP calls at import time) and are not part of the suite.

## Migration

**`supabase/migrations/20261004000000_phase_7_23_staff_faculty_onboarding_roster.sql`**

A durable change is genuinely required, because atomic approval with
invitation creation cannot be expressed as separate PostgREST calls. The
migration:

1. Widens `platform_admin_invitations.role_name` CHECK to
   `{admin, staff, faculty}`.
2. Adds the seven-argument `phase717_create_invitation_with_outbox` overload.
3. Replaces `phase717_resolve_email_outbox_context` to carry `role_name`.
4. Adds `phase723_approve_membership_with_invitation`.

No table is duplicated and no new table is created. All functions are
`SECURITY DEFINER SET search_path = ''` with `REVOKE ALL ... FROM PUBLIC, anon,
authenticated` and an explicit `GRANT EXECUTE ... TO service_role`.

## Remote Safety

- Remote Supabase changed: **NO**. The migration is local and unapplied.
- Production email sent: **NO**. No Mailgun invocation occurred.
- Production webhook invoked: **NO**.
- Production institutions/roles/data modified: **NO**.
- No remote migrations were pushed; all verification used local test doubles.

## Limitations

- **Role conversion (staff ↔ faculty) is OUT OF SCOPE**, as permitted by the
  brief. The existing role model is a single scoped grant per role and does not
  define a safe conversion semantic; no generic role-edit interface exists.
- The approval transaction depends on the new PostgreSQL RPC. Until the
  migration is applied to a given database, approval returns an error rather
  than falling back to a non-atomic path — a deliberate fail-closed choice.
- Roster invitation rows appear with an empty display name, because the
  applicant's name is not stored on the invitation row (it lives on the
  membership request).
- Phase 7.15's invitation expiry sweep still has no background scheduler in
  this deployment; as documented there, expiry is enforced at acceptance time
  regardless of whether the sweep has run.

