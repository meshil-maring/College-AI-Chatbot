# Phase 6.15.1 — Authentication UI Audit & Contract Verification

> Audit phase only. **No implementation changes were made.** Every statement
> below is verified against the actual repository source, cited by file path.
> Date of audit: 2026-09-20 (branch `main`, commit `7a6b39e`).

---

## 1. Audit Objective

Establish the exact current state of the frontend authentication/registration
architecture and the backend authentication contract before implementing
Phase 6.15. This report documents — without modifying — the login UI, auth
state management, auth API clients, backend auth endpoints, student
registration backend support, route protection, role-based behavior, token
persistence, error handling, and existing tests.

---

## 2. Frontend Authentication Architecture

### 2.1 Files inspected

| File | Role |
| ---- | ---- |
| `frontend/src/App.tsx` | Top-level render gating (NO router library) |
| `frontend/src/features/auth/AuthProvider.tsx` | Auth state (React Context) |
| `frontend/src/features/auth/LoginForm.tsx` | Login UI |
| `frontend/src/features/auth/ForgotPasswordForm.tsx` | Dev-only password reset UI |
| `frontend/src/features/auth/ChangePasswordForm.tsx` | Dev-only change-password UI |
| `frontend/src/services/auth.ts` | Auth API client (login / me) |
| `frontend/src/services/api.ts` | Chat + conversations client (consumes token) |
| `frontend/src/services/adminApi.ts` | Admin + student-self-service client |
| `frontend/src/services/devAuth.ts` | Dev-only password recovery client |
| `frontend/src/types/auth.ts` | Auth contract types |
| `frontend/src/types/admin.ts` | Admin identity + student profile types |
| `frontend/src/features/admin/AdminShell.tsx` | Admin panel shell (post-login) |
| `frontend/src/features/chat/ChatShell.tsx`, `features/academics/AcademicsPanel.tsx` | Student surface |

### 2.2 State mechanism


### 2.3 Session lifecycle

* **Restore (refresh):** on mount, saved token is re-validated via
  `GET /api/v1/auth/me`. `session_invalid` (401/404) → token discarded;
  `network` → token retained with a controlled error (AuthProvider.tsx:71–105).
* **Login:** `POST /auth/login` then `GET /auth/me` bootstrap, token stored,
  status → `authenticated` (AuthProvider.tsx:111–135).
* **Logout:** local-only clear of token/user/status. The backend is stateless
  JWT with **no logout/revocation endpoint** (AuthProvider.tsx:137–143).
* **Expired session mid-use:** NOT globally handled. A 401 during chat or
  admin calls surfaces as `ApiError`/`AdminApiError` in the calling
  component; `AuthProvider` only re-validates on page load. There is no
  token refresh (no refresh token exists in the contract).

---

## 3. Backend Authentication Architecture

### 3.1 Files inspected

| File | Role |
| ---- | ---- |
| `backend/app/api/auth.py` | `POST /auth/signup`, `POST /auth/login` |
| `backend/app/api/student_auth.py` | `POST /auth/student/login` (Phase 6.5) |
| `backend/app/api/registration.py` | `POST /registration` (Phase 6.3) |
| `backend/app/services/student_auth.py` | Student identity resolution + sign-in |
| `backend/app/services/sign_in.py` | Phase 6.13.6 post-auth status guard |
| `backend/app/services/student_registration.py` | Registration service + schemas |
| `backend/app/services/admin_academics.py` | `approve_student` / `reject_student` (Phase 6.4) |
| `backend/app/core/security.py` | JWT verification, `get_current_user`, `require_roles`, tenant scoping |
| `backend/app/core/errors.py` | `AppError` + `{"error":{code,message}}` envelope |
| `backend/app/main.py` | Router mounting, `/api/v1/auth/me`, 422 normalization |
| `backend/app/api/institutions.py` | Institution registration/join (Phase 6.13.3) |
| `backend/app/api/dev_auth.py` | Dev-only password endpoints (DEV_TEST_MODE gated) |


### 3.3 Token mechanism

* Supabase Auth (GoTrue) is the **single credential authority**; the app never
  stores, hashes, or compares passwords.
* Backend verifies the Supabase ES256 JWT server-side via JWKS
  (`PyJWKClient`, `leeway=10s`) — `security.py:36–53`. Rejection codes:
  401 `AUTH_REQUIRED` / `INVALID_SCHEME` / `TOKEN_MISSING` / `TOKEN_EXPIRED` /
  `INVALID_TOKEN`; 404 `USER_NOT_FOUND`.
* Roles + institution scope are **always resolved server-side** from
  `user_roles` / `students` (`get_current_user` → `get_user_by_auth_id`);
  the client can never inject them (all request schemas use
  `extra="forbid"`).
* Authorization failures: 403 `FORBIDDEN` (`require_roles`), 403
  `TENANT_MISMATCH` (institution isolation, `security.py:120–160`).

### 3.4 Error envelope

```json
{ "error": { "code": "<MACHINE_CODE>", "message": "<text>" } }
```

Validation failures (422) are normalized in `main.py:37–69` to
`{"error":{"code":"VALIDATION_ERROR","message":"Request validation failed",
"details":[{loc,msg,type}]}}`.

---

## 4. Current Login Flow

### 4.1 Login UI audit (`LoginForm.tsx`)

| Aspect | Current state |
| ------ | ------------- |
| Fields | **Email** + **Password only** |
| Labels | `Email`, `Password` (wrapped `<label>`) |
| Placeholders | `student@college.edu`, `••••••••` |
| Validation | HTML-only: email `type="email"` + `required`; password `required` + `minLength={6}` |
| Password handling | `type="password"`, `autoComplete="current-password"`, never stored/logged |
| Submit | `onSubmit` → `preventDefault()` → `login(email, password)`; no-op when busy |
| Loading | Button label `Signing in…`, inputs + button `disabled` |
| Error | `role="alert"` red banner; message comes from `authErrorMessage` mapping |
| Success | Status → `authenticated`; `App.tsx` swaps the form for the app shell |
| Redirect | None — conditional render swap (no router, no `window.location`) |
| Mobile | Responsive: `min-h-screen` centered flex, `max-w-md w-full px-4` |
| Accessibility | Wrapped labels, `role="alert"`, focus rings, disabled semantics |
| Extra | Dev/test-only "Forgot password?" link shown only when backend reports `dev_test_mode` |

### 4.2 Identifier support in the CURRENT login UI

| Identifier | Supported? |
| ---------- | ---------- |
| Email | **Yes** (only supported field) |
| Register number | **No** |
| University roll number | **No** |
| Institution code | **No** |

### 3.2 Endpoints (verified)

| Method | Endpoint | Auth | Purpose |
| ------ | -------- | ---- | ------- |
| POST | `/api/v1/auth/signup` | none | Supabase GoTrue signup (legacy surface, unused by frontend) |
| POST | `/api/v1/auth/login` | none | Email + password (admins/faculty/staff/demo). Phase 6.13.6 status guard |
| POST | `/api/v1/auth/student/login` | none | Student login: `identifier` (email / register_number / university_roll_number) + `password` (+ `institution_code` for academic identifiers) |

### 4.3 Runtime flow

```
LoginForm → services/auth.ts login({email,password})
    → POST /api/v1/auth/login
        → Supabase GoTrue sign_in_with_password
        → Phase 6.13.6 guard (sign_in.py): public.users row exists,
          users.status=='active', students: approval=='approved' +
          student active + institution active
        → any denial normalized to 400 INVALID_CREDENTIALS
          (anti-enumeration, auth.py:118–133)
    → GET /api/v1/auth/me (token bootstrap) → state populated
App.tsx AuthGate → AuthenticatedShell
```

---

## 5. Current Registration Flow

### 5.1 Backend (EXISTS — Phase 6.3, verified)

`POST /api/v1/registration` (`registration.py` → `student_registration.py`):

* **Request** (`StudentRegistrationRequest`, `extra="forbid"`):
  `institution_id: UUID (required)`, `email` (EmailStr), `password` (≥6),
  `first_name`, `last_name`, `register_number?`, `university_roll_number?`,
  `enrollment_date?`.
* **Preconditions:** at least one academic identifier required
  (422 `IDENTIFIER_REQUIRED`); institution must exist (404
  `INSTITUTION_NOT_FOUND`) and be active (403
  `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS`).
* **Duplicates (409):** `STUDENT_ALREADY_REGISTERED`,
  `EMAIL_ALREADY_REGISTERED` (account-level),
  `EMAIL_ALREADY_REGISTERED` / `REGISTER_NUMBER_ALREADY_REGISTERED` /
  `ROLL_NUMBER_ALREADY_REGISTERED` (institution-scoped).
* **Creation chain:** GoTrue auth account → `public.users`
  (`status='active'`) → `students` profile with
  **`approval_status='pending'`** (verified:
  `student_registration.py:348`, `PENDING = "pending"` at line 65);
  `student_number` is derived from `register_number` (preferred) else
  `university_roll_number` — never fabricated. Partial failures are
  compensated (best-effort auth-user/public-user deletion).
* **Response (201):** `{message: "Registration submitted. Your account is
  pending approval.", student_id, institution_id, email,
  approval_status: "pending"}`.

### 5.2 Approval flow (verified end-to-end)

```
Student registers (POST /registration)
        ↓  students.approval_status = 'pending'
Admin/staff approve: POST /api/v1/admin/students/{id}/approve (Phase 6.4,
        tenant-scoped, audit-logged) → 'approved'
        ↓
Only approval_status == 'approved' students can authenticate
        (student_auth.py:_assert_approved; sign_in.py:87–89)
```

Initial approval state verified from code: **`'pending'`** — the constant
`PENDING = "pending"` (`student_registration.py:65`) is written explicitly
in `_create_student_profile` and echoed in `RegistrationResponse`.

### 5.3 Frontend registration

**Student registration frontend: NOT IMPLEMENTED.**

No registration component, route, form, API integration, or approval
messaging exists anywhere in `frontend/src` (verified by full-source search
for `registration`, `institution_code`, `student/login` — zero frontend
hits). This is documented as a gap, not implemented in this phase.

---

## 6. Authentication API Contract

### 6.1 `POST /api/v1/auth/login` (used by current frontend)

```text
Method:   POST
Endpoint: /api/v1/auth/login
Request:  { email: EmailStr, password: str }   (extra="forbid", password ≥ 6)
Response: { access_token: str, message: str, user: { id, email } }
Auth:     Supabase GoTrue; JWT returned as opaque access_token
Errors:   400 INVALID_CREDENTIALS (wrong password OR any status-guard denial),
          422 VALIDATION_ERROR, 5xx AUTH_ERROR
```

### 6.2 `GET /api/v1/auth/me`

```text
Method:   GET  (Authorization: Bearer <token>)
Response: { authenticated: true, user_id, auth_user_id, email }
Errors:   401 AUTH_REQUIRED / INVALID_SCHEME / TOKEN_MISSING / TOKEN_EXPIRED /
          INVALID_TOKEN, 404 USER_NOT_FOUND
```

**Note:** no `role`, `institution_id`, `student_id`, or `approval_status`
is returned — the frontend cannot know the user's role from this endpoint.

### 6.3 `POST /api/v1/auth/student/login` (Phase 6.5 — NOT used by frontend)

```text
Method:   POST
Endpoint: /api/v1/auth/student/login
Request:  { identifier: str, password: str, institution_code?: str }
          (extra="forbid"; institution_code REQUIRED for non-email
          identifiers, else 422 VALIDATION_ERROR)
Response: { access_token, message, user: { id, email } }
Errors:   ALL failures normalized to 401 INVALID_CREDENTIALS
          (unknown identifier, wrong password, pending/rejected student,
          inactive student/institution, ambiguous identity, unknown code)
```

### 6.4 `POST /api/v1/registration`

See §5.1. Full error surface: 409 (4 duplicate codes), 404
`INSTITUTION_NOT_FOUND`, 403 `INSTITUTION_NOT_ACCEPTING_REGISTRATIONS`,
422 `IDENTIFIER_REQUIRED` / `VALIDATION_ERROR`, 500 `REGISTRATION_FAILED`.

---

## 7. Student Identity Contract

### 7.1 Identifier semantics (verified)

| Field | Uniqueness | Institution scoping | Notes |
| ----- | ---------- | ------------------- | ----- |
| `email` | **Globally unique** per `public.users` + Supabase Auth | Not required for login lookup | Also institution-scoped unique in `students` (duplicate check) |
| `register_number` | Unique **per institution** (Phase 6.2) | **Required** (`institution_code`) at login | Preferred source for derived `student_number` |
| `university_roll_number` | Unique **per institution** (Phase 6.2) | **Required** (`institution_code`) at login | Fallback source for `student_number` |
| `student_number` | Unique per institution, NOT NULL | Yes | Derived at registration, never client-supplied |
| `institution_id` | Internal UUID tenant key | — | Resolved server-side from `institutions.code` |
| `institution_code` | Public identifier (`institutions.code`, upper-cased) | — | Login + tenant resolution input; **not** the registration key |
| `auth_user_id` | Globally unique (Supabase `auth.users.id`) | — | JWT `sub`; the ONLY trusted identity anchor |
| `user_id` / `student_id` | Internal PKs | — | Resolved server-side via `auth_user_id` |

### 7.2 Tenant / institution resolution

* Login (academic identifiers): `institution_code` → `institutions.code`
  (upper-cased, `maybe_single`) → `institution_id`; identifier lookup is
  strictly scoped to that institution (`student_auth.py:92–131`).
* Authenticated identity resolution: JWT `sub` (auth_user_id) →
  `public.users.user_id` → `students.user_id` → `institution_id`
  (`get_current_user`, `security.py:56–94`). **Clients can never override
  the identity or tenant** (verified by
  `tests/test_personalized_security_6148.py` forgery tests — all passing).

### 7.3 Fields returned to the frontend

| Context | Fields exposed | Internal IDs exposed? |
| ------- | -------------- | ---------------------- |
| Login (both endpoints) | `user.id` (Supabase auth id), `user.email` | auth UUID yes (inherent) |
| `/auth/me` | `user_id`, `auth_user_id`, `email` | Both UUIDs yes |
| `/admin/me` | `user_id`, `auth_user_id`, `email`, `roles`, `is_admin` | Both UUIDs yes |
| Registration response | `student_id`, `institution_id`, `email`, `approval_status`, `message` | Both UUIDs yes |
| Student `/students/me/*` | Own profile/results/attendance (JWT-resolved, tenant-checked) | Own internal IDs yes |

---

## 8. Approval Flow

Verified chain (§5.2): registration writes `approval_status='pending'`
always; Phase 6.4 admin endpoints (`/admin/students/{id}/approve|reject`)
perform the only pending → approved/rejected transitions (tenant-scoped,
audit-logged, conditional write — `admin_academics.py:438–470`); both login
endpoints enforce `approval_status == 'approved'` before issuing a session
(`student_auth.py:_assert_approved`, `sign_in.py:87–89`).

**Frontend visibility of approval state: NONE.** Because login denials are
normalized to the generic invalid-credentials response (anti-enumeration),
the frontend cannot distinguish pending / rejected / disabled accounts at
login time. Approval feedback can only come from the registration response
message ("Your account is pending approval.") — which no frontend
currently renders.

---

## 9. Authentication State Management

| Concern | Current implementation |
| ------- | ---------------------- |
| Storage | React Context (memory) + `localStorage` access token only |
| Current user | `CurrentUser {authenticated, user_id, auth_user_id, email}` via `/auth/me` |
| Role | **Not stored** — inferred only by probing `GET /admin/me` (§11) |
| Institution | **Not stored** anywhere in the frontend |
| Student identity | **Not stored** (student "me" data is fetched ad-hoc with the token) |
| Refresh survival | Token in localStorage; `/auth/me` re-validation on mount |
| Logout | Local clear only; no backend revocation endpoint exists |
| Expired session | Detected only on next page load (`session_invalid` → token discarded); no mid-session global 401 handler |
| Unauthorized API response | `ApiError` / `AdminApiError` surfaced per-component; admin shell shows "Access denied" + Sign out on probe failure |

Mechanisms checked and ruled out: `sessionStorage` (absent), cookies
(absent), Zustand/Redux (not installed), custom hooks beyond `useAuth`
(absent). The existing mechanism is **not** replaced by this phase.

---

## 10. Route Protection

**There is no URL-based routing.** The app has no React Router and no URL
routes; "routes" are conditional render branches in `App.tsx`
(`AuthGate` → `RestoringShell` / `LoginForm` / `AuthenticatedShell`,
`AuthenticatedShell` → `AdminShell` / `StudentShell`).

Access determination: purely **frontend state + a backend authorization
probe** (`GET /api/v1/admin/me` succeeds ⇔ `admin` role, enforced server-side
by `_ADMIN` dependency).

| Transition | Current behavior |
| ---------- | ---------------- |
| Unauthenticated → protected UI | Impossible via UI: every protected shell renders only in `status === 'authenticated'`; login form is shown instead. **Backend enforces 401** on all protected APIs. |
| Student → admin surface | `GET /admin/me` probe fails (403 `FORBIDDEN` server-side) → `StudentShell` rendered. Student never sees admin panels. |
| Student → staff surface | No staff UI exists (nothing to reach). |
| Student → faculty surface | No faculty UI exists (nothing to reach). |
| Admin → student surface | Admin gets `AdminShell` only; the student chat/academics UI is not rendered for admins (role probe result is binary). |
| Staff → student surface | Staff/faculty users are treated as students by the UI (probe fails → `StudentShell`); they would hit 403 `FORBIDDEN` from student-only backend endpoints. **UI role assumption is incomplete** (documented, not changed). |
| Faculty → student surface | Same as staff. |

Backend enforcement is authoritative regardless of UI state (`require_roles`,
tenant scoping, `TENANT_MISMATCH`) — verified by
`tests/test_rbac_phase_6_6.py` (all passing). No route behavior was changed.

---

## 11. Role-Based Redirects

There are **no redirects** (no router). Post-login behavior:

```
login success → AuthenticatedShell
    → GET /api/v1/admin/me probe
        success → AdminShell        (admin)
        failure → StudentShell      (student, staff, faculty — indistinguishable)
```

Redirect/branch basis: **backend authorization probe** (not a
backend-provided role claim, not hardcoded role lists, not user type).
`/auth/me` deliberately returns no role, so the frontend cannot branch on
role except by probing endpoints.

Identified unsafe/duplicated role assumptions:

1. **Binary role model in the UI** — everything non-admin is rendered as a
   student (`App.tsx:76–107`). Staff/faculty users are silently routed to
   the student experience.
2. **Duplicated probe** — `AuthenticatedShell` (App.tsx:80–92) and
   `AdminShell` (AdminShell.tsx:53–66) each call `getAdminIdentity`
   independently (two HTTP calls for the same fact on every admin login).
3. **Probe-per-render** — the admin probe re-runs on every
   `accessToken` change with no caching; a 401/403 shows a generic
   "Access denied" screen with only a Sign out button.

---

## 12. Error Handling

### 12.1 Frontend mapping (`services/auth.ts:37–148`)

| HTTP | Backend code | Frontend `AuthError.kind` | User message |
| ---- | ------------ | ------------------------- | ------------ |
| 400 | `INVALID_CREDENTIALS` | `invalid_credentials` | "The email or password is incorrect…" |
| 422 | any | `validation` | "Please enter a valid email…" |
| 401/404 | any | `session_invalid` | "The saved session could not be verified…" |
| ≥500 | any | `server` | "The authentication server reported an error…" |
| no response | — | `network` | "Could not reach the backend…" |
| other | any | `unknown` | "Something went wrong…" |

Chat/admin clients (`api.ts`, `adminApi.ts`) map `error.message` /
`detail` to display text generically; `AdminApiError` carries `code`.

### 12.2 Situation coverage

| Situation | Backend | Frontend | Handled? |
| --------- | ------- | -------- | -------- |
| Invalid credentials | 400/401 `INVALID_CREDENTIALS` | mapped | ✅ (but see §15 status mismatch) |
| Unknown account | normalized to invalid-credentials | same message | ✅ (anti-enumeration by design) |
| Pending approval | 400/401 `INVALID_CREDENTIALS` (deliberate) | "incorrect password" message | ⚠️ Indistinguishable — approval state is never communicated |
| Rejected account | same as above | same | ⚠️ Same |
| Disabled account (`users.status != active`) | same as above | same | ⚠️ Same |
| Invalid institution code | 401 `INVALID_CREDENTIALS` (student login) | not surfaced (no student login UI) | ❌ MISSING FRONTEND |
| Duplicate email | 409 `EMAIL_ALREADY_REGISTERED` / `STUDENT_ALREADY_REGISTERED` | not surfaced (no registration UI) | ❌ MISSING FRONTEND |
| Duplicate register number | 409 `REGISTER_NUMBER_ALREADY_REGISTERED` | not surfaced | ❌ MISSING FRONTEND |
| Duplicate university roll number | 409 `ROLL_NUMBER_ALREADY_REGISTERED` | not surfaced | ❌ MISSING FRONTEND |
| Validation error | 422 `VALIDATION_ERROR` (+details) | mapped | ✅ |
| Network failure | — | `network` kind | ✅ |
| Server failure | 5xx | `server` kind | ✅ |
| Expired authentication | 401 `TOKEN_EXPIRED` | `session_invalid` on restore only; mid-session → per-component error | ⚠️ Partial |
| Unauthorized request | 403 `FORBIDDEN` | generic message / "Access denied" screen | ✅ (coarse) |
| Forbidden (tenant) | 403 `TENANT_MISMATCH` | generic message | ✅ (coarse) |

Backend messages are **not** displayed verbatim for login (the frontend uses
its own fixed copy keyed on code) and are displayed generically elsewhere.
No backend auth messages are lost, but the duplicate-registration codes
currently have **no** consumer.

---

## 13. Existing Tests

### 13.1 Frontend — `npm test` (`vitest run`, from `frontend/`)

```
Test command:  npm test   (package.json script "test": "vitest run")
Total tests:   69
Passed:        69
Failed:        0
Skipped:       0
Errors:        0        (12 test files, all green)
```

Auth-related frontend tests executed:

| File | Tests | Scope |
| ---- | ----- | ----- |
| `src/features/auth/LoginForm.test.tsx` | 2 | login form rendering/submission |
| `src/features/auth/ForgotPasswordForm.test.tsx` | 5 | dev-only reset flow |
| `src/features/auth/ChangePasswordForm.test.tsx` | 3 | dev-only change flow |
| `src/services/devAuth.test.ts` | 8 | dev auth client error mapping |
| `src/services/api.test.ts` | 9 | chat/conversation client |
| `src/services/adminApi.test.ts` | 10 | admin client + error mapping |
| `src/App.test.tsx` | 2 | top-level gate behavior |

**No dedicated test exists for the future student identifier login UI or a
registration UI** (they don't exist yet). `devAuth.test.ts` /
`ForgotPasswordForm.test.tsx` / `ChangePasswordForm.test.tsx` are the
closest auth-adjacent coverage beyond LoginForm.

### 13.2 Backend — `pytest` (from `backend/`, venv interpreter)

```
Test command:  .\.venv\Scripts\python.exe -m pytest tests/<files> -q
Auth subset (test_auth.py, test_student_auth_phase_6_5.py,
             test_student_registration_phase_6_3.py,
             test_sign_in_phase_6_13_6.py):        165 passed
RBAC/approval/security (test_rbac_phase_6_6.py,
             test_security_final_validation_phase_6_13_9.py,
             test_student_approval_phase_6_4.py):  136 passed
Stale-cache re-check (test_personalized_security_6148.py,
             test_organization_registration_phase_6_13_2.py): 89 passed
Failed:        0
Skipped:       0 (in the executed subset)
Errors:        0
```

**Pre-existing failures: NONE.** `backend/.pytest_cache/v/cache/lastfailed`
listed failures for `test_personalized_security_6148.py` and
`test_organization_registration_phase_6_13_2.py`; re-running them today
shows **89/89 passing**, so the cache file is **stale**, not a real
pre-existing failure. All executed tests passed on this audit run.

---

## 14. Security Findings

Lightweight, implementation-level only (no destructive testing, no
architecture changes):

1. **Access token in `localStorage`** (`AuthProvider.tsx:28`) — readable by
   any XSS payload. Documented tradeoff of the Phase 5.4 lock; no refresh
   token exists (limits blast radius). No change made.
2. **No mid-session 401 handling** — an expired token surfaces as
   component-level errors rather than a forced re-login (usability, not
   strictly security).
3. **Internal database IDs exposed to the UI** — `/auth/me` returns
   `user_id` + `auth_user_id`; the registration response returns
   `student_id` + `institution_id`. Low sensitivity (UUIDs, no PII beyond
   email), but worth noting before new UI work relies on them.
4. **Frontend-only authorization appearance** — the admin probe is a UI
   convenience; real authorization is enforced server-side
   (`require_roles`, tenant scoping). ✅ Correct direction. The residual
   risk is UX (staff seeing a student UI), not privilege escalation.
5. **Client-supplied role/approval injection: PREVENTED** — all auth request
   schemas use `extra="forbid"`; roles/approval are always resolved
   server-side. Verified by `test_rbac_phase_6_6.py::
   test_student_login_rejects_client_role_fields`,
   `test_sign_in_phase_6_13_6.py::test_16*`, and
   `test_security_final_validation_phase_6_13_9.py` role-escalation tests.
6. **Anti-enumeration: PRESENT** — pending/rejected/inactive accounts are
   byte-identical to wrong-password failures on both login endpoints.
7. **Public `/api/v1/auth/signup`** creates a GoTrue account with no
   `public.users` linkage; such an account can never complete sign-in
   (fails closed in the Phase 6.13.6 guard). Unused legacy surface — flag
   for future cleanup consideration, not changed here.
8. **Dev password endpoints** (`/dev/auth/*`) are gated server-side by
   `DEV_TEST_MODE` (404 otherwise) and the frontend fails closed
   (`devAuth.ts:140–149`). No production path.
9. **Passwords/tokens in logs: NOT FOUND** — no password or token appears
   in any frontend log/render path; the backend forwards passwords only to
   GoTrue and never logs them (module docstrings + code review).
10. **No hardcoded credentials or institution identifiers** found in
    `frontend/src` (base URL only, via `VITE_API_BASE_URL`).

---

## 15. Frontend/Backend Contract Mismatches

| Feature | Backend | Frontend | Status |
| ------- | ------- | -------- | ------ |
| Email + password login | Supported (`/auth/login`) | Supported (`LoginForm`) | **MATCH** |
| Register number + password + institution code | Supported (`/auth/student/login`) | Not implemented | **MISSING FRONTEND SUPPORT** |
| University roll number + password + institution code | Supported (`/auth/student/login`) | Not implemented | **MISSING FRONTEND SUPPORT** |
| Email + password via student endpoint | Supported (`identifier`=email, no code needed) | Not used (uses `/auth/login`) | **MISMATCH (routing)** |
| Student registration | Supported (`POST /registration`) | Not implemented | **MISSING FRONTEND SUPPORT** |
| Approval status surfaced to user | Only in registration response; login denials masked | Nothing renders it | **MISMATCH** |
| Role in session identity | `/auth/me` returns **no role** | UI probes `/admin/me` instead | **MISMATCH (workaround)** |
| Institution representation | `institution_id` (UUID) for registration; `institution_code` (string) for login | Neither exists | **MISMATCH (two different keys for two flows)** |
| Error status on bad credentials | `/auth/login` → **400**; `/auth/student/login` → **401** (both `INVALID_CREDENTIALS`) | 400+`INVALID_CREDENTIALS` → `invalid_credentials`; 401 → `session_invalid` | **MISMATCH** — reusing the current classifier on the student endpoint would misreport bad credentials as "session could not be verified" |
| Field naming | Login `user.id`; `/auth/me` `user_id`/`auth_user_id` | Mirrored faithfully in `types/auth.ts` | **MATCH** |
| Error envelope | `{"error":{code,message}}`; 422 normalized with `details` | `auth.ts` reads `error.code`; `api.ts` reads `detail`; `adminApi.ts` reads both | **MATCH (auth) / PARTIAL (api.ts ignores `error.code`)** |
| Token type | Supabase JWT (no refresh token, no expiry field returned) | `LoginResponse` declares no refresh/expiry | **MATCH** |

---

## 16. Missing Functionality

1. **Student identifier login UI** — no frontend for
   `POST /auth/student/login` (register number / roll number / institution
   code fields absent from `LoginForm`).
2. **Student registration UI** — `Student registration frontend:
   NOT IMPLEMENTED` (backend Phase 6.3 fully ready).
3. **Institution lookup for registration** — the registration schema takes
   `institution_id` (UUID), while the login flow uses `institution_code`.
   **No public endpoint exists to resolve an institution by code**
   (`/institutions/*` only supports institution registration + join
   decisions). A registration form driven by a human-friendly code needs
   either a backend lookup endpoint or an explicit code→id strategy.
   **MISSING BACKEND SUPPORT** (documented, not implemented).
4. **Role in `/auth/me`** — no role/institution in the session identity;
   frontend is forced to probe `/admin/me`. Staff/faculty have no UI at all.
5. **Approval-state messaging** — a pending student cannot learn their
   account is pending (login denial is masked by design); no registration
   success screen exists to carry the message.
6. **Mid-session expiry handling / logout-on-401** — absent.
7. **Frontend tests for student login + registration** — none exist yet.

---

## 17. Required Changes for Phase 6.15.2+

Recommended implementation order (none performed in this phase):

1. **Registration UI first** (backend is ready; zero backend change needed
   for the core flow): component + form (decide the institution key
   strategy per §16.3), validation mirroring backend rules (≥1 academic
   identifier, password ≥6, non-blank names), error mapping for
   409/404/403/422, pending-approval success message, link back to login.
2. **Student identifier login UI**: extend the login experience with an
   identifier mode (email OR register/roll + institution code), calling
   `POST /auth/student/login`; **fix the error classifier first** so 401
   `INVALID_CREDENTIALS` maps to `invalid_credentials` (not
   `session_invalid`).
3. **Post-login role resolution**: obtain role/institution from the backend
   (extend `/auth/me` server-side or probe) so student-vs-admin branching
   stops relying on a failing-request probe; keep `extra="forbid"`
   server-side resolution unchanged.
4. **Session hardening**: global 401 handling (clear session on
   `TOKEN_EXPIRED`), reusing the existing AuthProvider mechanism only.
5. **Tests**: frontend Vitest coverage for registration + student login
   (error mapping, pending-approval copy, institution-code requirement);
   no modification of passing backend tests.

Constraints going forward: no backend auth changes are required for items
1–2 except the optional institution-lookup endpoint (§16.3), which must be
decided explicitly before Phase 6.15.2 implementation.

---

## 18. Final Audit Status

| Definition-of-Done item | Status |
| ----------------------- | ------ |
| Existing frontend auth architecture inspected | ✅ §2, §9 |
| Existing backend auth architecture inspected | ✅ §3 |
| Login UI audited | ✅ §4 |
| Registration backend audited | ✅ §5.1–5.2 |
| Registration frontend audited | ✅ §5.3 — NOT IMPLEMENTED (documented) |
| Student identity flow verified | ✅ §7 |
| Institution scoping verified | ✅ §7.2 |
| Approval flow verified | ✅ §5.2, §8 (initial state: `pending`) |
| Auth state management verified | ✅ §2.2–2.3, §9 |
| Protected routes verified | ✅ §10 (no URL routes; render gating + server RBAC) |
| Role-based redirects verified | ✅ §11 (binary admin probe; gaps documented) |
| Error handling verified | ✅ §12 |
| Existing auth tests executed | ✅ §13 — frontend 69/69; backend 390 executed, 0 failures |
| Security findings documented | ✅ §14 |
| Frontend/backend contracts compared | ✅ §15 |
| Missing functionality documented | ✅ §16 (incl. MISSING BACKEND SUPPORT: institution-code lookup) |
| `PHASE_6_15_1_AUTH_UI_AUDIT.md` created | ✅ this document |
| No unrelated implementation changes introduced | ✅ only this audit report was created |

**Audit outcome: COMPLETE.** The backend fully supports all three student
login identifiers and the full registration → approval → authentication
chain; the frontend currently supports email+password login only, has no
student identifier login, no registration UI, and infers roles by probing.
All gaps are documented above for Phase 6.15.2+. **Stopping here per phase
instructions — Phase 6.15.2 has NOT been started.**


| POST | `/api/v1/registration` | none | Student self-registration → always `approval_status='pending'` |
| GET | `/api/v1/auth/me` | Bearer JWT | Identity bootstrap (`{authenticated, user_id, auth_user_id, email}`) |
| GET | `/api/v1/admin/me` | Bearer + `admin` role | `{user_id, auth_user_id, email, roles, is_admin:true}` |
| POST | `/api/v1/admin/students/{id}/approve` \| `/reject` | admin/staff (`_APPROVAL`) | Phase 6.4 approval lifecycle, tenant-scoped, audit-logged |
| GET | `/api/v1/dev/auth/status` | none | `{dev_test_mode}` boolean |
| POST | `/api/v1/dev/auth/forgot-password`, `/change-password` | none | 404 unless `DEV_TEST_MODE` enabled |

* **React Context** (`AuthProvider`) + **localStorage** for the access token
  only. **No** Zustand, Redux, sessionStorage, or cookies.
* localStorage key: `college-ai-chatbot.access-token`
  (`AuthProvider.tsx:28`). The password is never persisted; the token is
  treated as an opaque string.
* Status state machine: `'restoring' | 'unauthenticated' | 'authenticating' | 'authenticated'`
* Context value: `{ status, user, accessToken, error, login, logout }`
  where `user: CurrentUser | null` is `{ authenticated, user_id,
  auth_user_id, email }` (from `GET /api/v1/auth/me`).
* **No role, institution, or student identity is held in frontend auth state.**
