# Phase 6.15.4 — Authentication Role Resolution & Session Lifecycle

## 1. Objective

Replace the probe-based role detection (`GET /admin/me` → 200 = admin,
403 = student) with a clean, server-authoritative role resolution flow, and
add proper session-expiry handling — without changing the underlying RBAC
model.

Before:

```text
Login → AuthProvider → GET /auth/me → App.tsx → GET /admin/me → shell
```

After:

```text
Login → AuthProvider → GET /auth/me (identity + role) → shell
```

## 2. Existing Role-Resolution Architecture (inspected, pre-change)

* `backend/app/core/security.py::get_current_user` — verifies the Supabase
  JWT, resolves `public.users` via `get_user_by_auth_id`, and ALREADY returned
  `{ user_id, auth_user_id, email, roles, institution_id }` server-side.
  `roles` are the active names from `user_roles → roles` (the Phase 6.6 RBAC
  source); `institution_id` is the tenant, resolved from the one-to-one
  `students` profile (`app/db/supabase.py`).
* `backend/app/main.py::auth_me` (`GET /api/v1/auth/me`) — returned only
  `{ authenticated, user_id, auth_user_id, email }`; the resolved roles were
  dropped on the floor.
* `frontend/src/App.tsx::AuthenticatedShell` — the Phase 6.15.3 leftover:
  `getAdminIdentity()` (`GET /admin/me`) probe; 200 → AdminShell, anything
  else → StudentShell. Staff/faculty were indistinguishable from students and
  every student login spent one failed (403) probe request.
* `frontend/src/features/admin/AdminShell.tsx` — a SECOND `/admin/me` call
  for header identity, with its own loading/denied states.
* Session expiry was handled only inside the restore/login bootstrap
  (`AuthProvider`); an in-session 401 from a feature API call left the UI
  authenticated with no recovery path.

## 3. New Canonical Identity Contract

`GET /api/v1/auth/me` (Phase 6.15.4, additive):

```json
{
  "authenticated": true,
  "user_id": "...",
  "auth_user_id": "...",
  "email": "admin@college.edu",
  "role": "admin",
  "institution_id": null
}
```

* `role` — canonical, single, server-resolved. `null` when the account holds
  no supported role (fails safe).
* `institution_id` — tenant context (the same key the rest of the
  application uses for tenancy); `null` for platform-level accounts. No other
  internal database IDs are exposed (`user_id`/`auth_user_id` were already
  part of the locked Phase 5.4 contract and are preserved byte-for-byte).

## 4. `/auth/me` Changes

Smallest compatible backend change — the response schema was extended, no
new endpoint, no endpoint removed:

* `backend/app/core/security.py` — additive primitives:
  * `SUPPORTED_ROLES: tuple = ("admin", "staff", "faculty", "student")` —
    the EXISTING Phase 6.6 role names (verified in the `roles` table,
    `require_roles` usages, and `get_role_by_name`). No new role.
  * `resolve_primary_role(roles)` — canonical single-role resolution with
    precedence `admin > staff > faculty > student`; returns `None` for
    unknown/unsupported roles (never surfaces one).
* `backend/app/main.py` — `auth_me` now returns
  `resolve_primary_role(current_user["roles"])` and
  `current_user["institution_id"]` in addition to all existing fields.

Evaluation: `/auth/me` CAN safely be extended because `get_current_user`
already resolves roles + tenant server-side; a dedicated identity endpoint
was therefore NOT created.

## 5. Role Resolution

Server-authoritative chain (unchanged data sources):

```text
JWT/session → get_current_user → get_user_by_auth_id
    (public.users → user_roles → roles, active only)
    → tenant from students.institution_id
    → resolve_primary_role → /auth/me → frontend consumes
```

The frontend never derives a role from email, identifier format, URL,
localStorage, registration state, or any client-provided value — it only
renders `user.role` returned by the backend. `/admin/me` (and its
`require_roles("admin")` guard) is untouched for actual admin API use; it is
no longer called by the general authentication bootstrap. No
`/staff/me`/`/faculty/me`/`/student/me` endpoints were introduced.

## 6. AuthProvider Changes

Smallest safe change to the existing Phase 5.4 provider (not rewritten):

* `AuthContextValue.role` — readonly `AuthRole | null`, derived from
  `user.role` (canonical, server-provided). Institution/tenant context is
  available as `user.institution_id`.
* `handleSessionExpired` — subscribes to the session-expiry event bus
  (`services/sessionEvents.ts`). A global 401 handler for AUTHENTICATED
  requests only: clears the stored token, user, and access token, sets the
  fixed user-safe message, and returns to login. Guarded by a status check
  so stale notifications after logout are no-ops.
* `login()` and `restore()` flows are otherwise unchanged: both bootstrap
  through `GET /auth/me`, so the state shape is identical whether the
  session is fresh or restored (refresh-safe for all roles).

## 7. Shell Selection

`frontend/src/App.tsx::AuthenticatedShell` — selected purely from the
canonical role (no probe, no loading state):

| role                           | shell                                              |
|--------------------------------|----------------------------------------------------|
| `admin`                        | `AdminShell`                                       |
| `staff`                        | `StudentShell` (no dedicated staff UI yet)         |
| `faculty`                      | `StudentShell` (no dedicated faculty UI yet)       |
| `student`                      | `StudentShell`                                     |
| `null` / unknown / unsupported | `UnsupportedRoleShell` — safe fallback, no privileged UI, sign-out available |

No new dashboards were invented and no dashboard functionality was modified.
`AdminShell` no longer re-probes `/admin/me`; it renders identity from the
same AuthProvider state (one authenticated request bootstraps everything).
Backend authorization is unchanged: every admin API request still carries the
bearer token and `/admin/*` still rejects non-admin tokens with 403.

## 8. Session Expiry Handling

New `frontend/src/services/sessionEvents.ts` — a dependency-free
publish/subscribe seam:

* `notifySessionExpired()` — published by API clients on 401 for
  token-carrying (authenticated) requests.
* `onSessionExpired(listener)` — subscribed by `AuthProvider` only.
* `SESSION_EXPIRED_MESSAGE = 'Your session has expired. Please log in again.'`

Flow:

```text
Authenticated user → API request → 401 TOKEN_EXPIRED / INVALID_TOKEN /
USER_NOT_FOUND → API client notifies → AuthProvider clears state + token →
login screen with the safe message
```

Global integration points (no per-feature 401 handling, no circular
dependencies — the bus module imports nothing):

* `services/api.ts` — chat + conversations (3 request paths).
* `services/adminApi.ts` — single `requestJson` gateway used by every
  admin/student call.

## 9. 401 Classification

The Phase 6.15.3 operation-aware classifier in `services/auth.ts` is
INTACT and untouched:

| operation                                       | status   | backend code          | classified kind         | UI message                                       |
|-------------------------------------------------|----------|-----------------------|-------------------------|--------------------------------------------------|
| login (`/auth/login`, `/auth/student/login`)    | 400/401  | `INVALID_CREDENTIALS` | `invalid_credentials`   | generic credentials message                      |
| session (`/auth/me`)                            | 401/404  | `TOKEN_EXPIRED` etc.  | `session_invalid`       | saved-session message                            |
| authenticated feature API                       | 401      | any                   | `session_expired` event | "Your session has expired. Please log in again." |

Bad credentials can never reach the session-expiry channel: login failures
are classified inside the auth service and never published on the bus.

## 10. Logout Behavior

Unchanged semantics (verified): clears auth state, removes the localStorage
token (`college-ai-chatbot.access-token`), and returns to the unauthenticated
login screen. No server-side revocation call — the backend is stateless JWT
and exposes no logout endpoint (pre-existing architecture, unchanged).

## 11. Security Verification

* Role resolved server-side only (JWT → user_roles → roles); the frontend
  cannot grant roles — mutating localStorage or in-memory state yields no
  privilege (admin UI requires `role === 'admin'` FROM the server response,
  and every admin API call is still authorized server-side by
  `require_roles("admin")`).
* Unknown roles fail safe (no privileged UI, dedicated fallback shell).
* Expired tokens invalidate the session globally on the next authenticated
  401.
* Invalid login credentials never trigger session-expiry handling.
* Tokens and passwords are never logged or rendered; expiry messaging is a
  fixed safe string (no backend error text).
* No unnecessary internal IDs exposed (contract is additive; `role` and
  `institution_id` only).
* Anti-enumeration behavior untouched (login contract unchanged).
* Existing RBAC unchanged (`require_roles`, tenant guards, role names).

## 12. Frontend Tests

New `src/features/auth/AuthProvider.test.tsx` (11 tests):

* Restore: authenticated restore with role from `/auth/me`; admin role on
  restore; no token → no API call; session-invalid response clears the
  stored token.
* Login bootstrap: token stored + canonical identity/role loaded; rejected
  login shows `invalid_credentials` and never stores the token.
* Session expiry: authenticated 401 event clears session/token, shows the
  safe message; notification while unauthenticated is a no-op.
* Logout: state clears, token removed.

Updated `src/App.test.tsx` (6 tests): admin → AdminShell (with an assertion
that `getAdminIdentity` is NOT called); student/staff/faculty → student
shell; unknown role → "Access restricted"; `null` role → "Access restricted".

Updated `src/features/admin/AdminShell.test.tsx` (2 tests): identity from
auth state (no `/admin/me` fetch); navigation items render.

Regression: `services/auth.test.ts` (24 tests) — including the mandatory
"student login 401 `INVALID_CREDENTIALS` → `invalid_credentials`; /auth/me
401 `TOKEN_EXPIRED` → `session_invalid`" classification pair — all pass
unchanged.

## 13. Backend Tests

New in `backend/tests/test_auth.py` (9 tests):

* Identity: `test_valid_jwt_with_user` extended (role/institution additive);
  unauthenticated rejected preserved.
* Role resolution: admin/staff/faculty/student each resolve; precedence for
  multi-role accounts; unknown role → `None` (fail-safe).
* Tenant: student role resolved within the correct institution context.
* Security: client-provided `role`/`institution_id` query data cannot alter
  the server-resolved response.

## 14. Full Test Results

Frontend (`npm test` + `npm run build`):

```text
passed: 152   failed: 0   skipped: 0
build:  tsc -b && vite build — success (no TypeScript errors)
```

Backend (authentication / RBAC / security / tenant suites):

```text
passed: 314   failed: 0   skipped: 0
  test_auth.py (17) · test_student_auth_phase_6_5.py · test_rbac_phase_6_6.py
  test_admin_api.py · test_sign_in_phase_6_13_6.py (202 combined)
  test_role_scope_enforcement_phase_6_13_7.py +
      test_security_final_validation_phase_6_13_9.py (112)
  test_tenant_isolation.py (12)
```

No failures — pre-existing or introduced.

## 15. Files Changed

Backend:

```text
backend/app/core/security.py        — SUPPORTED_ROLES + resolve_primary_role (additive)
backend/app/main.py                 — /auth/me extended with role + institution_id
backend/tests/test_auth.py          — 9 new Phase 6.15.4 tests
```

Frontend:

```text
frontend/src/types/auth.ts                       — AuthRole + CurrentUser.role/institution_id
frontend/src/services/sessionEvents.ts           — NEW session-expiry event bus
frontend/src/services/api.ts                     — global 401 notify (3 request paths)
frontend/src/services/adminApi.ts                — global 401 notify (requestJson gateway)
frontend/src/features/auth/AuthProvider.tsx      — role in state + expiry subscription
frontend/src/App.tsx                             — role-based shell selection (probe removed)
frontend/src/features/admin/AdminShell.tsx       — identity from auth state (probe removed)
frontend/src/App.test.tsx                        — rewritten role-gating tests
frontend/src/features/admin/AdminShell.test.tsx  — updated for state-driven identity
frontend/src/features/auth/AuthProvider.test.tsx — NEW provider/session tests
```

Documentation:

```text
PHASE_6_15_4_AUTH_ROLE_SESSION.md    — this document
```

## 16. Known Limitations

* Staff/faculty have no dedicated UI (pre-existing); they receive the student
  shell — identical to the previous probe behavior, minus the wasted request.
  A future phase can add `StaffShell`/`FacultyShell` without further backend
  changes (the role is already in state).
* Global 401 handling covers `services/api.ts` and `services/adminApi.ts`
  (all existing authenticated feature clients). Any future standalone client
  must publish `notifySessionExpired()` on authenticated 401s — the bus is
  the single canonical seam.
* Token remains in localStorage (documented Phase 5.4 tradeoff, unchanged;
  no refresh token exists).
* `/admin/me` endpoint remains available (used by validation scripts and its
  own backend tests); only the frontend bootstrap stopped calling it.

## 17. Final Verification

* [x] Current role-resolution architecture inspected
* [x] Canonical role source established (server-side user_roles → roles)
* [x] `/auth/me` evaluated and extended (smallest compatible change)
* [x] Server-authoritative role resolution implemented
* [x] `/admin/me` no longer used for general role detection
* [x] Admin / staff / faculty / student roles verified (backend + frontend tests)
* [x] AuthProvider updated (role in state, expiry subscription)
* [x] Login bootstrap verified (token → /auth/me → role → shell)
* [x] Refresh bootstrap verified (restore path identical for all roles)
* [x] Shell selection verified for all roles + unknown-role fallback
* [x] Unknown-role handling implemented (no privileged UI)
* [x] Frontend role tampering grants no privileges
* [x] Global session-expiry handling implemented (api.ts + adminApi.ts)
* [x] Authenticated 401 correctly invalidates the session
* [x] Login 401 remains `invalid_credentials` (regression tests pass)
* [x] Logout verified
* [x] Race conditions reviewed (stale expiry after logout is a no-op; the
      expiry handler is guarded by current status; restore/login are the
      only writers of authenticated state)
* [x] Student email / register-number / university-roll-number login verified
      (all produce role `student` from /auth/me — identifier routing is
      login-time only and never affects role resolution)
* [x] Backend authentication, RBAC, and security tests pass
* [x] Frontend tests pass
* [x] Build passes (no TypeScript errors, no `any` introduced)
* [x] Documentation created
* [x] Git scope reviewed
* [x] No unrelated changes introduced
