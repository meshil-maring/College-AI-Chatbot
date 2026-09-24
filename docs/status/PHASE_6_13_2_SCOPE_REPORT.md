# Phase 6.13.2 — Organization Registration — Scope Report

**Date**: 2026-09-17
**Phase**: 6.13.2 — Organization Registration
**Status**: **IMPLEMENTED** — endpoint, service wiring, and tests complete; full backend regression green.

---

## 1. Executive Summary

Phase 6.13.2 adds a public, unauthenticated organization registration API that
creates an organization and its initial **Organization Admin**, reusing the
existing Phase 6.13.1 tenancy foundation, the existing Phase 6.3 Supabase
Auth integration, and the existing Phase 6.13 scope/RBAC model.

**No new tables, no new migration, no new auth system, no new role** were
created. The role is the existing `admin` role; the scope is the existing
`scope_type='organization'` / `scope_id=organizations.organization_id`
vocabulary on the existing `user_roles` table.

Flow implemented:

```
POST /api/v1/organizations/register
  -> validate (schema, extra="forbid")
  -> uniqueness pre-checks (org code case-insensitive, admin email)
  -> Supabase Auth account (existing GoTrue signup — password ONLY to GoTrue)
  -> public.users link row
  -> organizations row (status='pending', server-issued 12-char join_code)
  -> user_roles row (role 'admin', scope organization/org_id/org_id)
  -> 201 OrganizationResponse (no password, no token, no join_code echo)
```

### Out-of-scope work done for repo health (documented, not phase scope)

* Restored `backend/app/services/public_chat.py` to the committed (HEAD)
  version. The working tree contained a docstring-only stub (590 bytes vs the
  471-line committed file) left by earlier unfinished work; it broke 3
  Phase 6.13.1 public-chat regression tests. No public-chat behaviour was
  redesigned — the committed implementation was restored unchanged.

---

## 2. Files Changed

| File | Change |
|------|--------|
| `backend/app/api/organizations.py` | **NEW** — `POST /organizations/register` endpoint (thin delegation to the service, project convention) |
| `backend/app/main.py` | Router wired into the app under `/api/v1`; added a `RequestValidationError` handler normalizing schema failures to `{"error": {"code": "VALIDATION_ERROR", ...}}` with HTTP 422 (matches the AppError contract; pydantic error details sanitized to JSON-safe `loc`/`msg`/`type`) |
| `backend/tests/test_organization_registration_phase_6_13_2.py` | **NEW** — 34 focused tests (see §6) |
| `backend/app/services/public_chat.py` | **Restored to HEAD** (pre-existing working-tree stub broke Phase 6.13.1 regression; see §1) |

**Not changed** (reused as-is, per phase instructions): the tenancy service
(`register_organization` already implemented the orchestration), tenancy
repository, schemas, RBAC/authorization, student registration compensation
primitives, and the migration. The only service-side gap found was API wiring
(no router exposed `register_organization`), which this phase adds.

### Migration created

**None.** No schema change was required: `organizations` (with the
case-insensitive unique `lower(organization_code)` index), the `user_roles`
scope columns, and the integrity triggers already exist from Phase 6.13.1.

---

## 3. API Endpoint

```
POST /api/v1/organizations/register        (public, no authentication)
```

Request (all fields required; `extra="forbid"` so any extra field — e.g.
`role`, `scope_type`, `scope_id`, `status` — is rejected with 422 before the
service runs):

```
name                  str   (non-blank)
organization_code     str   (2..64, normalized trim+UPPER, case-safe)
official_email        EmailStr
contact_information   str   (non-blank)
admin_email           EmailStr
admin_password        str   (min 6 chars — existing project password rule)
admin_first_name      str   (non-blank)
admin_last_name       str   (non-blank)
```

Response `201`:

```
message, organization_id (uuid), organization_code, status ("pending"),
admin_user_id (uuid), email
```

Note on field naming: the request uses `admin_first_name` / `admin_last_name`
rather than a single `admin_full_name` because the existing `public.users`
model (`first_name` / `last_name`) and the existing schema contract already
store names split; the split fields map 1:1 onto the existing user row.

Error contract (all via the project's `{"error": {"code", "message"}}` shape):

| Situation | Status | Code |
|-----------|--------|------|
| Missing / invalid / extra field (incl. role/scope/status injection) | 422 | `VALIDATION_ERROR` |
| Duplicate organization code (case-insensitive) | 409 | `ORGANIZATION_CODE_TAKEN` |
| Duplicate admin email (public.users row or GoTrue `email_exists`) | 409 | `EMAIL_ALREADY_REGISTERED` |
| Any DB write failure after compensation | 500 | `REGISTRATION_FAILED` |

---

## 4. Registration Flow & Failure Safety

Orchestration lives in the existing `app.services.tenancy.register_organization`
(reused unchanged). Check order and compensation:

1. **Schema validation** (422 before any I/O).
2. `organization_code_exists` (case-insensitive via `ilike`, backed by the
   `uq_organizations_code_lower` unique index) → 409 `ORGANIZATION_CODE_TAKEN`.
   The DB unique index makes the check race-safe; two concurrent registrations
   with the same code cannot both succeed.
3. `get_user_by_email` → 409 `EMAIL_ALREADY_REGISTERED` (a user can never
   self-register into an existing organization as its admin — the admin is
   created fresh, server-side, bound only to the newly created organization).
4. Server issues the institution **join code** (`secrets.token_hex(6).upper()`,
   12 chars) — never client-chosen.
5. `_create_auth_account` (existing Phase 6.3 GoTrue signup; password goes
   ONLY to Supabase Auth; duplicate auth email → 409).
6. Inside one try block:
   `_create_public_user` → `insert_organization` (status `pending`) →
   `_grant_role(role='admin', scope_type='organization', scope_id=org_id,
   scope_organization_id=org_id)` via the existing
   `assign_user_role_scope` (idempotent on `(user_id, role_id)`, validated by
   the Phase 6.13 `user_roles` scope trigger).
7. **Compensation** (locked Phase 6.3 best-effort primitives):
   * users insert fails → auth account deleted (`auth.admin.delete_user`)
   * organizations insert fails → users row deleted + auth account deleted
   * role grant fails → users row deleted + auth account deleted
   * AppError re-raised as-is; other exceptions wrapped as 500
     `REGISTRATION_FAILED` (no internal details leaked).

Partial-failure residuals are therefore limited to the GoTrue/PostgREST
best-effort boundary already accepted by the Phase 6.3/6.13.1 architecture.
No institution is created automatically.

---

## 5. Authentication Integration & Role/Scope Behavior

* **Single auth system**: Supabase Auth (GoTrue) via the existing
  `student_registration._create_auth_account`. No second auth architecture.
* **Passwords**: never stored, hashed, logged, or echoed by the application;
  they go only to GoTrue. The password also never appears in the response, in
  the users insert payload, or in error messages.
* **Role/scope**: the created user receives the existing `admin` role with
  `scope_type='organization'`, `scope_id=organization.organization_id`,
  `scope_organization_id=organization.organization_id` — assigned strictly
  server-side. No `organization_admin` role was introduced.
* **Client control**: the schema's `extra="forbid"` makes role / scope /
  status injection unrepresentable (422 before the service runs).
* **Isolation**: the organization starts `pending`; institution joins and
  approvals remain Phase 6.13.3+ and the existing
  `resolve_authorization_context` / `assert_can_manage_organization` guards
  are untouched, so tenant isolation and existing RBAC are not weakened.

---

## 6. Tests

New file: `backend/tests/test_organization_registration_phase_6_13_2.py`
(mocked Supabase clients; no live DB/auth). Coverage per the phase checklist:

1. successful registration (201, `pending`) ✅
2. organization creation (row contents, code normalization, server-issued 12-char join_code) ✅
3. initial admin creation (GoTrue signup once + one public.users row) ✅
4. admin role assignment (`role_id` of existing `admin` role) ✅
5. organization scope assignment (`scope_type`/`scope_id`/`scope_organization_id`) ✅
6. duplicate organization code (case-insensitive + same case) ✅
7. duplicate admin email (+ precedence when code and email both taken) ✅
8. invalid admin email / official email ✅
9. invalid (short, empty) password ✅
10. missing required fields (parametrized over all 8 fields) + blank name/code ✅
11. password not exposed in response ✅
12. password never stored in application tables (goes only to GoTrue) ✅
13. partial failure/cleanup (auth, users, org, role-grant failures → compensation, no orphans) ✅
14. existing tenancy/RBAC regression (student route, repo helpers, authorization constants) ✅
+ role/scope/status injection rejected; no institution auto-created ✅

### Exact results

```
Targeted:  python -m pytest tests/test_organization_registration_phase_6_13_2.py -q
           34 passed, 2 warnings in 4.58s

Full:      python -m pytest tests -q
           1069 passed, 15 skipped, 7 warnings in 23.07s
           (baseline before this phase: 1035 passed, 15 skipped —
            34 new tests, 0 regressions)
```

The 15 skipped are the pre-existing opt-in live-database validation classes
(Phase 4.4 / 6.13.1 convention), unchanged.

---

## 7. Remaining Limitations

1. **Organization approval workflow is not part of this phase** — new
   organizations stay `pending`; platform-admin activation is a later
   sub-phase (the existing `decide_organization` service already exists).
2. **Institution / student / staff-faculty registration** are explicitly out
   of scope (Phase 6.13.3+); no institution is created automatically.
3. **Email verification**: the flow relies on Supabase Auth's configured
   email-confirmation behaviour; no application-side verification e-mail is
   sent (same as the existing student signup).
4. **No rate limiting / captcha** on the public endpoint (consistent with the
   existing public registration endpoints).
5. **Compensation is best-effort** (GoTrue is outside the PostgREST
   transaction) — a crash between compensation steps can in rare cases leave
   an auth account without a public profile, exactly as documented in the
   locked Phase 6.3 design.
6. **Phase 6.13.1 working-tree changes** (tenancy repo/authorization/migration
   fixes documented in `PHASE_6_13_1_SCOPE_REPORT.md`) remain uncommitted in
   the working tree; this phase did not alter them.

---

## 8. Definition of Done Verification

| Requirement | Status |
|-------------|--------|
| Organization registration API works | YES — 201 happy path, full validation contract |
| Organization created correctly | YES — pending status, unique case-safe code, server join code |
| Initial admin created correctly | YES — GoTrue account + public.users row |
| Admin receives organization-level scope | YES — `admin` / `organization` / org id (server-side) |
| Duplicate/race conditions handled | YES — pre-check + DB unique index + 409s |
| Passwords secure | YES — GoTrue only; never stored/logged/echoed |
| Partial failures handled safely | YES — Phase 6.3 compensation primitives; tested |
| Targeted tests pass | YES — 34 passed |
| Full backend regression passes | YES — 1069 passed, 15 skipped, 0 failed |
| Phase 6.13.1 functionality intact | YES — all 6.13.1 tests green (public_chat restored to HEAD) |
| Scope report complete | YES — this document |

---

**End of Report**
