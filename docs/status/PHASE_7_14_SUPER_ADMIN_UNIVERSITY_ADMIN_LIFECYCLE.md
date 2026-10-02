# Phase 7.14 — Super Admin University Admin Lifecycle

**Status:** COMPLETE
**Date:** 2026-10-01
**Scope:** `Super Admin → Institution → University Admin → Staff / Faculty / Students`

---

## 1. Objective

Phase 7.13 gave the Super Admin controlled assignment of an **already-existing**
account as a University Admin. That deliberately stopped short of provisioning:
it could not create a University Admin, revoke one, or show who held the role.

Phase 7.14 completes the SaaS hierarchy with a full, audited lifecycle:

```text
Super Admin
    ↓
Institution
    ↓
University Admin          ← invited, accepted, rostered, revocable
    ↓
Staff / Faculty / Students
```

Delivered: audited invitations, secure acceptance, an admin roster, revocation,
cancellation, expiry, one-time consumption, and a read-only platform audit view.

**What was NOT redesigned.** The Phase 7.12 authorization model, the Phase 7.13
institution APIs, and the existing RBAC primitives are all reused unchanged.

---

## 2. Existing architecture reused

| Existing system | How Phase 7.14 reuses it |
| --- | --- |
| `require_super_admin` (7.12) | **Unchanged.** Every platform route below binds the same dependency. |
| Platform role model (7.12) | `super_admin` remains platform-scoped-only; never granted by invitation. |
| Platform audit infra (7.12/7.13) | `platform_institution_audit_log` extended additively; no new ledger. |
| `public.institutions` (6.13 / 7.13) | The invitation's tenant FK. No new tenant table. |
| `assign_user_role_scope` (6.13) | The ONLY primitive used to grant the admin role. |
| `public.users`, `user_roles`, `roles` | Unchanged; the invitation writes into them, never beside them. |
| Supabase Auth / `_create_auth_account` | The single credential authority for acceptance. |
| `/auth/me`, login flows, RBAC | Untouched; the accepted admin resolves through them normally. |

**No duplicate tables were created.** There is no second user table, role table,
institution table, tenant table, or authentication system.
---

## 3. Invitation model

```text
Super Admin
    ↓  POST /api/v1/platform/institutions/{id}/admins/invitations  { "email": "..." }
platform_admin_invitations row  (status=invited, role_name='admin', expires_at=now+24h)
    ↓  raw token returned ONCE, stored only as SHA-256
Invitation URL  /admin-invite/{token}
    ↓  invited person opens it
GET /api/v1/admin-invitations/{token}          → institution name + expiry only
    ↓  chooses their OWN password
POST /api/v1/admin-invitations/{token}/accept { "password": "..." }
    ↓  server resolves: token → invitation → institution → role
Supabase Auth account + public.users row + institution-scoped `admin`
    ↓
Ordinary admin login → institution-scoped admin authorization
```

The invitation row is the **single source of truth** for `institution → role`.
Acceptance resolves that chain entirely server-side; the request body is never
consulted for authorization.

---

## 4. Token security

| Property | Implementation |
| --- | --- |
| **Generation** | `secrets.token_urlsafe(48)` — 384 bits of OS CSPRNG entropy, 64 URL-safe chars. |
| **Storage** | SHA-256 hex digest only (`token_hash`, `UNIQUE`, `CHECK ~ '^[0-9a-f]{64}$'`). |
| **Raw token** | Returned exactly once in the create response; never persisted, never re-servable. |
| **Expiry** | Server constant `INVITATION_TTL_HOURS = 24`. Enforced **inside** the atomic claim statement (`expires_at > now()`), so it cannot be raced. |
| **Single use** | One conditional `UPDATE … WHERE status='invited' AND expires_at > now()`. Concurrent requests: exactly one winner. |
| **Terminal states** | DB trigger rejects any transition out of `accepted` / `cancelled` / `expired`. Replay is structurally impossible. |
| **Logging** | The raw token never reaches the audit `details` (only email + expiry), never a log line, never an error message. |
| **Disclosure** | `token_hash` has **no field in any response schema** — leaking a digest is structurally impossible, not merely avoided. |

---

## 5. Invitation lifecycle

```text
INVITED ──accept──► ACCEPTED ──revoke──► (role removed; account preserved)
    │
    ├──cancel──► CANCELLED
    └──expiry──► EXPIRED
```

* **Duplicate invitations** are refused (409 `INVITATION_ALREADY_PENDING`), so a
  mis-click never leaves two live links for one person.
* **Cancelling transitions, never deletes** — the audit record and the invitation
  row are both retained.
* **Expiry is persisted** when observed, so the roster reflects reality instead of
  a permanently "invited" row.
* **Already-accepted accounts** are refused with a pointer to the Phase 7.13
  assignment endpoint, which remains the supported path for existing accounts.

---

## 6. Authentication integration

The accepted admin becomes authenticated exactly like any other account. No second
authentication mechanism was introduced.

1. The invited person supplies **their own** password on the acceptance page.
2. It is forwarded to Supabase Auth (GoTrue) through the existing
   `student_registration._create_auth_account` primitive.
3. A `public.users` link row is created through the existing `_create_public_user`.
4. The institution-scoped `admin` role is granted through the existing
   `assign_user_role_scope`.
5. The person signs in at `/login/admin`.

The resulting role resolves through the **unchanged** chain:

```text
JWT → get_current_user → get_user_by_auth_id → user_roles → roles → institution → resolve_primary_role
```

**Password handling.** No password is ever accepted on the platform-management
API. On acceptance it is never stored in this application's database, never
compared, never logged, never audited, and never returned. Failures use the
established Phase 6.3 compensation pattern (`_try_delete_user_row`,
`_try_delete_auth_user`), so a failed acceptance leaves no orphaned identity.
---

## 7. Admin roster

`GET /api/v1/platform/institutions/{id}/admins/roster` merges two sources:

* **accepted admins** — derived from the EXACT `(admin, institution, this id)`
  grant tuple, so a Super Admin or another institution's admin can never appear;
* **invitations** — every non-accepted invitation with its real status.

Exposed fields: email, lifecycle status, opaque ids, expiry. Nothing else exists
in the response model.

---

## 8. Revocation

`POST /api/v1/platform/institutions/{id}/admins/{user_id}/revoke`

Safety chain, verified in this order **before** any mutation:

```text
target user → institution → admin role → institution scope
```

* the institution must exist;
* the user must hold the exact `(admin, institution, this id)` grant;
* an account that **also** holds a platform `super_admin` grant is refused
  outright (409 `PLATFORM_ROLE_PRESERVED`).

Only that single `user_roles` row is deleted — the `DELETE` re-asserts user, role,
scope type and scope id rather than trusting a fetched row. The Auth account, the
`public.users` row and every other role are preserved. Because all tenant
authorization re-reads `user_roles` per request, revocation takes effect on the
revoked admin's very next request.

---

## 9. Cancellation

`POST /api/v1/platform/institutions/{id}/admins/invitations/{invitation_id}/cancel`

The institution binding is verified before mutation (a cross-tenant cancel is a
clean 404), the update is conditional on `status='invited'`, and the invitation row
is retained for the audit trail.

---

## 10. Audit events

| Action | Recorded when |
| --- | --- |
| `institution_admin_invited` | A Super Admin issues an invitation. |
| `institution_admin_invitation_accepted` | An invitation is consumed and the admin created. |
| `institution_admin_invitation_expired` | An expired invitation is observed. |
| `institution_admin_invitation_cancelled` | A pending invitation is cancelled. |
| `institution_admin_revoked` | An institution admin grant is removed (or already absent). |

Each record carries **actor, action, target, institution, timestamp and result**.
`details` is a bounded, non-sensitive summary (email, expiry, changed role). The
Phase 7.13 vocabulary is preserved; the CHECK constraint was dropped and recreated
additively so no historical row is rewritten.

**Never stored:** raw tokens, token hashes, passwords, service-role keys.

---

## 11. Audit API and UI

```text
GET /api/v1/platform/audit?institution_id=&action=&date_from=&date_to=&limit=&offset=
```

Read-only by construction — the test suite asserts no audit route anywhere in the
API uses POST/PATCH/PUT/DELETE. Page size is bounded server-side (max 200).

Access matrix, verified by test:

```text
anonymous → 401
student / faculty / staff / admin → 403
super_admin → 200
```

The **Platform Audit** section in the Super Admin shell is a timeline listing
timestamp, actor email, action and institution, with an action filter and paging.
It exposes no mutation control. Multiple Super Admins are fully supported: every
record identifies which authenticated platform operator acted.
---

## 12. Tenant isolation

* An invitation is bound to **exactly one** institution by a non-nullable FK, and
  the role is pinned to `'admin'` by a database CHECK.
* The acceptance client cannot supply `role`, `institution_id`, `scope` or
  `permissions` — `extra="forbid"` rejects them with 422.
* Cross-tenant operations fail: an Institution A admin receives 403 on
  Institution B's roster, invitations and revocation (tested).
* The institution is resolved **from the invitation row**, never from the URL.

---

## 13. Security controls

* **No service-role key in the browser** — asserted by a test that scans all
  frontend sources for `service_role`, `supabase_secret` and JWT prefixes.
* **No password through platform management** — the invite payload is `{email}`.
* **No role escalation** — an invited admin can never become `super_admin`.
* **No frontend authorization bypass** — hiding buttons is UX only; every endpoint
  independently enforces `require_super_admin`.
* **No token disclosure** — no `token_hash` field exists in any response schema.
* **Safe errors** — invalid / expired / cancelled / already-used / inactive /
  revoked all return fixed messages with no table names, SQL or driver text.
* **Service-role-only tables** — the invitation table is revoked from
  `PUBLIC`/`anon`/`authenticated`; the audit ledger has no UPDATE/DELETE grant.

---

## 14. Database migration

**File:** `supabase/migrations/20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql`
**Ledger position:** 19 of 19 (after 18 prior; verified with `supabase migration list --local`).

New table `platform_admin_invitations`:

| Constraint | Purpose |
| --- | --- |
| `token_hash` UNIQUE | Token digest uniqueness |
| `status_check` | `invited \| accepted \| cancelled \| expired` |
| `role_name_check` | Pinned to `'admin'` |
| `email_check` | Non-empty, lowercase, ≤320 chars |
| `token_hash_check` | 64-char lowercase SHA-256 hex |
| `expiry_check` | `expires_at > created_at` |
| `terminal_state_check` | Accepted/cancelled timestamps mutually exclusive |

Foreign keys: `institution_id → institutions`, `created_by → users`,
`accepted_user_id → users`, all `ON DELETE RESTRICT`.

Trigger `trg_phase714_invitation_transition` rejects any transition out of a
terminal state and forbids re-pointing an invitation's institution, role, token,
email, creator or expiry.

Indexes: `(institution_id, status)`, `(status, expires_at)`, `(email)`, plus the
token UNIQUE constraint's own index and two audit indexes. A separate index on
`token_hash` was deliberately **not** created — the UNIQUE constraint already
provides it, and a duplicate would be pure write amplification (asserted by test).

**Verification:** migration applied, fresh reset #1 ✅, fresh reset #2 ✅, ledger
valid, schema confirmed with `\d` against the live local database.

---

## 15. Test results

| Suite | Result |
| --- | --- |
| Focused backend (`test_phase_7_14_...`) | **55 passed** |
| Full backend (`pytest tests`) | **2285 passed, 15 skipped, 0 failed** |
| Frontend (`npm test`) | **496 passed / 58 files, 0 failed** |
| TypeScript (`tsc -b`) | ✅ |
| Build (`vite build`) | ✅ |
| Fresh reset #1 / #2 | ✅ / ✅ |
| Migration ledger | ✅ 19 of 19, no drift |

**One pre-existing test timeout was corrected.** `src/config/env.test.ts`
synchronously walks the entire `src/` tree; its runtime grows with the frontend
and the default 5 s vitest budget was already marginal. Adding Phase 7.14 files
tipped it over under parallel-suite CPU contention. The assertions are
**unchanged** — only the timeout allowed for that intentionally I/O-bound scan
was made explicit (30 s). The test passes both before and after this change when
run in isolation, confirming no assertion regression.

The Phase 7.13 mock in `InstitutionManagement.test.tsx` was extended with the
four new Phase 7.14 API functions, since a partial `vi.mock` factory would
otherwise leave the roster unmocked.

## 16. Known limitations

1. **Invitation links are returned in the API response and shown once.** In a
   production deployment this should be emailed by a delivery service; no mail
   sending was introduced in this phase.
2. **No scheduled expiry sweep.** Expiry is evaluated lazily at read/claim time
   and persisted when observed. A cron-based sweep would tidy long-idle rows.
3. **No invitation resend.** A lost link requires cancel + reissue.
4. **Email is not verified.** The invited person receives the link; possession of
   the link is the authorization. Adding email verification is a follow-up.
5. **Audit page size capped at 200** per request; very large ledgers would want
   cursor pagination.
6. **Rate limiting is not applied to the public invitation endpoints.** The token
   is 384 bits of entropy so guessing is infeasible, but a dedicated limiter would
   harden the surface further.

---

## 17. Remote safety

Every command ran against the **local** Supabase stack only, via the existing
guarded `scripts/validation/invoke_local_supabase.ps1` wrapper, which verifies the
loopback endpoint and refuses any non-local target.

```text
Remote database modified: NO
Remote migrations applied: NO
Remote Auth modified: NO
Remote users modified: NO
Remote institution data modified: NO
Remote audit data modified: NO
Production deployment: NO
DNS modified: NO
```

`supabase db push --linked` was never executed. No credential was printed.

---

## 18. Next phase

Recommended: **Phase 7.15 — Invitation delivery and email verification.**

Building directly on what exists here:

1. Deliver the invitation link by email instead of returning it only in the API
   response, so the link never transits an operator's screen.
2. Add email verification on acceptance so possession of the link is not the only
   binding.
3. Add a rate limiter and a scheduled expiry sweep to the invitation endpoints.
4. Add admin-to-admin delegation (an institution admin inviting peer admins) once
   the platform roster and audit model have proven themselves in use.