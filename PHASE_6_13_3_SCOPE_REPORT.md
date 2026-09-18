# Phase 6.13.3 — Institution Registration / Join Request — Scope Report

**Date**: 2026-09-17
**Phase**: 6.13.3 — Institution Registration / Join Request
**Status**: **IMPLEMENTED** — endpoint wired, tests complete; full backend regression green.

---

## 1. Executive Summary

Phase 6.13.3 adds a public, unauthenticated institution registration API that
requests to join an EXISTING organization, reusing the Phase 6.13.1 tenancy
foundation, the Phase 6.3 Supabase Auth integration, and the Phase 6.13
scope/RBAC model unchanged.

**No new tables, no new migration, no new auth system, no new role.** The
Phase 6.13.1 tenancy service (`app.services.tenancy.register_institution`)
already implemented the full orchestration; as with Phase 6.13.2, the only gap
was API wiring, which this phase adds.

Flow implemented:

```
POST /api/v1/institutions/register
  -> validate (InstitutionRegistrationRequest, extra="forbid")
  -> resolve organization by PUBLIC code (case-insensitive; must be ACTIVE)
  -> verify organization-issued join code when present (constant-time)
  -> uniqueness pre-checks (institution code, admin email)
  -> Supabase Auth account (existing GoTrue signup — password ONLY to GoTrue)
  -> public.users link row
  -> institutions row (status='pending', is_active=False trigger-derived)
  -> user_roles row (role 'admin', scope institution/inst_id/org_id)
  -> institution_join_requests row (status='pending')
  -> 201 InstitutionRegistrationResponse (no password, no token)
```

The approval / activation workflow (organization admin deciding the join
request) is explicitly **Phase 6.13.4** — not implemented here.

## 2. Files Changed

| File | Change |
|------|--------|
| `backend/app/api/institutions.py` | **NEW** — `POST /institutions/register` endpoint (thin delegation to the existing service, project convention) |
| `backend/app/main.py` | Router wired into the app under `/api/v1` (import + `include_router`) |
| `backend/tests/test_institution_registration_phase_6_13_3.py` | **NEW** — 48 focused tests (see §9) |
| `PHASE_6_13_3_SCOPE_REPORT.md` | **NEW** — this document |

**Not changed** (reused as-is, per phase instructions): the tenancy service
(`register_institution`), tenancy repository, schemas, RBAC/authorization,
student-registration compensation primitives, and the Phase 6.13.1 migration.

### Migration created

**None.** No schema change was required: `institutions` already carries
`organization_id`, `status`, `is_active` (trigger-derived), the global unique
`institutions_code_key` constraint, and the `institution_join_requests` /
`user_roles` scope infrastructure exist from Phase 6.13.1.

---

## 3. API Endpoint

```
POST /api/v1/institutions/register        (public, no authentication)
```

Request (existing schema naming; `extra="forbid"` so any extra field — e.g.
`organization_id`, `role`, `scope_type`, `scope_id`, `status`, `is_active` —
is rejected with 422 `VALIDATION_ERROR` before the service runs):

```
name              str    (required, non-blank)
institution_code  str    (2..64, normalized trim+UPPER)
organization_code str    (2..64, normalized trim+UPPER, case-safe)
join_code         str?   (optional; required when the org issued one)
official_email    str    (required, valid email)
location          str?   (optional)
admin_email       str    (required, valid email)
admin_password    str    (required, min 6 chars)
admin_first_name  str    (required, non-blank)
admin_last_name   str    (required, non-blank)
```

> Note: the phase prompt suggested `institution_name` / `contact_information`,
> but the existing model/schema uses `name` and `location` — the existing
> naming was kept, per "do not force fields that don't exist in the current
> model".

Response (201): `message, institution_id, institution_code, organization_id,
status='pending', admin_user_id, email`. Never returns the password or a token.

Standard error format (`{"error": {"code", "message", ...}}`):

| Condition | HTTP | Code |
|-----------|------|------|
| Missing/invalid/extra fields, bad email, short password | 422 | `VALIDATION_ERROR` |
| Organization code not found | 404 | `ORGANIZATION_NOT_FOUND` |
| Organization not `active` | 403 | `ORGANIZATION_NOT_ACCEPTING_REQUESTS` |
| Join code wrong / missing when required | 403 | `INVALID_JOIN_CODE` |
| Institution code taken | 409 | `INSTITUTION_CODE_TAKEN` |
| Admin email already registered (pre-check or GoTrue race) | 409 | `EMAIL_ALREADY_REGISTERED` |
| Non-AppError DB failure after compensation | 500 | `REGISTRATION_FAILED` |

---

## 4. Organization Resolution

* Resolved SERVER-SIDE via `tenancy_repo.get_organization_by_code`
  (case-insensitive `ilike` on the public code; the payload has no
  organization-id field at all, so the resolved id cannot be overridden).
* The organization must exist (404 otherwise) and must be `active` — a pending
  organization does not accept institution requests (403).
* When the organization has issued a join code, the request must present it;
  comparison is constant-time and exact after whitespace-strip (case must
  match — the code is server-issued uppercase).
* The client cannot create a new organization, join a different organization,
  or override the resolved id.

## 5. Institution Pending / Join-Request Behavior

* The institution row is inserted with `status='pending'` and
  `is_active=False` (the Phase 6.13 trigger derives `is_active` from `status`
  on every write, so the pending institution is structurally unavailable).
* A pending `institution_join_requests` row is recorded (organization,
  institution, requested code, requesting user) — the existing Phase 6.13.1
  join-request entity is reused; no duplicate approval system was created.
* Nothing becomes active automatically. Approval (`decide_join_request` →
  institution activation) is the existing Phase 6.13.4 flow, untouched.

## 6. Admin / Auth Behavior

* The submitting user becomes the initial INSTITUTION ADMIN via the existing
  mechanisms: one GoTrue signup (password goes ONLY to Supabase Auth), one
  `public.users` link row, and a server-side `user_roles` grant of the
  existing `admin` role with `scope_type='institution'`,
  `scope_id=<institution_id>`, `scope_organization_id=<organization_id>`.
* The role/scope are decided ONLY server-side — the payload cannot influence
  them (`extra="forbid"`), and the Phase 6.13 `user_roles` scope trigger makes
  a cross-organization grant structurally impossible.
* No plaintext password is ever stored, hashed, logged, or echoed by the
  application; no token is returned at registration.

## 7. Security / Tenant Isolation

* Pending-institution access fails closed: every authorization guard checks
  the institution `status`, which stays `pending` until approval, and the
  institution-activation guard (`_assert_institution_active`) rejects
  anything that is not `active` + `is_active` — so staff/faculty/student
  onboarding against the pending institution is impossible.
* The admin's grant is institution-scoped only — never organization-wide,
  never platform.
* The institution is tenant-bound to the server-resolved
  `organizations.organization_id`; `Organization A + X` / `Organization B + X`
  is additionally impossible because the existing schema enforces GLOBAL
  institution-code uniqueness (`institutions_code_key UNIQUE (code)`) — the
  service enforces it via the existing global `institution_code_exists`
  pre-check plus the DB constraint (race-safe: a concurrent duplicate insert
  would hit the constraint and roll back via compensation).

## 8. Failure Safety

Orchestration reuses the locked Phase 6.3 / 6.13.2 compensation boundary
unchanged (`_create_auth_account` / `_create_public_user` /
`_try_delete_auth_user` / `_try_delete_user_row`):

| Failure point | Compensation |
|---------------|--------------|
| GoTrue signup fails (duplicate email) | nothing created |
| `public.users` insert fails | auth account deleted |
| `institutions` insert fails | users row + auth account deleted |
| `user_roles` grant fails | users row + auth account deleted |
| `institution_join_requests` insert fails | users row + auth account deleted |

(As in Phase 6.13.2, the first DB record — here the pending institution row —
intentionally lingers when a LATER step fails; its cleanup relies on the
unique code constraint / admin tooling, and no second insert attempt is made.)

## 9. Tests

`backend/tests/test_institution_registration_phase_6_13_3.py` — 48 tests
(mocked GoTrue + service-role PostgREST clients, following the Phase 6.13.2
test conventions; no live services contacted):

1. successful institution registration request (201, pending) ✅
2. existing organization resolution (server-side binding to resolved id) ✅
3. nonexistent organization (404, nothing created, no auth signup attempted) ✅
4. case-insensitive organization code (mixed-case + whitespace variants) ✅
5. institution creation in pending state (status='pending', is_active=False) ✅
6. initial institution admin (1 GoTrue signup + 1 public.users row) ✅
7. institution-scoped access NOT usable before approval (pending fails
   closed via the existing activation guard; institution scope only) ✅
8. duplicate institution code (case-insensitive, nothing created) ✅
9. duplicate institution within the same organization (+ global-unique
   across organizations, per the existing schema constraint) ✅
10. duplicate admin email (pre-check, case-insensitive, GoTrue race) ✅
11. invalid admin email / official email ✅
12. invalid password (short, empty) ✅
13. missing required fields (parametrized over all 8) + blank text fields ✅
14. password not returned / never stored in application tables (GoTrue only) ✅
15. partial failure cleanup (auth, users, institution, role, join-request
    failure injections → compensation, no orphan users/auth accounts) ✅
16. organization/institution tenant isolation (scope shape; resolved org
    cannot be overridden; role/scope/status injection rejected) ✅
17. Phase 6.13.1 / 6.13.2 regression (endpoints present, repo helpers,
    authorization constants untouched) ✅

### Exact results

```
Targeted:  python -m pytest tests/test_institution_registration_phase_6_13_3.py -q
           48 passed, 2 warnings in 3.80s

Regression (6.13.1 + 6.13.2):
           python -m pytest tests/test_organization_institution_phase_6_13_1.py
                            tests/test_organization_registration_phase_6_13_2.py -q
           78 passed, 4 skipped, 2 warnings in 4.15s

Full:      python -m pytest tests -q
           1117 passed, 15 skipped, 7 warnings in 19.21s
           (baseline before this phase: 1069 passed, 15 skipped —
            48 new tests, 0 regressions)
```

The 15 skipped are the pre-existing opt-in live-database validation classes
(Phase 4.4 / 6.13.1 convention), unchanged.

---

## 10. Remaining Limitations

1. **Approval workflow is not part of this phase** — the pending join request
   and pending institution await the existing `decide_join_request` service
   (Phase 6.13.4 exposes/enforces it for organization admins; not touched here).
2. **Email verification**: relies on Supabase Auth's configured
   email-confirmation behaviour; no application-side verification e-mail is
   sent (same as the existing organization / student signups).
3. **No rate limiting / captcha** on the public endpoint (consistent with the
   existing public registration endpoints).
4. **Compensation is best-effort** (GoTrue is outside the PostgREST
   transaction) — a crash between compensation steps can in rare cases leave
   an auth account without a public profile, exactly as documented in the
   locked Phase 6.3 design. A pending institution row may linger if a later
   step (role grant / join-request insert) fails — same boundary as
   Phase 6.13.2 organization rows.
5. **Join-code case sensitivity**: the join code is server-issued and compared
   exactly (constant-time) — case must match; only surrounding whitespace is
   stripped. This is existing Phase 6.13.1 behaviour, unchanged.
6. **Institution codes are globally unique** (existing `institutions_code_key
   UNIQUE` constraint), so the same institution code cannot exist under two
   organizations. If per-organization code scoping is ever desired, that
   requires a schema change (out of this phase's scope).

---

## 11. Definition of Done Verification

| Requirement | Status |
|-------------|--------|
| Institution registration API works | YES — 201 happy path, full validation contract |
| Institution associated with the correct existing organization | YES — server-resolved org id; cannot be overridden |
| Registration starts in pending state | YES — institution `pending`/`is_active=False` + pending join request |
| Initial admin handled securely | YES — GoTrue account + public.users + server-side institution-scoped grant |
| No unauthorized institution access before approval | YES — pending status fails closed (activation guard + guards on status) |
| Duplicate/race conditions handled | YES — pre-checks + DB unique constraint + GoTrue race → 409s |
| Tenant isolation preserved | YES — institution bound to resolved org; scope trigger-enforced |
| Passwords secure | YES — GoTrue only; never stored/logged/echoed |
| Targeted tests pass | YES — 48 passed |
| Full backend regression passes | YES — 1117 passed, 15 skipped, 0 failed |
| Phase 6.13.1 / 6.13.2 remain green | YES — 78 passed, 4 skipped |
| Scope report complete | YES — this document |

---

**End of Report**


