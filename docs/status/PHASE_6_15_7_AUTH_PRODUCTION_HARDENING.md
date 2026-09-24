# Phase 6.15.7 — Authentication Production Hardening & Security Validation

**Status:** COMPLETE
**Date:** 2026-09-20
**Scope:** Production-readiness hardening of the existing authentication & registration system (no redesign, no new auth framework).
**Predecessors:** Phases 5.4, 6.13.x, 6.15.1–6.15.6 (their uncommitted work remains in the tree and is NOT attributed to this phase).

---

## 1. Objective

Perform the final production-readiness audit and hardening of the authentication and registration surface:

- Verify production/development separation (`DEV_TEST_MODE`).
- Verify dev-only endpoints cannot activate in production.
- Audit environment configuration, token storage, password handling, API requests, response minimization, CORS, logging, and error sanitization.
- Verify race conditions, multi-tab behavior, role security, tenant isolation, registration privilege injection, and schema hardening.
- Add meaningful frontend and backend security tests.
- Run dependency audit, secret scan, production build, and full regression.
- Document accepted limitations without inventing unrelated architecture (no refresh tokens, no OAuth, no new frameworks).

## 2. Authentication Architecture Reviewed

The existing architecture was reviewed end-to-end and preserved unchanged:

```
Student Registration (POST /api/v1/users/register)
        ↓  institution resolved server-side from public code
Pending Approval (approval_status='pending')
        ↓
Student Login (POST /api/v1/auth/student/login — email / register number / roll number)
   or Email Login (POST /api/v1/auth/login — admins / faculty / staff)
        ↓
GET /api/v1/auth/me → server-authoritative role + tenant (institution_id)
        ↓
Correct Shell (admin / staff / faculty / student)
        ↓
Session Restoration (saved token re-validated against /auth/me)
        ↓
Session Expiry (authenticated 401 → session-expiry event)
        ↓
Logout
```

Files inspected (source of truth = current repository):

- **Frontend:** `AuthProvider.tsx`, `LoginForm.tsx`, `RegistrationForm.tsx`, `ForgotPasswordForm.tsx`, `ChangePasswordForm.tsx`, `PasswordField.tsx`, `services/auth.ts`, `services/api.ts`, `services/adminApi.ts`, `services/devAuth.ts`, `services/registration.ts`, `services/sessionEvents.ts`, `types/auth.ts`, `types/registration.ts`, bootstrap (`main.tsx`/`App.tsx`), all auth tests.
- **Backend:** `api/auth.py`, `api/student_auth.py`, `api/users.py`, `api/registration.py`, `api/institutions.py`, `api/dev_auth.py`, `main.py` (`/auth/me`, routing, exception handlers), `core/security.py`, `core/errors.py`, `config.py`, `db/supabase.py`, `services/sign_in.py`, `services/student_auth.py`, `services/user_registration.py`, `services/tenancy.py`, `schemas/users.py`, `schemas/tenancy.py`, `schemas/student_auth.py`, plus the full backend test suite.

## 3. Production/Development Separation

`DEV_TEST_MODE` is a single backend setting (`backend/app/config.py`, pydantic-settings, **default `false`**, documented "NEVER set true in production"). It controls exactly:

| Capability | Behavior when `DEV_TEST_MODE=false` |
|---|---|
| `POST /api/v1/dev/auth/forgot-password` | 404 `NOT_FOUND` |
| `POST /api/v1/dev/auth/change-password` | 404 `NOT_FOUND` |
| `POST /api/v1/dev/auth/admin/reset-student-password` | 404 `NOT_FOUND` (route hidden — 404, never 401, even for unauthenticated callers) |
| Dev authentication convenience endpoints | Same flag; no separate mechanism |

Hardening applied in Phase 6.15.7 (`backend/app/api/dev_auth.py`):

- Every dev route resolves the flag through a shared dependency that raises **404** when the flag is off. Disabled dev routes fail **before** creating any Supabase client (test-verified: the auth/admin client factories are asserted never called).
- Route existence is hidden: an unauthenticated caller with the flag off gets 404 `NOT_FOUND`, not 401 — no signal that a dev route exists.
- When the flag is ON, normal authorization is never bypassed: the admin reset endpoint still requires the existing RBAC `admin` role (student role → 403 `FORBIDDEN`), and dev schemas use `extra="forbid"` (injected `role` / `user_id` fields → 422).
- Password validation is not bypassed: minimum-length and confirm-password rules run in dev mode exactly as elsewhere.
- No privileged authentication is issued by dev endpoints; the service-role key stays server-side and is never returned or logged; internal account information is not exposed beyond what the dev feature itself needs.
- Frontend `services/devAuth.ts` feature-detects the dev endpoints; the dev recovery UI only appears when the backend actually exposes it. In production the frontend receives 404 and renders standard production recovery messaging — the dev UI cannot be activated by a normal frontend request.

**Conclusion: development authentication functionality cannot accidentally remain enabled in production.**

## 4. Environment Configuration

Variable names audited (values deliberately not reproduced):

- **Backend (`.env.example` placeholders only):** `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (anon/public), `SUPABASE_SECRET_KEY` (service role — backend only), `SUPABASE_JWKS_URL` (JWT verification), `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `MAX_UPLOAD_SIZE_MB`, `AI_PROVIDER`, `OPENROUTER_API_KEY`, `OPENROUTER_SITE_URL`, `OPENROUTER_APP_NAME`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `EMBEDDING_BATCH_SIZE`, `DEV_TEST_MODE`.
- **JWT configuration:** verification is JWKS-based (`SUPABASE_JWKS_URL`); no symmetric JWT secret is stored in the application.
- **Frontend:** `VITE_API_BASE_URL` (public API base path, default `/api`) — the only frontend variable. Vite exposes only `VITE_*` names, and no secret is prefixed `VITE_`, so the frontend build cannot contain backend secrets by construction.
- **CORS origins:** no origin list is configured in the backend (see §11); the frontend talks to the backend same-origin through the Vite dev proxy.

Findings:

- ✅ No secrets committed: `git ls-files` shows no `.env` files tracked; `.gitignore` covers `.env`; `git check-ignore` confirms local `.env` files are ignored.
- ✅ `.env.example` files contain placeholder values only (`<your-…>`), no real credentials.
- ✅ No production or development credentials hardcoded in source (see §20 secret scan).
- ✅ Public configuration (`VITE_API_BASE_URL`, `SUPABASE_URL`, anon key) is clearly distinguishable from secret configuration (`SUPABASE_SECRET_KEY`, R2/OpenRouter keys — backend-only).

### Authentication configuration matrix

| Setting | Development | Test | Production |
|---|---|---|---|
| `DEV_TEST_MODE` | `true` (opt-in, local only) | `true` where tests exercise dev routes; default `false` | **`false` (default)** — dev routes 404, frontend recovery UI hidden |
| CORS | No CORS middleware configured — frontend uses the Vite dev proxy (`/api` → `http://localhost:8000`), so no cross-origin requests occur in dev | Same as dev (TestClient in-process) | Must be served same-origin, or a production CORS allow-list added before public deployment |
| API URL | `VITE_API_BASE_URL=/api` (Vite proxy) | `/api` default | Same-origin `/api` (default) — no secret embedded |
| Auth provider | Supabase Auth (GoTrue) via backend; no client-side Supabase SDK | Mocked at HTTP boundary | Supabase Auth (GoTrue) via backend |
| Password recovery | Dev-gated `/dev/auth/*` endpoints (flag-locked) | Flag-locked; RBAC still enforced on admin reset | **Disabled** (flag `false`; production recovery = Supabase hosted reset flow — documented limitation) |
| Debug behavior | FastAPI default error detail acceptable in dev | N/A | AppError envelope only (`code`+`message`); unhandled exceptions → FastAPI generic 500 "Internal Server Error" (no stack trace) |

No production values were invented — the table documents observed/expected behavior.

## 5. Token Storage Review

Documented Phase 5.4 tradeoff, re-verified in Phase 6.15.7 and **accepted** as an architectural limitation (no refresh-token architecture exists to replace it; cookies were NOT introduced):

- **Where:** access token only, under `localStorage` key `college-ai-chatbot.access-token` (`AuthProvider.tsx` `readStoredToken`/`storeToken`, try/catch-guarded for private browsing).
- **Which code can access it:** only the auth boundary — `AuthProvider` (store/restore/clear) and the API clients (`services/api.ts`, `services/adminApi.ts` attach it as a bearer header). No other module reads the key.
- **Logged?** No — repo-wide scan found no `console.*` statement printing the token (see §12).
- **Rendered?** Never; the token never enters React-rendered output.
- **Transport:** included **only** in the `Authorization: Bearer` header — never in URLs, query strings, or bodies.
- **Removed on logout:** yes — `clearSession` → `storeToken(null)` (test-verified).
- **Removed on session expiry:** yes — the session-expiry handler clears it (test-verified), as does a failed `/auth/me` restore.
- **Exposed to unnecessary components?** No — components consume `user`/`role`/`status` from the auth context; the raw token is not distributed beyond the API clients.

The current implementation is internally consistent; localStorage is documented as an accepted Phase 5.4 tradeoff.

## 6. Password Security

Every password input (Login, Registration, Forgot password, Change password) was audited. Verified:

- **Never logged:** repo-wide frontend scan found no `console.*` printing passwords; backend auth paths never log credentials (`dev_auth.py` explicitly documents "Passwords, tokens, and other secrets are never logged").
- **Never persisted:** no `localStorage`/`sessionStorage` write of passwords anywhere (scan-verified; Phase 6.15.5/6.15.6 storage-audit tests still pass).
- **Never in URLs/query parameters:** all password-bearing requests (`/auth/login`, `/auth/student/login`, `/users/register`, dev recovery endpoints) send passwords **only in the POST request body**.
- **Never in API error messages:** backend errors return the AppError envelope with fixed, user-safe codes (`INVALID_CREDENTIALS`, `VALIDATION_ERROR`); Supabase error text is never echoed with credential material.
- **Cleared from state:** Registration, Forgot-password reset, and Change-password forms drop plaintext password state once the request settles (established in Phase 6.15.6, re-verified here).
- **Shared `PasswordField`:** renders an `<input type="password">` with a visibility toggle only; it never stores, logs, or exports the value beyond the controlled `onChange` path.

## 7. API Security

Request-contract audit (working contracts preserved; no changes made):

| Request | Passwords | Token |
|---|---|---|
| `POST /auth/login` | body only | — |
| `POST /auth/student/login` | body only | — |
| `POST /auth/signup` | body only | — |
| `POST /users/register` | body only | — |
| `GET /institutions/lookup` | — | — (intentionally public) |
| `GET /auth/me` | — | `Authorization: Bearer` header only |
| Dev forgot/change password | body only | — |
| Authenticated app requests (`api.ts`, `adminApi.ts`) | — | `Authorization: Bearer` header only |

- Credentials never appear in URLs or query strings (only the public `code` query on `/institutions/lookup`).
- Tokens are attached only by the API clients as bearer headers; no request embeds a token in the body or query.
- Logout is a client-side session clear (no backend revoke endpoint exists in the architecture); no token-bearing logout request exists to audit.

## 8. Institution Lookup Security

`GET /api/v1/institutions/lookup` re-verified:

- ✅ Public access is **intentional and documented** (unauthenticated prospective student knows only the public code).
- ✅ Only **ACTIVE** institutions resolve; pending/rejected/inactive institutions return `404 INSTITUTION_NOT_FOUND` (no status leak distinguishing "inactive" from "unknown").
- ✅ Response projection is deliberately minimal: `InstitutionLookupResponse` = `institution_id`, `code`, `name` — never contact/location details, organization linkage, join codes, or status machinery.
- ✅ No student data and no internal configuration exposed.
- ✅ Codes are normalized server-side (case-insensitive, blank-rejected); there is no wildcard/prefix/contains querying — a code either matches exactly or 404s, so broad enumeration-style querying yields nothing beyond brute-forcing individual codes.
- ✅ The registration endpoint re-resolves and re-validates the institution server-side (the lookup is advisory only).

## 9. Registration Security

`POST /users/register` re-verified against abuse risks:

- **Validation:** strict Pydantic schemas, `extra="forbid"`, password ≥ 6 chars, email format enforced, names not blank.
- **Duplicate handling:** typed 409 codes (`EMAIL_ALREADY_REGISTERED`, `STUDENT_ALREADY_REGISTERED`, `REGISTER_NUMBER_ALREADY_REGISTERED`, `ROLL_NUMBER_ALREADY_REGISTERED`).
- **Institution scoping:** institution resolved SERVER-side from the public code; must be ACTIVE; internal IDs are never accepted from the client.
- **Approval defaults:** students always start `approval_status='pending'`; no token is issued at registration.
- **Password validation:** mirrors the backend minimum both client- and server-side.
- **Error handling:** stable AppError envelope; no internals leaked.
- **Rate limiting / request size limits:** **not present** in the current stack (no middleware, no dependencies for it). Documented as a **production limitation** (§26) rather than inventing unrelated infrastructure.

## 10. Authentication Abuse Controls

- **Brute force / rate limiting:** no rate limiting exists in the backend stack (no middleware or dependency for it). Documented as a **production limitation** (§26) — not silently invented.
- **Anti-enumeration:** verified. `POST /auth/login` normalizes **every** post-credential denial (missing `public.users` row, inactive status, unapproved/lifecycle-inactive student, inactive institution) to the identical `400 INVALID_CREDENTIALS` / "Invalid login credentials" contract — byte-for-byte indistinguishable from a wrong password. `POST /auth/student/login` likewise normalizes unknown identifier vs wrong password vs pending/inactive account to a uniform `401 INVALID_CREDENTIALS` family, so the client cannot enumerate accounts. Test-covered.
- **Institution scoping:** academic-identifier logins require the institution code; resolution is server-side and institution-scoped (Phase 6.2).
- **No account lockout:** none exists; none introduced (no explicit backend design for it).
- **Suspicious repeated requests:** no detection mechanism exists today — same production limitation as rate limiting.

## 11. CORS Review

- The backend **does not configure `CORSMiddleware` at all** (`main.py` has no CORS block; no `allow_origins=["*"]` anywhere).
- The architecture is **same-origin by design**: the frontend talks to the backend through the Vite dev proxy in development, and deployment is expected to serve the API and frontend from the same origin (or a reverse proxy), so no credentialed cross-origin surface exists.
- Because there is no CORS surface, there are no wildcard origins, no `Access-Control-Allow-Credentials` risks, and no origin allow-list to maintain. If a future deployment splits origins, a strict explicit-origin CORS configuration must be added at that time.
- ✅ Avoided-by-construction: `allow_origins=["*"]` with credentials.

## 12. Logging Review

- **Backend:** `api/auth.py` defines a module logger but logs **nothing sensitive** — no logging statements print passwords, tokens, JWTs, authorization headers, recovery tokens, or secrets anywhere in the auth surface (repo-wide pattern scan verified). Safe logging content (operation type, failure classification, HTTP status) does not include credential material.
- **Frontend:** repo-wide scan found **no** `console.log/warn/error/debug/info` statements printing passwords, tokens, or `Authorization` values (the only `console.*` hits in the tree are inside vendored documentation HTML, not application code).
- **dev_auth.py:** explicitly documented and verified — passwords, tokens, and secrets are never logged; error messages are safe fallbacks, never rendered secrets.

## 13. Error Sanitization

- **`AppError` handler** (`core/errors.py`): responses contain only `{ "error": { "code", "message" } }` — no stack traces, no exception class names, no file paths, no environment values.
- **`RequestValidationError` handler** (`main.py`): normalized to HTTP 422 `VALIDATION_ERROR` in the same envelope (framework `detail` payloads are not leaked to clients).
- **Unhandled exceptions:** FastAPI's default behavior returns a bare `500 Internal Server Error` with no stack trace or Python internals exposed to the client (the traceback stays in server logs only). Auth endpoints additionally catch `AuthApiError` and re-raise as typed `AppError`s, so upstream Supabase exceptions are never propagated raw — and the login status guard collapses all denials to the fixed `INVALID_CREDENTIALS` contract.
- **Frontend:** receives stable typed error codes (`invalid_credentials`, `validation`, `institution_not_found`, etc.) and maps them to fixed user-safe messages; raw server text is never rendered as-is.

## 14. Race Conditions

Phase 6.15.7 hardened `AuthProvider` with **synchronous race guards** (`sessionTokenRef` + `sessionGenerationRef`):

- **Login + browser refresh:** the saved token is re-validated against `/auth/me` on restore; a token saved by a login whose continuation is interrupted cannot restore a partially-initialized session.
- **Login + immediate logout:** every session-changing operation (logout, expiry, newer login) bumps the generation counter synchronously; an in-flight login/restore that settles afterwards is **discarded**, so a stale response can never resurrect a signed-out session.
- **Session restore + API 401:** a failed `/auth/me` clears the saved token and returns to login with the fixed expiry message.
- **Session expiry + pending API request:** expiry notifications are now **token-scoped** (`notifySessionExpired(token)` — `sessionEvents.ts`): a stale 401 belonging to a token the provider no longer holds (e.g. the user already signed in again) is **ignored**, so a stale 401 can never clear a fresh session. Notifications without a token keep the previous behavior.
- The expiry handler itself is idempotent (state-machine guarded — it only acts from the `authenticated` state), so concurrent 401s cannot loop, double-redirect, or double-error.

### 14.1 Session-Expiry Race (401 ×3)

Verified: three concurrent authenticated requests all receiving 401 publish three expiry notifications, and the provider's handler is **idempotent**:

- The first notification transitions `authenticated → unauthenticated` and clears the session once.
- Subsequent notifications find the state machine already out of `authenticated` (or the token already replaced/scoped out) and are **no-ops**.
- No logout loops, no repeated redirects, no repeated error banners, no React state errors (setState-in-render style hazards are avoided because the handler is a stable callback registered once via `useEffect`).
- Token-scoping (§14) additionally prevents an old-token 401 from clobbering a newer session.

## 15. Multi-Tab Behavior

Cross-tab synchronization **is implemented** (Phase 6.15.7 addition, `AuthProvider.tsx`): a `window` `storage` event listener reacts to the `college-ai-chatbot.access-token` key changing in `localStorage`.

- **Tab A logs out → Tab B:** the storage event fires (token removed), Tab B's provider re-validates/clears its session → Tab B drops to the login state. Test-verified ("another tab signing out clears this tab").
- **Tab A logs in → Tab B:** the storage event carries the new token; Tab B restores/validates the session against `/auth/me` and follows the server-authoritative role. Test-verified ("another tab logging in syncs this tab").
- **Degraded mode (storage unavailable):** sessions stay in memory per tab — no cross-tab sync is possible; each tab is independent. Documented behavior, not a security issue.

## 16. Role Security

- `role` is **always server-authoritative**: resolved by the backend from the verified JWT → `public.users` → `user_roles` → `roles` chain and returned by `/auth/me` as `role: AuthRole | null`. The frontend never derives a role from email, identifier, or localStorage.
- **Manipulation attempts reviewed:**
  - *localStorage tampering:* only the raw token lives there; forging or editing it simply fails JWT verification (`401`), never grants a role.
  - *React state:* `user`/`role` are set exclusively from `/auth/me` responses; no setter is exported.
  - *Request payloads:* login/registration schemas are `extra="forbid"`; `role` is unrepresentable (`registration_type` is a Literal of `student|faculty|staff`; "admin" → 422).
  - *Authentication identifiers:* student login identifiers resolve server-side within the institution; they cannot select a role.
- Unknown/unsupported roles resolve to `null` → "no privileged UI" (fail-safe). **No privilege escalation path found.**

## 17. Tenant Security

- Tenant context (`institution_id`) is resolved **server-side** from the verified JWT, never from client input.
- `scope_tenant` (core/security.py): a tenant-bound user requesting another institution's id → `403`; platform-level users pass through by explicit design.
- `assert_tenant_object`: fetched/created rows are checked against the user's tenant; cross-tenant access raises `403`.
- `institution_code` / `institution_id` injection from the frontend is rejected: public payloads carry only the public code, resolved server-side; internal IDs in auth/registration schemas are `extra="forbid"`-blocked.
- Student authentication, student academic data, and institution-scoped roles all remain institution-scoped (existing Phase 6.2/6.13 services unchanged). **No cross-tenant escalation found.**

## 18. Schema Hardening

All authentication-related request schemas enforce `model_config = ConfigDict(extra="forbid")`:

| Schema | File | Effect |
|---|---|---|
| `AuthRequest` (login/signup) | `app/api/auth.py` | Rejects `role`, `scope_*`, `institution_id`, `status`, etc. |
| `StudentLoginRequest` | `app/schemas/student_auth.py` | Only `identifier`, `password`, `institution_code` |
| `UserRegistrationRequest` | `app/schemas/users.py` | `registration_type` Literal `student|faculty|staff` — `admin` unrepresentable |
| `InstitutionRegistrationRequest` / `ApprovalDecisionRequest` | `app/schemas/tenancy.py` | No decision/status spoofing |
| Dev recovery schemas | `app/api/dev_auth.py` | Strict even in dev mode (tested with flag ON) |

Verified with a payload injecting `{"role": "admin", "approval_status": "approved", "institution_id": "<other-id>"}` against registration, login, and student-login endpoints: every extra field is rejected with 422 `VALIDATION_ERROR` before any service call (test-verified in the hardening suite). Response schemas (`UserRegistrationResponse`, `InstitutionLookupResponse`, `/auth/me` projection) are additive allow-lists — nothing beyond the declared fields is serialized. Schema validation was not weakened.

### Registration privilege injection (schema-level review + tests of `POST /users/register`)

| Injection attempt | Result |
|---|---|
| `registration_type: "admin"` | 422 (Literal `student|faculty|staff` — unrepresentable) |
| Extra field `role`, `approval_status`, `institution_id`, `scope_*` | 422 `VALIDATION_ERROR` (`extra="forbid"`) |
| Setting another student's institution | Impossible — no institution id accepted; institution is resolved server-side from the public code |
| Bypassing approval | Impossible — approval status is server-set (`pending`); no token issued at registration; `/auth/me` role comes only from server-side user_roles |
| Receiving a privileged token | Registration returns **no token**; approval is a separate admin workflow |

No role is assigned at registration time; roles are written server-side during approval only.

## 19. Dependency Audit

**Frontend (`npm audit`):** `found 0 vulnerabilities`. No upgrades required, no dependency churn.

**Backend (uv-managed `pyproject.toml`):** dependencies are current, actively maintained majors (`fastapi>=0.141.1`, `pyjwt[crypto]>=2.13.0`, `supabase>=2.31.0`, `cryptography>=44.0.0`, `pydantic-settings>=2.9.1`, `httpx>=0.28.1`, `boto3>=1.38.0`, etc.). No known CVE affecting the authentication surface; no package was upgraded in this phase (per phase instructions). JWT verification uses JWKS (`SUPABASE_JWKS_URL`) via PyJWT — no shared-secret HMAC handling in application code.

## 20. Secret Scan

Static patterns scanned across tracked repository files and the production build output: API-key shapes, JWT secret literals, Supabase service-role keys, password literals, private tokens, and hardcoded `Authorization` headers.

**Result: no committed secrets, no remediation required.**

- `.env` files are local-only and confirmed ignored by `.gitignore` (`git check-ignore` verified); only `.env.example` placeholders (`<your-...>`) are tracked.
- The Supabase service-role key is referenced ONLY by variable name (`SUPABASE_SECRET_KEY`) in `app/db/supabase.py` / `app/config.py`; it never leaves the backend and never reaches the frontend.
- Frontend environment usage is limited to `VITE_API_BASE_URL` (public, non-secret). No `VITE_`-prefixed secret exists.
- **Build-output scan:** `frontend/dist` was searched for the same patterns — no secrets; only the public API base URL string is embedded, as expected.


## 21. Frontend Security Tests

Meaningful new/updated tests added in Phase 6.15.7 (no duplication of existing coverage):

| Test | File | Assurance |
|---|---|---|
| Stale 401 notification for a replaced token is ignored (does not clear a fresh session) | `AuthProvider.test.tsx` | Session-expiry race |
| Token-scoped `notifySessionExpired` semantics (named-token vs unnamed) | `AuthProvider.test.tsx` | Expiry idempotency |
| Cross-tab logout via `storage` event clears this tab's session | `AuthProvider.test.tsx` | Multi-tab sync |
| Cross-tab login via `storage` event syncs this tab | `AuthProvider.test.tsx` | Multi-tab sync |
| Login + immediate logout: stale login result cannot restore a session | `AuthProvider.test.tsx` | Race guard |

Pre-existing suites already cover the remainder and all pass unchanged: password never persisted / token cleared on logout & expiry (6.15.5 storage-audit tests), session-restore + 401 (6.15.4), registration payload contains no privileged fields (RegistrationForm payload assertion), token never rendered, safe error rendering, `PasswordField` behavior, ForgotPasswordForm dev-disabled handling. Duplicating these would add no assurance.

## 22. Backend Security Tests

New file: `backend/tests/test_auth_production_hardening_phase_6_15_7.py` — **42 tests, all passing**:

- Dev endpoint gating: flag OFF → every `/dev/auth/*` route returns 404 `NOT_FOUND` (route hidden, not 401 — existence concealed from unauthenticated callers).
- Disabled dev routes never construct a Supabase client (fail-closed; patched clients assert not called).
- Flag ON → strict schemas (`extra="forbid"`) still reject unexpected fields with 422.
- Flag ON → the admin reset still enforces real RBAC (non-admin role → 403 `FORBIDDEN`); the dev flag never replaces the authorization boundary.
- Registration privilege injection: `role`/`approval_status`/`institution_id`/`scope_*` extras → 422; `registration_type: "admin"` → 422.
- Anti-enumeration: unknown account, wrong password, and pending-approval normalize to the identical locked failure contract.
- Institution lookup projection: response contains only `institution_id`/`code`/`name`.
- Error sanitization: AppError envelope contains only `code`/`message`; no exception names, SQL, paths, or env values in responses.
- Sensitive-field exclusion: login/register/`/auth/me` responses never contain passwords, hashes, service-role data, or internal role metadata.

Full existing security suite re-run green (§23). No pre-existing security test was weakened.

## 23. Full Regression

**Backend:** `python -m pytest tests -q` → **1658 passed, 15 skipped, 2 warnings** (skips are pre-existing environment-conditional skips — live-Supabase/service-role tests — unchanged from prior phases; warnings are Starlette `TestClient` deprecations, also pre-existing).

**Frontend:** `npm test` → **194/194 passed** (all suites, including the 6.15.7 additions).

**Production build:** `npm run build` → **passes**; TypeScript compile clean; one pre-existing CSS warning only. No build artifacts committed (`dist/` is git-ignored).

## 24. Issues Found

1. **Session-expiry race (stale 401 vs fresh session):** a 401 notification for a request carrying an OLD token could clear a NEWLY established session (login → rapid expiry of the prior request). Fixed (§ Fixes Applied #1, #2).
2. **Async login/restore vs logout race:** an in-flight `/auth/me` or login result settling AFTER a logout could restore an already-signed-out state. Fixed (§ Fixes Applied #3).
3. **Multi-tab desync:** Tab B stayed authenticated after Tab A logged out (localStorage is per-tab state in React). Fixed (§ Fixes Applied #4).
4. **Dev recovery route-contract inconsistencies:** `/dev/auth/*` gating was audited and tightened — routes are now unconditionally hidden (404 `NOT_FOUND`, never 401/403 for unauthenticated callers) when `DEV_TEST_MODE` is false, and no Supabase client is constructed on a disabled route.
5. **Non-issues confirmed safe:** no XSS sinks (`dangerouslySetInnerHTML`/`innerHTML`/`eval`/`new Function`/`document.write` absent from `frontend/src`); passwords only in POST bodies (never URLs/query/storage/logs); tokens only in `Authorization` headers and the single documented localStorage key; logs contain no credentials (the one backend `logger` in `auth.py` logs operation/status only); CORS has no wildcard (`allow_origins=["*"]` is absent); registration grants no token/role; tenant scoping is enforced server-side (`scope_tenant`/`assert_tenant_object` + institution-scoped identifier resolution).

## 25. Fixes Applied

1. **`frontend/src/services/sessionEvents.ts`** — `notifySessionExpired` now accepts the token the failed request carried (`notifySessionExpired(token?: string | null)`), so a stale notification can be identified.
2. **`frontend/src/services/api.ts` + `frontend/src/services/adminApi.ts`** — 401-on-authenticated-request paths publish the failing request's token with the expiry notification.
3. **`frontend/src/features/auth/AuthProvider.tsx`** —
   - Race guards: `sessionTokenRef` (mirror of the live token, written synchronously) and `sessionGenerationRef` (invalidation counter bumped on every logout/expiry/login) so stale async results are discarded.
   - Token-scoped expiry handling: a 401 notification naming a token the provider no longer holds is ignored; unnamed notifications keep prior behavior. Expiry handling remains idempotent (state-machine guarded, multiple 401s produce one clean transition, no loops/redirect storms).
   - Cross-tab sync: `storage` event listener reacts to the token key changing in `localStorage` (another tab's logout clears this tab; another tab's login syncs this tab).
4. **`backend/app/api/dev_auth.py`** — gating tightened to fail-closed 404 `NOT_FOUND` (existence hidden), zero auth-infrastructure construction when disabled, strict schemas and preserved RBAC when enabled; explicit flag-state logging-safe documentation.
5. **`backend/app/config.py`** — `DEV_TEST_MODE` documented as development-only with default `false` and a warning comment; `.env.example` documents the flag's meaning and danger.

## 26. Accepted Limitations

1. **Access token in `localStorage`** — documented Phase 5.4 architectural tradeoff (no refresh-token architecture exists to replace it). Mitigations in place: token sent only in `Authorization` headers, cleared on logout/expiry/cross-tab logout, never logged/rendered; no XSS sinks exist that could reach it. Accepted.
2. **No rate limiting / brute-force throttling** — the backend has no rate-limit infrastructure (no such middleware/dependency in the stack), and inventing one is explicitly out of scope. Production deployment should place a reverse proxy/gateway (e.g. nginx, Cloudflare) in front of `/auth/*` for throttling. Documented as a production limitation.
3. **No account lockout** — deliberately not introduced (requires an explicit backend design per phase instructions).
4. **Password recovery in production** — dev-gated recovery endpoints are disabled in production; the intended production recovery path is Supabase Auth's hosted email reset flow, not yet wired into the UI. Documented gap.
5. **CORS in production** — no CORS middleware exists (dev relies on the Vite proxy). Production must serve frontend+API same-origin or add an explicit allow-list before public deployment. Documented gap, not silently left to chance.
6. **`/auth/signup` legacy endpoint** returns Supabase's own error messages (`AUTH_ERROR`) rather than the fully normalized anti-enumeration contract used by `/auth/login` and student login; it is not part of the frontend auth surface (the frontend uses `/auth/login` and `/auth/student/login` only). Left unchanged to avoid altering working contracts.

## 27. Production Readiness Notes

- Dev/prod separation is fail-closed and test-enforced: `DEV_TEST_MODE=false` (the default) hides every dev route and disables the frontend recovery UI; enabled dev routes never bypass RBAC, password validation, or schema strictness.
- Role and tenant are ALWAYS server-authoritative: role from the verified-JWT → `public.users` → `user_roles` → `roles` chain; tenant from server-side records (`scope_tenant` rejects cross-tenant requests with 403). No client field can influence either.
- Registration cannot yield access: no token issued, `approval_status` forced to `pending`, role assigned only during admin approval, institution resolved server-side from the public code.
- Errors are stable and typed end-to-end (`{"error": {"code", "message"}}`), sanitized, and anti-enumeration-normalized on all authentication failures.
- Logging contains no credentials or tokens anywhere in the auth surface.
- Secrets live only in untracked `.env`; the production build embeds no secrets.
- Pre-production checklist: (a) decide same-origin serving vs CORS allow-list; (b) add gateway-level rate limiting for auth endpoints; (c) wire Supabase hosted password-reset for production recovery.

## 28. Final Verification

- Definition-of-Do checklist: **all items satisfied** (dev/prod separation audited and test-enforced; dev endpoints verified safe; environment/token/password/API/lookup/registration/abuse/CORS/logging/error/race/multi-tab/role/tenant/schema reviews complete; frontend + backend security tests pass; dependency audit and secret scan clean; production build passes; full regression passes; this document created; git scope reviewed; no unrelated changes introduced).
- Backend: **1658 passed, 15 skipped** (pre-existing skips) — `python -m pytest tests -q`.
- Frontend: **194/194 passed** — `npm test`; **build passes** — `npm run build`.
- Secret scan of tracked files and `frontend/dist`: clean.
- No working request contract, schema, or authorization rule was changed.
- Phase 6.15.7 is **COMPLETE**. Phase 6.15.8 is not started (per instructions).

