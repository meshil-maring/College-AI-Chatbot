# Phase 6.15.3 — Student Identifier Login Frontend & Authentication Error Handling

Status: **COMPLETE** — no backend changes required.

---

## 1. Objective

Close the verified frontend/backend gap (Phase 6.15.1 audit §11 gap #1): the
backend already supports `POST /api/v1/auth/student/login` with a unified
identifier (email / register number / university roll number), but the
frontend only supported email login via `POST /api/v1/auth/login`. This phase
adds student identifier login to the existing login form and fixes the
Phase 6.15.1 error-classification defect: student login returns HTTP **401**
for invalid credentials, which the previous classifier collapsed into
`session_invalid`.

## 2. Existing Authentication Contract (verified, unchanged)

```text
LoginForm
   ↓ services/auth.ts login()
POST /api/v1/auth/login            { email, password }   (extra-forbid)
   ↓ 200 { access_token, message, user: { id, email } }
GET  /api/v1/auth/me               Bearer JWT
   ↓ 200 { authenticated, user_id, auth_user_id, email }
AuthProvider                       status/user/accessToken
   ↓ App.tsx AuthenticatedShell → GET /api/v1/admin/me probe → Admin/Student shell
```

- Errors on `/auth/login`: 400 `INVALID_CREDENTIALS`; 422 validation.
- Errors on `/auth/me`: 401 (`AUTH_REQUIRED`, `INVALID_SCHEME`, `TOKEN_MISSING`,
  `TOKEN_EXPIRED`, `INVALID_TOKEN`), 404 `USER_NOT_FOUND`.
- Role resolution remains the untouched `/admin/me` probe in `App.tsx`
  (`AuthenticatedShell`); the frontend never decides roles.

## 3. Student Login Contract (verified from the repository, unchanged)

`POST /api/v1/auth/student/login` (backend/app/api/student_auth.py,
schemas in app/schemas/student_auth.py):

```text
Request (extra="forbid"):
  identifier        str   ← UNIFIED field: email | register_number | university_roll_number
  password          str
  institution_code  str?  ← REQUIRED for academic identifiers; IGNORED for email

Success 200: { access_token, message: "Login successful.", user: { id, email } }
             (reuses the locked /auth/login response contract)

Errors:
  401 INVALID_CREDENTIALS ← EVERY auth failure (unknown identifier, wrong
                            password, pending/rejected student, inactive
                            student/institution, ambiguous identity) is
                            normalized to 401 for anti-enumeration
  422 VALIDATION_ERROR    ← academic identifier without institution_code
                            (raised by _validate_login_request) or FastAPI
                            validation
```

Key discovery: the backend takes ONE `identifier` field and resolves its type
itself (its `_is_email` heuristic), so the frontend needs NO
register-number-vs-roll-number classification and no per-institution formats.

## 4. Identifier Handling

Single UI input ("Email, Register Number or University Roll Number") maps to
the backend's unified `identifier` field verbatim (trimmed). The only
frontend classification is a mirror of the backend's own heuristic —
`services/auth.ts isEmailAddress()` ("@" present and a "." in the domain
part) — used EXCLUSIVELY to decide (a) which endpoint to call and (b) whether
an institution code is required. Register-number vs roll-number semantics are
never interpreted client-side; the backend remains authoritative.

## 5. Institution Code Handling

Per the verified backend contract (`_validate_login_request`):

| Identifier          | institution_code | Frontend behavior                                    |
| ------------------- | ---------------- | ---------------------------------------------------- |
| email               | optional/ignored | field hidden; never sent on either path              |
| register number     | REQUIRED (422)   | field shown + `required`; sent as `institution_code` |
| university roll no. | REQUIRED (422)   | field shown + `required`; sent as `institution_code` |

Email logins route to `/auth/login` where institution data is not part of the
contract, so no institution data is ever sent for email. The form also
guards client-side: an academic identifier without a code never submits.

## 6. Login UI Changes

`frontend/src/features/auth/LoginForm.tsx`:

- The "Email" field became the unified identifier field
  (`type="text"`, `autoComplete="username"`, label
  "Email, Register Number or University Roll Number").
- The Institution Code field is rendered ONLY while the identifier is a
  non-email (academic) value — the smallest UX change satisfying the
  contract (email users see no extra field). It is `required` when visible.
- Loading state kept: submit disabled + "Signing in…" while
  `status === 'authenticating'`; `onSubmit` no-ops when busy (duplicate
  submissions prevented); all inputs disabled while busy.
- Error banner (`role="alert"`) unchanged; the message is the new generic
  invalid-credentials copy for all rejected logins.
- Registration navigation ("Register as Student" ↔ "Back to Login") and the
  dev/test-gated "Forgot password?" link are untouched and re-verified.

## 7. API Client Changes

`frontend/src/services/auth.ts` (same single API client — no new client):

- `STUDENT_LOGIN_ENDPOINT = /api/v1/auth/student/login`.
- `studentLogin(request: StudentLoginRequest): Promise<LoginResponse>`.
- `authenticate(identifier, password, institutionCode?)`: the single routing
  entry point — email → `login()` (existing endpoint), academic identifier →
  `studentLogin()` with `institution_code` (omitted entirely for email;
  `JSON.stringify` drops it, satisfying `extra="forbid"`).
- `isEmailAddress()` exported for the form.
- `requestAuthJson`/`buildAuthError` gained an operation-context parameter
  (see §9). `login()`/`studentLogin()` use `'login'`; `fetchCurrentUser()`
  uses `'session'`.

## 8. Authentication State Integration

`frontend/src/features/auth/AuthProvider.tsx` — smallest safe change only:
`login()` now accepts `(identifier, password, institutionCode?)` and calls
`authenticate()`; everything else (restore via `/auth/me`, token storage in
localStorage, logout, error state, `AuthStatus` machine) is unchanged.
Student login success flows through the same path: token → `/auth/me`
bootstrap → `status='authenticated'` → `App.tsx` `/admin/me` probe decides
Admin vs Student shell. No role/approval decisions were added client-side.

## 9. 401 Error Classification (the Phase 6.15.1 fix)

`buildAuthError(response, operation)` now classifies by BACKEND ERROR CODE
first, then by operation context — never by HTTP status alone:

```text
error.code === INVALID_CREDENTIALS (any status) → invalid_credentials
  400 on /auth/login, 401 on /auth/student/login
422                                              → validation
operation=login + 401                            → invalid_credentials
  (no session exists on a login request; a 401 there can never be expiry)
operation=session + 401/404                      → session_invalid
≥500                                             → server
fetch rejection                                  → network
anything else                                    → unknown
```

Verified distinction (covered by tests): student login 401
`INVALID_CREDENTIALS` → `invalid_credentials` ("Invalid login credentials.
Please check your details and try again."); /auth/me 401 `TOKEN_EXPIRED` /
404 `USER_NOT_FOUND` → `session_invalid` ("The saved session could not be
verified…"). No string matching (`message.includes(...)`) is used anywhere.

## 10. Error Handling (user-safe, anti-enumeration)

- Invalid credentials — generic: "Invalid login credentials. Please check
  your details and try again." (reveals nothing about which identifier
  exists, which part failed, or approval state).
- Pending approval — the backend masks it as 401 `INVALID_CREDENTIALS` by
  design; the frontend shows the same generic message (no distinction,
  per the security contract).
- Validation — "Please enter a valid email and a password of at least 6
  characters." (422s only occur on contract mismatches; the form prevents
  the missing-code case locally).
- Network / server / session messages unchanged.
- No backend internals, tokens, or internal IDs are ever surfaced.

## 11. Security Considerations

- Generic auth failures preserved; anti-enumeration behavior untouched.
- Server-side role resolution (`/admin/me` probe) and approval enforcement
  untouched; the frontend decides nothing about `role`/`approved`.
- `extra="forbid"` respected: only `identifier`/`password`[/`institution_code`]
  are sent; no fake empty values.
- Token handling unchanged (Bearer header only, localStorage token only,
  never rendered/logged); no sensitive logging added.
- No institution UUIDs are ever submitted for login (code only, resolved
  server-side).

## 12. Tests Added

`frontend/src/services/auth.test.ts` (NEW, 24 tests):
- `isEmailAddress` heuristic (email / register / roll / backend edge).
- `login`: URL/method/body on `/auth/login`; 400 `INVALID_CREDENTIALS`.
- `studentLogin`: register-number, roll-number, and email bodies (email
  sends NO `institution_code`); 401→`invalid_credentials` (with exact
  generic message); 422→`validation`; 5xx→`server`.
- `authenticate`: email→existing endpoint (also with an unused code
  argument → nothing sent); register/roll → student endpoint with code;
  identifier trimming.
- `fetchCurrentUser`: bearer header; 401 `TOKEN_EXPIRED` and 404
  `USER_NOT_FOUND` → `session_invalid`.
- **Critical**: student-login 401 ≠ session 401 (classified differently,
  different messages); bare 401 on login → `invalid_credentials`;
  network failure; non-envelope 403 → `unknown`.

`frontend/src/features/auth/LoginForm.test.tsx` (+11 tests, mock made
mutable via `vi.hoisted`): identifier/password fields render; code field
hidden for email, shown+required for register number; submission payloads
for email / register number (GIT) / roll number (IMPHAL); no submission for
an academic identifier without a code; busy state disables inputs + button
("Signing in…"); duplicate submission prevented; `role="alert"` error
rendering. Existing gating + registration-navigation suites unchanged.

## 13. Test Results

- Frontend: `npm test` → **15 files, 141 tests passed** (was 127 pre-phase).
- Frontend build/typecheck: `npm run build` (`tsc -b && vite build`) → pass.
- Backend (unchanged code): `pytest tests/test_student_auth_phase_6_5.py
  tests/test_sign_in_phase_6_13_6.py` → **130 passed** (covers email /
  register / roll login, institution scoping, invalid credentials, approval
  enforcement, anti-enumeration, role behavior, 422 extra-field rejects).
- Backend regression: `pytest tests/test_security_final_validation_phase_6_13_9.py
  tests/test_rbac_phase_6_6.py` → **100 passed** (sign-in status guards,
  cross-tenant, RBAC/audit, approval lifecycle).

## 14. Files Changed

```text
frontend/src/types/auth.ts                     StudentLoginRequest; LoginResponse reuse doc
frontend/src/services/auth.ts                  studentLogin, authenticate, isEmailAddress,
                                               operation-aware classifier, generic message
frontend/src/services/auth.test.ts             NEW — 24 HTTP-boundary tests
frontend/src/features/auth/AuthProvider.tsx    login(identifier, password, institutionCode?)
frontend/src/features/auth/LoginForm.tsx       unified identifier field + conditional
                                               institution-code field
frontend/src/features/auth/LoginForm.test.tsx  +11 tests; mutable useAuth mock
PHASE_6_15_3_STUDENT_IDENTIFIER_LOGIN.md       NEW — this document
```

No backend files changed. No new dependencies, API clients, or frameworks.

## 15. Known Limitations

- `/admin/me` probe architecture retained (per phase scope): role-based shell
  selection is still probe-based; a student session spends one failed probe
  (403) on every login. Awaiting a future phase extending `/auth/me` with
  role/institution.
- Staff/faculty have no dedicated UI; they land in the student shell
  (unchanged pre-existing behavior).
- Identifier↔endpoint routing uses the same email heuristic as the backend
  (`@` + dotted domain). A value like `user@localhost` routes to
  `/auth/login` (email endpoint) where the backend would resolve it via the
  student path; such identifiers are not a supported academic format.
- The institution code field appears reactively as the identifier is typed;
  no code persistence between logins (deliberate).
- A pending-approval student cannot discover their approval state from the
  login UI (intentional backend anti-enumeration contract).

## 16. Final Verification

- [x] Student identifier login UI (email / register number / roll number)
- [x] Email login via existing `/auth/login` preserved (admin/staff/faculty)
- [x] Register-number and roll-number login via `/auth/student/login`
- [x] Institution-code handling per backend contract (required + submitted
      for academic identifiers; never sent for email)
- [x] Correct endpoint + exact request bodies (verified by tests)
- [x] AuthProvider integration (login/restore/logout unchanged semantics)
- [x] Student login success flow → `/auth/me` bootstrap → role probe shell
- [x] Student login 401 classified `invalid_credentials`; session 401/404
      classified `session_invalid`; the two verified distinct
- [x] Generic errors; no enumeration; no client-side approval/role logic
- [x] Loading state + duplicate-submission prevention
- [x] Registration navigation and forgot-password preserved (tests pass)
- [x] Change-password untouched (separate devAuth service)
- [x] Accessibility: wrapped labels, `role="alert"`, disabled-while-busy,
      `autoComplete` attributes, keyboard-operable, no unrelated redesign
- [x] Responsive: same single-column max-w-md card as before; the new field
      inherits existing breakpoints; no layout changes elsewhere
- [x] TypeScript types updated, no `any` introduced
- [x] Frontend tests 141/141 pass; build/typecheck passes
- [x] Backend authentication tests pass (no backend changes)
- [x] Git scope reviewed — only the files listed in §14





