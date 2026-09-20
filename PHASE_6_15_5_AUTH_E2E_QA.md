# PHASE 6.15.5 — AUTHENTICATION & REGISTRATION END-TO-END QA

**Status:** COMPLETE
**Date:** 2026-09-20
**Scope:** Validation, integration, regression, and security hardening of the
complete authentication + student registration system delivered by Phases
6.15.1–6.15.4. No architecture redesign; one security-hardening fix applied.

---

## 1. Objective

Perform end-to-end validation of the full lifecycle:

```text
Student Registration
        ↓
Institution Code Resolution
        ↓
Pending Approval
        ↓
Student Login (email / register number / university roll number)
        ↓
Canonical /auth/me
        ↓
Server-authoritative Role Resolution
        ↓
Correct Application Shell
        ↓
Session Expiry Handling
```

All verification below is backed by either an executed automated test, a
static contract inspection of the repository, or a build/test run — source of
truth is the current working tree (Phase 6.15.1–6.15.4 changes uncommitted).

---

## 2. System Under Test

### Frontend (inspected, verified)

| Component | File | Notes |
|---|---|---|
| AuthProvider | `frontend/src/features/auth/AuthProvider.tsx` | status/user/**role**/token state; `restore`, `login`, `logout`; subscribes to session-expiry bus; 401 on `/auth/me` restore → token discarded |
| LoginForm | `frontend/src/features/auth/LoginForm.tsx` | unified identifier field; conditional required institution code (non-email identifiers); busy guard blocks duplicate submits |
| RegistrationForm | `frontend/src/features/auth/RegistrationForm.tsx` | institution lookup before submit; client validation mirrors backend; pending-approval success state (never authenticated); **Phase 6.15.5 fix applied** |
| App.tsx | `frontend/src/App.tsx` | shell selection from `user.role` only; staff/faculty/student → StudentShell; admin → AdminShell; unknown role → safe restricted shell |
| AdminShell | `frontend/src/features/admin/AdminShell.tsx` | identity from AuthProvider state; **no `/admin/me` probe** |
| auth service | `frontend/src/services/auth.ts` | `/auth/login`, `/auth/student/login`, `/auth/me`; `authenticate()` routing; operation-context error classification |
| registration service | `frontend/src/services/registration.ts` | `lookupInstitution` (GET `/institutions/lookup?code=…`, encoded), `registerStudent` (POST `/users/register`); typed error kinds; timeout/network mapping |
| api clients | `frontend/src/services/api.ts`, `adminApi.ts` | publish `notifySessionExpired()` on any authenticated 401 |
| session events | `frontend/src/services/sessionEvents.ts` | dependency-free pub/sub; `SESSION_EXPIRED_MESSAGE` |
| types | `frontend/src/types/auth.ts`, `types/registration.ts` | exact backend mirrors (`AuthRole`, `CurrentUser.role/institution_id`, lookup/registration contracts) |

### Backend (inspected, verified)

| Area | File | Verified contract |
|---|---|---|
| `/auth/login` | `backend/app/api/auth.py` | Supabase Auth verify → server-side sign-in context → fail-closed status guard; every denial normalized to `400 INVALID_CREDENTIALS` (byte-identical to wrong password) |
| `/auth/student/login` | `backend/app/api/student_auth.py` + `services/student_auth.py` | unified identifier; academic identifiers REQUIRE `institution_code`; ALL failures (unknown identifier, wrong password, pending/rejected, inactive) → `401 INVALID_CREDENTIALS` |
| `/auth/me` | `backend/app/main.py` (`auth_me`) | canonical identity bootstrap: `authenticated, user_id, auth_user_id, email, role, institution_id` — role resolved SERVER-side via `resolve_primary_role` |
| `/users/register` | `backend/app/api/users.py` + `services/user_registration.py` | `registration_type` Literal (admin unrepresentable); server-side code resolution; student → `approval_status='pending'`; no token in response |
| institution lookup | `backend/app/api/institutions.py` + `services/tenancy.py::lookup_institution_by_code` | 200 `{institution_id, code, name}` / 404 / 422 / 403 codes per §4 below |
| token security | `backend/app/core/security.py` | ES256 JWT verify (JWKS), `aud=authenticated`, leeway; `TOKEN_EXPIRED`/`INVALID_TOKEN` → 401; missing/absent user → 404 `USER_NOT_FOUND` |
| RBAC | `backend/app/core/security.py::require_roles` | 401 unauthenticated / 403 `FORBIDDEN` for wrong role |
| tenant isolation | `security.py::scope_tenant/assert_tenant_object` | institution_id is the tenant key; cross-tenant access → 403 `TENANT_MISMATCH` |
| 422 normalization | `backend/app/main.py::validation_error_handler` | FastAPI 422s → `{"error":{"code":"VALIDATION_ERROR",…}}` (sanitized loc/msg/type) |
| schemas | `schemas/student_auth.py`, `users.py`, `tenancy.py` | `extra="forbid"` everywhere — role/institution/status injection is unrepresentable |

---

## 3. Registration Flow

Flow validated end-to-end (`RegistrationForm.test.tsx` — 24 tests, all pass):

```text
Registration page → institution code → resolved (name shown)
→ student information → submit → POST /users/register
→ 201, approval_status = 'pending' → "Registration Successful" screen
```

Verified:

- ✅ **No token is issued** — the registration response carries no token;
  the test asserts `college-ai-chatbot.access-token` absent from localStorage
  and both storages empty after registration.
- ✅ **Student is not authenticated / not redirected** — the success screen is
  a status state inside the form; AuthProvider state untouched; `App.tsx`
  still renders the login gate.
- ✅ Registration success state displayed (`role="status"` region +
  "Registration Successful" heading; test-verified).
- ✅ Account exists in backend with `approval_status='pending'`
  (`test_user_registration_phase_6_13_5.py`,
  `test_student_registration_phase_6_3.py`; the service writes
  `approval_status=tenancy_svc.PENDING`).

## 4. Institution Lookup

`GET /api/v1/institutions/lookup` (`test_institution_lookup_phase_6_15_2.py`,
all pass) + frontend `RegistrationForm` lookup UX tests:

| Scenario | Expected | Verified |
|---|---|---|
| Valid code | `200` + `{institution_id, code, name}` | ✅ backend test + UI "shows the institution name" |
| Invalid code | `404 INSTITUTION_NOT_FOUND` | ✅ backend + UI controlled message |
| Missing code | `422 VALIDATION_ERROR` (normalized envelope) | ✅ backend + main.py handler |
| Inactive institution | `403 INSTITUTION_NOT_ACCEPTING_REGISTRATIONS` | ✅ `_assert_institution_active` + test |

Response exposure audited: `InstitutionLookupResponse` is a deliberate
3-field projection. **No** student data, internal configuration, credentials,
join codes, organization linkage, status machinery, or other DB columns are
exposed (schema-level guarantee — `response_model` filters).

## 5. Student Login

All three identifiers via `POST /auth/student/login`
(`test_student_auth_phase_6_5.py`, `test_rbac_phase_6_6.py`,
`test_security_final_validation_phase_6_13_9.py` — all pass):

| Matrix row | Verified behavior |
|---|---|
| Email + valid credentials | 200 + access token (email needs no institution code) |
| Register number + code + valid credentials | 200 + access token |
| Roll number + code + valid credentials | 200 + access token |
| Invalid password (any identifier) | `401 INVALID_CREDENTIALS` — generic |
| Unknown identifier | `401 INVALID_CREDENTIALS` — indistinguishable from wrong password |
| Missing institution code (academic) | `422 VALIDATION_ERROR` (schema + `_validate_login_request`) |
| Wrong institution code | `401 INVALID_CREDENTIALS` — never "institution exists" |
| Correct institution code | resolves within tenant scope only |

**Anti-enumeration preserved:** every auth denial is the SAME safe 401 with
the same message; the frontend maps it to one generic string
("Invalid login credentials. Please check your details and try again.").
Account existence / approval state / lifecycle state are never disclosed.

Frontend identifier routing (`services/auth.ts::authenticate`) verified by
`auth.test.ts` (23 tests): email → `/auth/login` (code never sent); academic
identifier → `/auth/student/login` with `institution_code`;
`LoginForm.test.tsx` verifies the field is hidden for email and
shown+required otherwise.

## 6. Admin Login

```text
Admin credentials → POST /auth/login → token → GET /auth/me → role = admin
→ AdminShell
```

- ✅ `role='admin'` from `/auth/me` (`test_auth.py` — role resolution tests).
- ✅ AdminShell rendered from AuthProvider role (`App.test.tsx` gating tests).
- ✅ **No `/admin/me` probe** for shell selection — static verification: no
  `/admin/me` fetch exists in `App.tsx` / `AuthProvider.tsx` /
  `AdminShell.tsx` (only backend tests + validation scripts still use it).
- ✅ Existing admin APIs continue to work (`test_admin_api.py`,
  `test_role_scope_enforcement_phase_6_13_7.py` — all pass).

## 7. Staff Login

- ✅ `/auth/me` → `role='staff'` → `StudentShell` fallback (`App.test.tsx`
  role-mapping tests pass). No dedicated staff shell exists or was created.
- ✅ Backend authorization remains authoritative — staff cannot reach
  admin-only APIs (`test_rbac_phase_6_6.py` staff rows; 403 `FORBIDDEN`).

## 8. Faculty Login

- ✅ `/auth/me` → `role='faculty'` → `StudentShell` fallback (same tests).
  No dedicated faculty shell exists or was created.
- ✅ Faculty blocked from privileged APIs server-side (403).

## 9. Role Resolution

- Canonical: `GET /auth/me` → `resolve_primary_role(roles)` over the
  `JWT → public.users → user_roles → roles` chain, SERVER-side only.
- Precedence admin > staff > faculty > student (multi-role accounts keep
  existing admin behavior).
- Unknown/unsupported roles → `null` → frontend "Access restricted" shell
  (fail-safe, no privileged UI).
- Frontend NEVER derives role from email/identifier/localStorage/URL.

## 10. Session Lifecycle

```text
Login → token → /auth/me bootstrap → authenticated (role, user)
Refresh → restore() → saved token → /auth/me → same authenticated state
Logout → state + token cleared → login screen
Expiry → authenticated 401 → session_invalid event → cleared → login screen
```

### Page refresh (all roles) — `AuthProvider.test.tsx` + `App.test.tsx`

- Restore path is identical for every role: saved token → `/auth/me` →
  `user.role` → correct shell. Admin, staff, faculty, and student restore
  tests pass; during restore the "Restoring your session…" shell renders, so
  **no dashboard flash before authentication resolves**.
- An expired/rejected token on restore → `session_invalid` → token discarded
  → unauthenticated login screen (test-verified with `TOKEN_EXPIRED`).

### Logout (all roles)

- `logout()` clears user, role, token, and localStorage key; unauthenticated
  UI renders. Stale in-flight `notifySessionExpired()` after a deliberate
  logout is a guarded no-op (status check) — the expiry message is never
  shown for a manual sign-out (test-verified).
- Post-logout access attempts: every protected request would be sent without
  a token → backend 401 `AUTH_REQUIRED` (`test_rbac_phase_6_6.py`,
  `test_admin_api.py`); no authenticated UI is reachable client-side because
  `AuthGate` renders `LoginForm` for any non-authenticated status.

## 11. Session Expiry

Exact chain verified (`AuthProvider.test.tsx`, `api.test.ts`,
`adminApi.test.ts`):

```text
Authenticated API request → 401 (TOKEN_EXPIRED / INVALID_TOKEN /
USER_NOT_FOUND) → api client publishes notifySessionExpired()
→ AuthProvider clears user + accessToken + localStorage token
→ status = unauthenticated → login screen with EXACTLY:
"Your session has expired. Please log in again."
```

- The message is the fixed constant `SESSION_EXPIRED_MESSAGE` — raw backend
  errors are never surfaced.
- Both feature API clients (`api.ts` chat/conversations, `adminApi.ts` all
  admin/student requests) publish on 401 — no per-feature handling gaps.

## 12. Logout

Covered in §10. Additional storage audit: after logout
`window.localStorage` contains no token (AuthProvider `storeToken(null)`
removes the key — test-verified), no password is ever stored anywhere
(passwords exist only transiently in controlled React state / POST bodies).

## 13. Tenant Isolation

- Academic identifier login is institution-scoped BY CONTRACT: register
  number / roll number REQUIRE `institution_code`, and the lookup is filtered
  by the resolved institution (`services/student_auth.py::
  _resolve_academic_id_with_context`). An "Institution A code + Institution B
  academic identifier" combination resolves to nothing → `401
  INVALID_CREDENTIALS` (test: cross-institution identifier login fails).
- Authorization stays tenant-bounded after login: `scope_tenant` /
  `assert_tenant_object` reject cross-tenant ids with `403 TENANT_MISMATCH`
  (`test_tenant_isolation.py` — all pass; `test_rbac_phase_6_6.py`,
  `test_role_scope_enforcement_phase_6_13_7.py` tenant rows — all pass).
- Role resolution is per-account server-side; no client value can widen the
  tenant scope. No isolation rule was weakened for testing.

## 14. Security Verification

| Check | Result | Evidence |
|---|---|---|
| Anti-enumeration | ✅ | All student-auth denials → identical `401 INVALID_CREDENTIALS`; `/auth/login` denials → identical `400 INVALID_CREDENTIALS`; tests assert indistinguishability |
| Approval enforcement | ✅ | `pending`/`rejected` students blocked (`_assert_approved`; `test_student_approval_phase_6_4.py`, `test_student_auth_phase_6_5.py::test_api_login_rejected_student_returns_401`) |
| Role enforcement | ✅ | `require_roles` 403 `FORBIDDEN` (RBAC + role-scope suites) |
| Tenant isolation | ✅ | §13 suites |
| Token validation | ✅ | ES256 + JWKS + `aud=authenticated`; tampered/expired token → 401 (`TOKEN_EXPIRED`/`INVALID_TOKEN`) |
| No password logging | ✅ | Repo-wide logger grep: no `password`/`token` in any log statement; passwords forwarded ONLY to Supabase GoTrue |
| No token logging | ✅ | Token only in `Authorization: Bearer` headers; never rendered/logged by the UI or services |
| No sensitive response fields | ✅ | Lookup = 3-field projection; registration response has no password/token; `/auth/me` exposes id/email/role/institution only |
| Role injection | ✅ | `extra="forbid"` on every auth/registration schema; `registration_type` Literal excludes `admin`; role granted only server-side |
| Institution injection | ✅ | Client submits only the public CODE; server resolves the id (`_resolve_institution`); client `institution_id` is rejected (422) |
| Privilege escalation | ✅ | Registration never grants a role; approvals are server-side admin workflows; frontend tampering cannot escalate (§17) |

## 15. Browser/Network Verification

### Browser storage audit (static + test-verified)

| Point | Expected | Result |
|---|---|---|
| After registration | No authentication token | ✅ test: both storages empty; token key absent |
| After successful login | Access token per existing architecture (`college-ai-chatbot.access-token` in localStorage — documented Phase 5.4 tradeoff) | ✅ unchanged |
| After logout | Access token removed | ✅ `storeToken(null)`; test-verified |
| After session expiry | Access token removed | ✅ expiry handler + restore-failure path both remove it |
| Passwords | Never stored | ✅ passwords exist only as transient controlled React state and POST bodies; nothing persisted |

### Network request audit (static + request-shape tests)

- **Registration** — `GET /institutions/lookup?code=<url-encoded>` then
  `POST /users/register` with the exact backend schema
  (`registration.test.ts` asserts URL/method/body shape). No institution
  UUID is submitted (the server resolves the public code). No password in
  URLs or query strings. No duplicate submission (`submitting` guard +
  disabled controls; test-verified).
- **Login** — `POST /auth/login` for email (institution code NOT sent),
  `POST /auth/student/login` for academic identifiers (with
  `institution_code`). Password only in the POST body. Busy guard prevents
  duplicate login requests (test-verified).
- **Auth bootstrap** — `GET /auth/me` is the single canonical identity
  request (login path and refresh path). **No `/admin/me` role probe is
  performed anywhere in the bootstrap** (static verification; AdminShell
  test asserts no identity fetch).
- **No duplicate authentication requests** — one `/auth/me` per bootstrap;
  role probes eliminated in Phase 6.15.4 (regression-verified).

## 16. Frontend Tests

`npm test` (vitest run) — final result:

```text
Test Files  16 passed (16)
Tests       154 passed (154)     ← 152 before Phase 6.15.5 (+2 new)
```

| Test file | Tests |
|---|---|
| `src/features/auth/RegistrationForm.test.tsx` | 24 (22 + **2 new in 6.15.5**) |
| `src/services/auth.test.ts` | 23 |
| `src/services/registration.test.ts` | 15 |
| `src/features/auth/LoginForm.test.tsx` | 14 |
| `src/services/adminApi.test.ts` | 10 |
| `src/services/api.test.ts` | 9 |
| `src/services/devAuth.test.ts` | 8 |
| `src/features/auth/AuthProvider.test.tsx` | 9 |
| `src/App.test.tsx` | 6 |
| `src/hooks/useConversationHistory.test.ts` | 6 |
| `src/features/chat/ConversationList.test.tsx` | 8 |
| `src/features/admin/FaqManager.test.tsx` | 7 |
| `src/features/auth/ChangePasswordForm.test.tsx` | 3 |
| `src/features/auth/ForgotPasswordForm.test.tsx` | 5 |
| `src/features/academics/AcademicsPanel.test.tsx` | 5 |
| `src/features/admin/AdminShell.test.tsx` | 2 |

No test was modified to make a failure disappear. The only test-file change
in 6.15.5 is `RegistrationForm.test.tsx` (+2 tests for the new invariants).

## 17. Backend Tests

Full backend suite (`backend\.venv\Scripts\python -m pytest tests`):

```text
1616 passed, 15 skipped, 6 warnings in ~28s
```

All 15 skips are pre-existing manual-opt-in gates for live databases / real
providers (test_attendance_phase_6_7, test_organization_institution_phase_6_13_1,
test_physical_validation_phase_4_4, test_results_phase_6_8,
test_student_model_phase_6_2 — "requires explicit manual opt-in"). None are
authentication-related.

Targeted authentication/security suite (14 files) — **467 passed**:

`test_auth.py`, `test_student_auth_phase_6_5.py`,
`test_sign_in_phase_6_13_6.py`, `test_institution_lookup_phase_6_15_2.py`,
`test_user_registration_phase_6_13_5.py`, `test_student_registration_phase_6_3.py`,
`test_rbac_phase_6_6.py`, `test_role_scope_enforcement_phase_6_13_7.py`,
`test_security_final_validation_phase_6_13_9.py`, `test_tenant_isolation.py`,
`test_student_approval_phase_6_4.py`, `test_admin_api.py`,
`test_students_api.py`, `test_approval_workflow_phase_6_13_4.py`

This covers: authentication, student authentication, registration,
institution lookup, RBAC, tenant isolation, security validation, admin APIs,
and student academic authorization — all green.

## 18. End-to-End Matrix

| Flow | Expected | Result | Backed by |
|---|---|---|---|
| Student registration | Pending | ✅ PASS | RegistrationForm tests + 6.13.5/6.3 backend suites |
| Student email login | Student | ✅ PASS | auth.test.ts + App.test.tsx + student_auth suite |
| Student register-number login | Student | ✅ PASS | same |
| Student roll-number login | Student | ✅ PASS | same |
| Admin login | Admin | ✅ PASS | test_auth.py + App.test.tsx |
| Staff login | Staff | ✅ PASS | test_auth.py + App.test.tsx |
| Faculty login | Faculty | ✅ PASS | test_auth.py + App.test.tsx |
| Refresh student session | Preserved | ✅ PASS | AuthProvider.test.tsx restore path |
| Refresh admin session | Preserved | ✅ PASS | AuthProvider.test.tsx restore path |
| Logout | Unauthenticated | ✅ PASS | AuthProvider.test.tsx |
| Expired token | Session cleared | ✅ PASS | AuthProvider / api / adminApi expiry tests |
| Student → admin API | Forbidden | ✅ PASS | test_rbac_phase_6_6 (403 FORBIDDEN) |
| Cross-tenant login | Rejected | ✅ PASS | test_student_auth (wrong-code 401) + test_tenant_isolation |
| Role tampering | No escalation | ✅ PASS | extra="forbid" 422 tests + RBAC suites |
| Token tampering | Rejected | ✅ PASS | security.py verify (401) + restore-clears-token test |

Every result is backed by an executed automated test or a verified static
contract inspection — none are assumed.

## 19. Issues Found

1. **[Fixed] Registration password retained after successful submission**
   (§20 requirement). After a successful registration the plaintext password
   and its confirmation remained in React component state while the
   pending-approval success screen was displayed. Never exposed to storage
   or the network, but it lingered in memory against the phase's
   "passwords are not retained after submission" requirement.
2. **[Pre-existing, documented — not fixed] React `act(...)` warnings in
   `AdminShell.test.tsx`** — `AdminDashboard` fires its async dashboard fetch
   on mount inside tests without `act` wrapping. Warnings only; both tests
   pass; test-hygiene item outside Phase 6.15.5 scope (fixing it would touch
   unrelated admin test files).
3. **[Pre-existing, documented — not fixed] Vite/CSS build warning** —
   Tailwind v4 optimizer emits "Invalid pseudo class after pseudo element"
   for a generated `::file-selector-button:disabled` rule. Present before
   6.15.5; unrelated to authentication; the build succeeds.
4. **[Observation, accepted] A malformed/empty 2xx body from an auth
   endpoint would surface as a generic error rather than a typed kind** —
   every consumer (`AuthProvider`, `RegistrationForm`) has a non-typed
   catch-all that renders a safe generic message. No crash, no stack trace;
   only the error-kind granularity is reduced in that hypothetical case.

## 20. Fixes Applied

**Phase 6.15.5 fix #1 — clear registration credentials after submission**
(`frontend/src/features/auth/RegistrationForm.tsx`):

- After `registerStudent(...)` succeeds, `setPassword('')` and
  `setConfirmPassword('')` run together with the success state update, so the
  plaintext password never lingers in component memory on the
  pending-approval screen.
- New tests (`RegistrationForm.test.tsx`, +2):
  1. *drops the password after submission: no password retention in UI or
     storage* — password/confirm inputs are gone after success, both
     storages stay empty, and a freshly mounted form never pre-fills
     credentials.
  2. *never authenticates after registration: no token exists in browser
     storage* — the AuthProvider token key is absent and
     `localStorage`/`sessionStorage` are empty after registration.

No other source change was made in Phase 6.15.5. Backend code: unchanged.

## 21. Known Limitations

- The access token remains in localStorage (documented Phase 5.4 tradeoff;
  no refresh-token architecture exists to replace it).
- No dedicated staff/faculty shells — by design they receive the student
  shell; backend authorization remains the privilege boundary.
- Browser-level click-through validation was performed via the jsdom
  testing-library suite and API-level pytest suites; the 15 live-database
  backend tests remain manual-opt-in skips and were not executed.
- Logout is client-side only (stateless JWT; no backend revocation endpoint
  exists).
- `act(...)` test warnings in `AdminShell.test.tsx` (pre-existing) remain.

## 22. Final Verification

| Requirement | Status |
|---|---|
| Registration end-to-end verified | ✅ |
| Institution lookup verified (200/404/422/403 + safe projection) | ✅ |
| Pending approval verified | ✅ |
| Student email / register-number / roll-number login verified | ✅ |
| Admin / staff / faculty login verified | ✅ |
| Refresh persistence verified (all roles) | ✅ |
| Logout verified | ✅ |
| Session expiry verified (exact message) | ✅ |
| Login 401 vs session 401 kept distinct | ✅ |
| Registration → approval → login lifecycle verified | ✅ |
| Rejected student behavior verified (anti-enumeration) | ✅ |
| Tenant isolation verified | ✅ |
| Role tampering / token tampering tested | ✅ |
| Protected APIs verified | ✅ |
| Browser storage audited | ✅ |
| Network requests audited | ✅ |
| Unexpected failures handled safely | ✅ |
| Duplicate submissions prevented | ✅ |
| Frontend tests pass (154/154) | ✅ |
| Frontend build passes | ✅ |
| Backend regression tests pass (1616 passed / 15 pre-existing skips) | ✅ |
| Security tests pass | ✅ |
| E2E matrix completed | ✅ |
| QA documentation created | ✅ (this file) |
| Git scope reviewed — no unrelated changes | ✅ |
| Nothing committed automatically | ✅ |

**PHASE 6.15.5 — COMPLETE.** No Phase 6.15.6 work was started.

## Git Scope (§30)

Pre-existing uncommitted working-tree content (Phases 6.15.1–6.15.4,
untouched by 6.15.5):

- Modified (17): `backend/app/api/institutions.py`,
  `backend/app/core/security.py`, `backend/app/main.py`,
  `backend/app/schemas/tenancy.py`, `backend/app/services/tenancy.py`,
  `backend/tests/test_auth.py`, `frontend/src/App.test.tsx`,
  `frontend/src/App.tsx`, `frontend/src/features/admin/AdminShell.test.tsx`,
  `frontend/src/features/admin/AdminShell.tsx`,
  `frontend/src/features/auth/AuthProvider.tsx`,
  `frontend/src/features/auth/LoginForm.test.tsx`,
  `frontend/src/features/auth/LoginForm.tsx`,
  `frontend/src/services/adminApi.ts`, `frontend/src/services/api.ts`,
  `frontend/src/services/auth.ts`, `frontend/src/types/auth.ts`
- Untracked (13): `PHASE_6_15_1_AUTH_UI_AUDIT.md`,
  `PHASE_6_15_2_REGISTRATION_FRONTEND.md`,
  `PHASE_6_15_3_STUDENT_IDENTIFIER_LOGIN.md`,
  `PHASE_6_15_4_AUTH_ROLE_SESSION.md`,
  `backend/tests/test_institution_lookup_phase_6_15_2.py`,
  `frontend/src/features/auth/AuthProvider.test.tsx`,
  `frontend/src/features/auth/RegistrationForm.test.tsx`,
  `frontend/src/features/auth/RegistrationForm.tsx`,
  `frontend/src/services/auth.test.ts`,
  `frontend/src/services/registration.test.ts`,
  `frontend/src/services/registration.ts`,
  `frontend/src/services/sessionEvents.ts`,
  `frontend/src/types/registration.ts`

Phase 6.15.5 additions:

- `PHASE_6_15_5_AUTH_E2E_QA.md` (NEW — this document)
- Hardening fix + 2 tests inside the (already untracked)
  `RegistrationForm.tsx` / `RegistrationForm.test.tsx` from Phase 6.15.2 —
  git cannot separately attribute hunks inside untracked files; the exact
  6.15.5 delta is documented in §20.

Nothing was committed.

