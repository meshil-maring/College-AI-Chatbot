# Phase 6.15.8 — Authentication Deployment & Operational Readiness

## 1. Phase Objective

Prepare the completed Phase 6.15 authentication system for a realistic production
deployment and operational environment — WITHOUT redesigning authentication.

Phase 6.15.1–6.15.7 established the authentication UI and contracts, student
registration, identifier login, institution resolution, server-authoritative role
resolution, session lifecycle, recovery behavior, E2E validation, production
security hardening, race-condition protection, multi-tab synchronization,
development/production separation, and dependency/secret auditing.

Phase 6.15.8 verifies that the existing system can be **configured, deployed,
observed, tested, and operated safely** across development, testing, and
production environments. The authentication architecture itself is treated as
locked; the only code changes are deployment-readiness additions (startup
configuration validation, configuration tests, a build-artifact security scan)
that do not alter any authentication contract.

## 2. Existing Authentication Architecture

The locked architecture (unchanged in this phase):

```text
Frontend
   ↓
Authentication UI
   ↓
AuthProvider
   ↓
API client  (VITE_API_BASE_URL, default "/api")
   ↓
FastAPI  (no CORS middleware — same-origin by design)
   ↓
Supabase Auth / GoTrue
   ↓
Server-side user resolution  (JWT → public.users via SUPABASE_JWKS_URL)
   ↓
Tenant resolution  (students.institution_id, server-side)
   ↓
Server-authoritative role resolution  (user_roles → roles)
   ↓
Authenticated application shell
```

Authentication methods (frozen):

- **Email:** `email + password`
- **Student academic identifier:** `register number + password + institution code`,
  or `university roll number + password + institution code`, or `email + password`,
  depending on the login flow.

Registration flow (frozen):

```text
institution code → institution lookup → student registration
→ pending approval → admin/staff approval → student login
```

JWT verification is JWKS-based (`SUPABASE_JWKS_URL`); no symmetric JWT secret is
stored in the application. Tokens live only in the single documented
localStorage key and the `Authorization` header. No part of this was modified.

## 3. Environment Variables

### Backend (`backend/.env.example`, loaded by `app/config.py` relative to CWD)

| Variable | Purpose |
|---|---|
| `ENVIRONMENT` | Deployment environment name. Local allow-list: `development`, `dev`, `local`, `test`, `testing`. Anything else (production/prod/staging/typo/empty) is a deployment environment: stricter validation applies. |
| `DEBUG` | Gates chat timing diagnostics metadata. Must be `false` in any deployment. |
| `SUPABASE_URL` | Supabase project URL. |
| `SUPABASE_PUBLISHABLE_KEY` | Public anon/publishable key (used only server-side; the frontend has NO client-side Supabase SDK). |
| `SUPABASE_SECRET_KEY` | Service-role key — bypasses RLS. Backend-only. |
| `SUPABASE_JWKS_URL` | JWKS endpoint used to verify Supabase JWTs. |
| `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` | Cloudflare R2 storage credentials (documents). |
| `MAX_UPLOAD_SIZE_MB` | Upload size limit (default 50). |
| `AI_PROVIDER` | Generation provider (default `openrouter`). |
| `OPENROUTER_API_KEY` | OpenRouter credential. |
| `OPENROUTER_SITE_URL`, `OPENROUTER_APP_NAME` | Optional OpenRouter attribution. |
| `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `EMBEDDING_BATCH_SIZE` | Model configuration (non-secret). |
| `DEV_TEST_MODE` | **Development/testing ONLY.** Gates `/api/v1/dev/auth/*`. Default `false`. |

### Frontend (`frontend/.env.example`, Vite `VITE_*` exposure)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | The ONLY frontend variable. Public API base path, default `/api` (same-origin). |

No CORS configuration variables exist — the backend configures no CORS middleware.
There are no Docker/deployment manifests and no CI configuration in the repository;
deployment topology is documented in Section 11 and the checklist in Section 25.

## 4. Configuration Matrix

| Variable | Backend/Frontend | Dev | Test | Production | Secret? | Required? |
|---|---|---|---|---|---|---|
| `SUPABASE_URL` | Backend | required | required | required — startup fails if missing | No (URL, treat as confidential) | Yes |
| `SUPABASE_PUBLISHABLE_KEY` | Backend | required | required | required — startup fails if missing | Public-by-design (never shipped to browser anyway) | Yes |
| `SUPABASE_SECRET_KEY` | Backend | required | required | required — startup fails if missing | **SECRET — backend only** | Yes |
| `SUPABASE_JWKS_URL` | Backend | required | required | required — startup fails if missing | No | Yes |
| `DEV_TEST_MODE` | Backend | `true` opt-in (local envs only) | `true` only where dev routes are exercised; default `false` | **`false` (default; `true` refuses to start)** | No | No (default false) |
| `ENVIRONMENT` | Backend | `development` (default) | `test`/`testing` as needed | `production`/`prod` (anything outside the local allow-list) | No | No (default `development`) |
| `DEBUG` | Backend | `true` (default) | either | **`false` — startup fails if `true`** | No | No (default true for local dev) |
| `R2_ENDPOINT_URL` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` | Backend | required for document features | mocked | required for document features | `R2_SECRET_ACCESS_KEY`/`R2_ACCESS_KEY_ID` **SECRET — backend only** | Only for document features; not required for authentication startup |
| `OPENROUTER_API_KEY` | Backend | required for chat | mocked | required for chat | **SECRET — backend only** | Only for generation features; not required for authentication startup |
| `OPENROUTER_SITE_URL` / `OPENROUTER_APP_NAME` / `OPENROUTER_BASE_URL` / `OPENROUTER_MODEL` / `EMBEDDING_*` | Backend | optional/defaults | defaults | defaults | No | No |
| `MAX_UPLOAD_SIZE_MB` | Backend | default 50 | default | default | No | No |
| `VITE_API_BASE_URL` | Frontend | `/api` (Vite dev proxy → `localhost:8000`) | `/api` default | `/api` (same-origin) or explicit public API origin | No — public | No (default `/api`) |
| CORS | Backend | none configured (Vite proxy) | none | **none configured — same-origin required** | n/a | n/a |

R2/OpenRouter variables are deliberately NOT part of the authentication startup
gate (they are feature-scoped, not auth-scoped): authentication and session
endpoints require only the four Supabase variables plus the safe flags.

## 5. Secret Classification

**Public (may safely reach the browser):**

- `VITE_API_BASE_URL` — the only variable compiled into the frontend bundle.

**Backend-only (must NEVER be exposed to frontend JavaScript):**

- `SUPABASE_SECRET_KEY` (service role)
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
- `OPENROUTER_API_KEY`

**Sensitive configuration (supply through deployment secrets/configuration):**

- All backend variables above. `SUPABASE_PUBLISHABLE_KEY` is public-by-design but
  is still supplied server-side only, because the frontend has no Supabase SDK.

**Verification results:**

- Secrets are not committed: live-value scan of all 384 tracked files against the
  5 real credential values in the local (untracked) `backend/.env` → **0 hits**
  (the only long-value matches were the public model name `qwen/qwen3-embedding-8b`,
  which is not a secret). `git check-ignore` confirms `.env` is ignored in root,
  backend, and frontend.
- Secrets are not embedded into Vite bundles: `VITE_API_BASE_URL` is the only
  `VITE_*` variable referenced in `frontend/src` (enforced by
  `frontend/src/config/env.test.ts`), and no secret is `VITE_`-prefixed.
- Secrets are not present in `.env.example`: placeholder values only (`<your-…>`),
  enforced by `scripts/verify_frontend_build_security.mjs`.
- Secrets are not present in documentation: this document names variables only.
- Secrets are not printed during startup: `app/core/startup_validation.py` emits
  only `✓ SUPABASE_SECRET_KEY (configured (value withheld))`-style lines;
  `test_check_details_never_contain_secret_values` enforces value-free output even
  with realistic-looking fake credentials in Settings.
- Secrets are not returned by health endpoints: `/health` returns only
  `{status, service, environment}` (asserted by test).

## 6. Frontend Production Configuration

The frontend determines the API base URL in exactly one way, in every service
module (`api.ts`, `auth.ts`, `registration.ts`, `adminApi.ts`, `devAuth.ts`):

```ts
const API_BASE_URL: string = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/+$/, '')
```

- **Development:** `VITE_API_BASE_URL=/api` (default) + Vite dev proxy
  (`frontend/vite.config.ts`): browser → `http://localhost:5173/api/…` →
  `http://localhost:8000/api/…`. No CORS changes needed.
- **Test:** Vitest mocks `fetch` at the boundary; the default `/api` base applies.
- **Production:** the same default `/api` produces same-origin requests against
  whatever origin serves the static bundle. The fallback is a relative path —
  never `localhost` — so production cannot accidentally point at a development
  backend unless an operator explicitly sets `VITE_API_BASE_URL` to one, and
  `scripts/verify_frontend_build_security.mjs` fails if the built bundle contains
  any `localhost`/`127.0.0.1` reference.

A production build (`npm run build`) was performed and all generated assets in
`frontend/dist` (JS/CSS/HTML/maps) were scanned for API secrets, Supabase
service-role keys, database credentials, OpenRouter keys, JWTs, passwords, and
internal deployment secrets: **none found**; only the public `/api` base path is
embedded, as intended. A cross-origin frontend could set
`VITE_API_BASE_URL=https://api.example.com` at build time — still public
information, but see Section 11 for the CORS consequence.

## 7. Backend Production Configuration

`backend/app/config.py` + the new `backend/app/core/startup_validation.py`
(wired at import time in `backend/app/main.py`):

- **Production defaults are safe.** `DEV_TEST_MODE` defaults to `false`;
  `ENVIRONMENT` defaults to `development` — but the *permissive* treatment is the
  explicit local allow-list, so a deployment with a missing/typo'd `ENVIRONMENT`
  is treated as a deployment environment and gets stricter validation, not looser.
- **`DEV_TEST_MODE=false` by default** — and `Settings` itself refuses to exist
  with `DEV_TEST_MODE=true` outside the local allow-list (Phase 6.15.7 guard,
  re-verified by Phase 6.15.8 tests).
- **Debug mode disabled in production:** `DEBUG=true` (which would expose chat
  timing diagnostics in response metadata) now **stops startup** outside the local
  allow-list. Previously `debug: bool = True` was unconditional and only affected
  dev chat diagnostics — now it is explicitly enforced in deployments.
- **Development authentication endpoints cannot accidentally become enabled:**
  the config guard + router-level 404 gate + the new startup check all fail
  closed. With the flag off, every `/api/v1/dev/auth/*` route answers
  `404 NOT_FOUND` and never constructs a Supabase client (asserted with a patched
  `app.db.supabase.create_client`).
- **Missing required production variables fail clearly:** outside local
  environments, missing/empty `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`,
  `SUPABASE_SECRET_KEY`, or `SUPABASE_JWKS_URL` raises `RuntimeError` at startup
  naming the missing variable, e.g. `SUPABASE_URL is missing or empty`. Invalid
  configuration fails during startup rather than producing confusing runtime
  authentication failures.
- **Secrets are not logged:** validation details are static sentences or
  `configured (value withheld)`; error messages name variables, never values.
- The startup validation performs **no network I/O** and constructs **no Supabase
  clients**.

In local development/testing, failed checks log a warning and startup continues,
so a partially configured laptop stays usable while the problem stays visible.

## 8. DEV_TEST_MODE

Verified state (shipped code + new tests in
`backend/tests/test_config_phase_6_15_8.py` and the existing Phase 6.15.7 suite):

| Endpoint (flag OFF = production) | Behavior |
|---|---|
| `POST /api/v1/dev/auth/forgot-password` | `404 NOT_FOUND` |
| `POST /api/v1/dev/auth/change-password` | `404 NOT_FOUND` |
| `POST /api/v1/dev/auth/admin/reset-student-password` | `404 NOT_FOUND` (route hidden — never 401, even unauthenticated) |
| `GET /api/v1/dev/auth/status` | Returns `{dev_test_mode: false}` (flag report only; frontend fails closed on any error) |

Production expectation: `DEV_TEST_MODE=false`, and every `/dev/auth/*` route
remains inaccessible. Confirmed disabled routes return `404` **and** never
instantiate a privileged Supabase client (patched `create_client.assert_not_called()`).

Additional guard: `Settings` refuses to construct with `DEV_TEST_MODE=true` and a
non-local `ENVIRONMENT` — a misconfigured deployment cannot even start with the
dev endpoints enabled. The frontend `devAuth.ts` module also fails closed: on any
network/HTTP error it reports the feature as disabled, so the dev recovery UI can
never appear in production.

## 9. Supabase Configuration

Manual Supabase project configuration required for deployment (no Supabase
production settings were changed during this phase — documentation only):

- Supabase project URL → `SUPABASE_URL`
- Public/anon (publishable) key → `SUPABASE_PUBLISHABLE_KEY` (backend-only usage)
- Service-role (secret) key → `SUPABASE_SECRET_KEY` (**backend only, never frontend**)
- JWKS endpoint → `SUPABASE_JWKS_URL` (normally
  `https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`)
- **Authentication enabled** for the project (Auth → Providers)
- **Email/password authentication enabled** (Email provider on; confirm sign-up
  policy matches the registration flow's pending-approval model)
- **Site URL / redirect configuration** for the hosted password-recovery flow
  (Section 10): the Supabase Auth "Site URL" must be the production origin, and
  the recovery redirect allow-list (`Additional Redirect URLs`) must include the
  exact production recovery route(s) the frontend uses.
- RLS policies on `public.*` tables remain as established by prior phases (the
  backend uses the service-role key; tenant isolation is enforced server-side).

## 10. Password Recovery

The project relies on the **Supabase hosted password-reset mechanism** for
production recovery. No custom email service, no custom recovery-token system,
and no replacement of Supabase recovery exists or was added.

Expected production flow:

```text
Forgot Password (frontend UI)
      ↓
Supabase hosted recovery flow (backend → GoTrue)
      ↓
email
      ↓
reset link (hosted by Supabase / redirect to production origin)
      ↓
Supabase recovery session
      ↓
password update (Supabase Auth)
```

**Development/Test recovery** (distinct from production): the `/api/v1/dev/auth/*`
endpoints — flag-gated by `DEV_TEST_MODE` and additionally locked to the local
environment allow-list — provide direct reset helpers for local QA. They are
**disabled in production** (Section 8).

Manual operator steps:

1. Supabase dashboard → Auth → URL Configuration: Site URL = production frontend
   origin; add the production recovery redirect path to the redirect allow-list.
2. Verify email delivery (Supabase built-in SMTP or custom SMTP) sends recovery
   emails for the production project.
3. Execute the recovery flow end-to-end in production (Section 14 smoke test).

## 11. Same-Origin Deployment Contract

Phase 6.15.7 established that the application assumes **same-origin deployment**
(the backend configures no CORS middleware at all; no origin allow-list exists and
there is no wildcard risk). Expected production topology:

```text
https://college.example.com
        │
        ├── frontend (static bundle from frontend/dist)
        │
        └── /api/*  → reverse proxy → FastAPI  →  Supabase
```

Verification: the frontend API configuration is compatible with this model — the
default `VITE_API_BASE_URL=/api` makes the browser issue same-origin requests; the
reverse proxy maps `/api/*` to the FastAPI service.

**Cross-origin support status:** the current code does NOT support a separate
frontend/backend origin safely. A frontend at `https://app.example.com` calling
`https://api.example.com` would be blocked by the browser because no CORS headers
are ever emitted. Therefore:

> **Production requirement:** Frontend and API must use same-origin deployment
> **OR** an explicit CORS allow-list must be introduced before cross-origin
> deployment. Do NOT introduce wildcard CORS.

## 12. Health and Readiness

The backend already exposes `GET /health` (`backend/app/main.py`); no new
endpoint was needed. Verification results:

- **Does not expose secrets** — returns only `{status, service, environment}`
  (asserted by `test_health_endpoint_is_public_and_minimal`, which also rejects
  key/secret/token/password substrings and any Supabase URL fragment).
- **Does not require authentication** — public, unauthenticated (asserted).
- **Does not expose internal database details** — no DB/Supabase/R2/OpenRouter
  fields; the handler touches no service or client.
- **Returns stable status information** — static shape; `environment` is the
  configured deployment label, useful for deploy confirmation.
- **Does not instantiate privileged services unnecessarily** — the handler reads
  only Settings fields; no Supabase client, no R2 client, no network I/O.

Additional non-sensitive surfaces verified: the API root (`/`) returns only the
service name, version, environment label, and docs/health paths. Startup logs now
include the value-free configuration-validation report (Section 13).

## 13. Startup Validation

New: `backend/app/core/startup_validation.py`, invoked from `backend/app/main.py`
at import time (before the app serves any traffic).

Live output observed in local development (values withheld by design):

```text
Configuration validation: all 6 checks passed
(✓ SUPABASE_URL (configured (value withheld));
 ✓ SUPABASE_PUBLISHABLE_KEY (configured (value withheld));
 ✓ SUPABASE_SECRET_KEY (configured (value withheld));
 ✓ SUPABASE_JWKS_URL (configured (value withheld));
 ✓ DEV_TEST_MODE (enabled (allowed only in a local development/testing environment));
 ✓ DEBUG (enabled (set DEBUG=false outside local development/testing)))
```

Behavior:

- **Local development/testing:** failed checks log a `WARNING` and startup
  continues (a partially configured laptop stays usable; the problem is visible).
- **Any deployment environment (production/prod/staging/typo/empty):** any failed
  check raises `RuntimeError` and the app refuses to start, e.g.:

```text
Configuration validation failed for ENVIRONMENT='production'. The application
refuses to start with an incomplete/unsafe deployment configuration:
✗ SUPABASE_SECRET_KEY (SUPABASE_SECRET_KEY is missing or empty); ...
```

- Never prints actual secret values — only check names and static details
  (test-enforced with realistic-looking fake credentials).
- Checks: the four Supabase variables (presence), `DEV_TEST_MODE` (must be off
  outside local envs), `DEBUG` (must be off outside local envs).
- Failure is fail-fast at startup rather than a confusing runtime auth failure;
  no network I/O, no Supabase client construction.

## 14. Authentication Smoke Test

Repeatable post-deployment checklist (manual; requires a seeded production
Supabase project and an admin/staff account):

```text
Student registration
  1. Open production frontend                    → login page renders
  2. Institution lookup with valid code          → institution found
  3. Register student (identifiers + email)      → success message
  4. Attempt login before approval               → pending/not-approved message

Approval
  5. Admin/staff logs in, opens approvals        → pending student visible
  6. Approve student                             → status becomes approved

Student login
  7. Login with email + password                 → authenticated shell
  8. Login with register number + password + institution code → authenticated shell
  9. Login with university roll number + password + institution code → authenticated shell

Session
  10. Refresh page (restore session)             → still authenticated
  11. Token refresh / continued activity         → session stays valid
  12. Logout                                     → session cleared, login page shown

Session expiry
  13. Expired/invalidated session + API call     → API 401 → session cleared → login message

Multi-tab
  14. Tab A logout                               → Tab B reacts (session-expired → login)
  15. Tab B login                                → Tab A reacts (authenticated)
```

Status: documented, and the automated parts are executed by the regression suite
(registration, approval, all three login variants, session restore/refresh,
logout, expiry → 401 → cleared session → login message, and multi-tab
synchronization are covered by the Phase 6.15.2–6.15.7 suites). Steps 1–15
require a live production deployment and must be executed by the operator at
deploy time; no production deployment was performed in this phase.

## 15. Production Error Behavior

Phase 6.15.7 hardening, re-verified in this phase's regression run:

- Unhandled server exceptions → generic `500 {"error": {"code": "INTERNAL_ERROR",
  "message": "An unexpected server error occurred. Please try again later."}}` —
  no stack traces, SQL errors, Supabase internal errors, exception class names,
  filesystem paths, or implementation details (traceback logged server-side only).
- JWT contents, passwords, and API keys never appear in any response.
- Internal database IDs are exposed only where the locked contract requires them
  (e.g. the authenticated user's own identifiers via `/auth/me`).

Verified error codes remain stable and non-sensitive: `INVALID_CREDENTIALS`,
`SESSION_INVALID`, `NOT_FOUND`, `VALIDATION_ERROR` (422 with sanitized
`loc`/`msg`/`type` only). Test coverage: the Phase 6.15.7 hardening suite plus
the Phase 6.15.8 route tests.

## 16. Logging

Production logging audit (searched: `print(`, `console.log(`, `console.error(`,
`logger.*`, `password`, `token`, `access_token`, `refresh_token`, `service_role`,
`authorization`):

- **Backend:** the single authentication-related logger call (`app/api/auth.py`)
  logs operation/status metadata only — never credentials. `app/config.py` logs
  the DEV_TEST_MODE warning (flag value + environment name, no secrets). The new
  startup validation logs check names/details only — no values. The
  unhandled-error handler logs the traceback server-side (with the request path),
  never to the client.
- **Frontend:** authentication service modules (`auth.ts`, `devAuth.ts`,
  `registration.ts`) log nothing — no `console.*` calls.
- **Prints:** backend `print()` usage is confined to the local `start()`
  entrypoint banner (URLs only) and one-off developer scripts under
  `backend/scripts/` (not part of the runtime request path).
- Determination: **no sensitive value (password, JWT, refresh token,
  service-role key, API key) can reach logs.** Authentication logs contain
  operational metadata only.

## 17. Dependencies

Reviewed: `frontend/package.json` + `package-lock.json`, `backend/pyproject.toml`
+ `uv.lock`; no Docker files or deployment manifests exist.

- **Backend** (`pyproject.toml`, uv-managed, `uv.lock` pins exact versions):
  authentication-relevant dependencies are `fastapi`, `pyjwt[crypto]` (JWKS JWT
  verification), `supabase` (Auth/GoTrue + PostgREST client), `pydantic-settings`
  (configuration), `httpx`/`python-multipart` (API), `uvicorn` (server),
  `cryptography` (JWT crypto backend). Document/storage dependencies: `boto3`
  (R2), `pypdf`, `python-docx`, `email-validator`. No obsolete auth dependency
  remains (no legacy JWT-secret auth, no custom password hashing library —
  Supabase Auth owns credentials).
- **Frontend** (`package.json`): runtime dependencies are only `react` +
  `react-dom`. All test tooling (`vitest`, `@testing-library/*`, `jsdom`) and
  build tooling (`vite`, `typescript`, `tailwindcss`, `@vitejs/plugin-react`) are
  in `devDependencies` — test-only packages are not part of the production
  runtime (they are tree-shaken/bundler-excluded from `dist/`).
- **Known caveat (pre-existing, accepted):** `pytest`/`pytest-asyncio` are listed
  in the backend `[project] dependencies` (runtime section) rather than a separate
  dev group, because the project declares no dependency groups/extras. They are
  harmless at runtime (imported only by `tests/`) but are technically installed in
  production environments. Not changed in this phase to avoid unrelated dependency
  refactors (see Section 24).
- **Pinning:** both ecosystems are lockfile-pinned (`uv.lock`,
  `package-lock.json`) and both lockfiles are tracked in Git.

## 18. Build Reproducibility

- **Frontend:** clean `npm install` + `npm run build` executed in this phase —
  the build succeeds from tracked source alone (`tsc -b && vite build`; 63
  modules, `dist/` regenerated). `frontend/dist` is git-ignored; no
  developer-local file is required.
- **Backend:** dependencies install from `pyproject.toml`/`uv.lock`; the full test
  suite and the startup validation run against the declared dependency set. The
  app starts cleanly with a local-environment `.env` (validation report observed),
  and with no `.env` at all it fails only with explicit value-free validation
  warnings in local environments — production environments *require* the four
  Supabase variables and fail fast without them.
- **`.env` is not required to be committed** — it is git-ignored everywhere; all
  tracked configuration is `.env.example` placeholders.
- **Generated artifacts ignored appropriately:** `dist/`, `.venv/`,
  `__pycache__/`, `.pytest_cache/`, logs — all covered by `.gitignore` files
  (verified: `git status` shows no artifacts).
- **Production build contains no secrets** — verified by the dist scan (Section 6)
  and `scripts/verify_frontend_build_security.mjs`.

## 19. Test Configuration Separation

- **Backend tests:** construct `Settings(_env_file=None, …)` with explicit
  fake/placeholder values — they never read the developer's real `.env` for
  production-sensitive assertions and never contact live services (Supabase
  clients are mocked at the client boundary). The one suite that touches the real
  `settings` object (`test_shipped_settings_pass_their_own_validation`) only
  asserts the local development configuration satisfies its own guard.
- **Frontend tests:** Vitest mocks `fetch`; no environment variables are required
  (the `/api` default applies in jsdom).
- **E2E tests** (Phase 6.15.5 suite): run against the dev-configured local stack
  (`DEV_TEST_MODE`-gated local endpoints), never production credentials.
- **Production environment variables are never required for ordinary test
  execution** — a fresh clone with no `.env` can run `pytest tests -q` and
  `npm test` (tests needing Supabase config pass fakes; local `.env` warnings are
  non-fatal in the `development` environment).

## 20. Regression Testing

Full suites executed in this phase (clean working tree at phase start; only
Phase 6.15.8 changes applied):

- **Backend:** `python -m pytest tests -q` → **1683 passed, 15 skipped** (all
  pre-existing skips), 6 third-party deprecation warnings — includes the 25 new
  Phase 6.15.8 tests and all Phase 6.15.1–6.15.7 suites unchanged.
- **Frontend:** `npm test` (Vitest) → **197 passed / 197, 0 failed** (18 files) —
  includes the 3 new `src/config/env.test.ts` tests.
- **Build:** `npm run build` → TypeScript pass + Vite build success (pre-existing
  Tailwind CSS pseudo-class warning only).
- **Secret/build scan:** `node scripts/verify_frontend_build_security.mjs` → PASS.
- No authentication regression was accepted or observed: every prior auth suite
  passes unchanged.

## 21. Configuration Tests

New: `backend/tests/test_config_phase_6_15_8.py` (25 tests) and
`frontend/src/config/env.test.ts` (3 tests). Coverage vs. the required
expectations:

- **`DEV_TEST_MODE` defaults safely** — `test_dev_test_mode_defaults_to_false`;
  the default `ENVIRONMENT` is a local value
  (`test_environment_defaults_to_local_development`).
- **Production configuration cannot accidentally enable dev auth routes** —
  `test_dev_test_mode_true_with_production_environment_is_refused` (production /
  prod / staging / empty all refused) + `test_dev_auth_routes_return_404_with_flag_off`
  (all three dev routes → 404, `create_client` never called).
- **Required production configuration is validated** —
  `test_fully_configured_production_settings_pass_validation`;
  `test_missing_required_production_config_stops_startup` (parametrized over all
  four Supabase variables: `RuntimeError`, variable named, startup refused);
  `test_debug_true_stops_startup_outside_local_environments`;
  `test_incomplete_local_configuration_only_warns`.
- **Secret values are not exposed in configuration output** —
  `test_check_details_never_contain_secret_values`;
  `test_failure_log_lines_never_contain_secret_values`.
- **Frontend production configuration does not expose backend secrets** —
  env-usage allowlist test, secret-shaped-name test, same-origin default test
  (plus the built-bundle scan script for the artifact level).
- **Invalid API configuration fails predictably** — missing backend Supabase
  variables fail at startup with a clear, value-free message; the frontend default
  is same-origin `/api`, and any `localhost` reference in `dist/` fails the scan.

All configuration tests use placeholder/fake values — none require real
production secrets.

## 22. Security Verification

Mandatory security requirements — final status:

- Never expose service-role keys to frontend → **verified** (no client-side
  Supabase SDK; only `VITE_API_BASE_URL` in the bundle; dist scan clean).
- Never expose passwords in logs → **verified** (Section 16 audit).
- Never expose JWTs in logs → **verified** (Section 16 audit).
- Never enable `/dev/auth/*` in production → **verified** (flag default off;
  environment allow-list refuses misconfiguration; router-level 404 gate; no
  Supabase client on disabled routes).
- Never introduce wildcard production CORS → **verified** (no CORS middleware at
  all; same-origin contract documented in Section 11).
- Never expose stack traces through authentication endpoints → **verified**
  (generic 500 `INTERNAL_ERROR` envelope; Phase 6.15.7 tests re-run).
- Never put credentials in URLs → **verified** (passwords/tokens only in POST
  bodies and the `Authorization` header; pre-existing property).
- Never weaken tenant isolation → **verified** (no auth code touched; tenant
  scoping suites pass unchanged).
- Never trust frontend role fields → **verified** (role resolution remains
  server-authoritative; no auth code touched).
- Never allow registration to assign privileged roles → **verified** (registration
  contract unchanged; suite passes).
- Never allow client-provided approval status → **verified** (unchanged; suite passes).
- Never expose internal database IDs unnecessarily → **verified** (`/auth/me`
  field set locked by Phase 6.15.7 tests).
- Never commit `.env` → **verified** (git-ignored in root/backend/frontend;
  live-value scan of 384 tracked files → 0 secret hits).
- Never place secrets in documentation → **verified** (this document names
  variables only).
- Never disable existing authentication tests merely to make deployment pass →
  **verified** (all 1683 backend + 197 frontend tests pass; zero tests modified,
  skipped, or deleted).

## 23. Issues Found

1. **No startup configuration validation existed.** A deployment with missing
   Supabase variables would boot and only fail later with confusing runtime
   authentication errors. → Fixed (Sections 7, 13).
2. **`DEBUG=true` was effectively unenforced.** The setting existed and gated
   chat diagnostics metadata, but nothing prevented a deployment from shipping
   with debug enabled. → Fixed (startup check refuses `DEBUG=true` outside local
   environments).
3. **`ENVIRONMENT`/`DEBUG` were undocumented** in `backend/.env.example`, leaving
   the dev/production boundary implicit. → Fixed (documented with the local
   allow-list semantics).
4. **No automated guard against `localhost` leaking into the production bundle**
   or non-allowlisted env variables reaching the browser. → Fixed
   (`scripts/verify_frontend_build_security.mjs` + `frontend/src/config/env.test.ts`).
5. **Pre-existing, NOT fixed (accepted):** `pytest`/`pytest-asyncio` sit in the
   backend runtime dependency list (no dependency-groups section exists); moving
   them would be an unrelated dependency refactor. Harmless at runtime.
6. **Pre-existing, NOT fixed (accepted):** `frontend/dist` build emits a Tailwind
   CSS pseudo-class warning (`::file-selector-button:disabled`) — cosmetic, build
   succeeds, unrelated to authentication.
7. **Pre-existing, NOT fixed (accepted):** the local developer `.env` runs with
   `DEV_TEST_MODE=true` and `ENVIRONMENT` unset (defaults to `development`) —
   valid for the local allow-list and intentional for local QA; a deployment copy
   must set `DEV_TEST_MODE=false` (checklist item).

## 24. Fixes Applied

1. Added `backend/app/core/startup_validation.py` — value-free configuration
   checks (4 Supabase variables + `DEV_TEST_MODE` + `DEBUG`), warning-only in
   local environments, fail-fast `RuntimeError` anywhere else; wired into
   `backend/app/main.py` at import time. No network I/O, no Supabase clients.
2. Documented `ENVIRONMENT` and `DEBUG` in `backend/.env.example` with the local
   environment allow-list semantics.
3. Added `backend/tests/test_config_phase_6_15_8.py` (25 configuration/security
   tests).
4. Added `frontend/src/config/env.test.ts` (3 env-configuration invariant tests).
5. Added `scripts/verify_frontend_build_security.mjs` — repeatable production
   build-artifact + env-usage + `.env.example` secret scan.
6. Added this document (28 sections) including the production deployment
   checklist.

No authentication architecture, contract, or test was modified.

## 25. Production Deployment Checklist

```text
[ ] Production Supabase project configured (URL, keys, auth enabled, email/password on)
[ ] Site URL + recovery redirect allow-list configured in Supabase (Section 10)
[ ] Backend secrets configured (SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY,
    SUPABASE_SECRET_KEY, SUPABASE_JWKS_URL via deployment secrets)
[ ] Frontend public configuration configured (VITE_API_BASE_URL=/api or explicit origin)
[ ] DEV_TEST_MODE=false
[ ] DEBUG=false
[ ] ENVIRONMENT=production (or any non-local value)
[ ] No production secrets in frontend (scripts/verify_frontend_build_security.mjs PASS)
[ ] No secrets committed to Git (live-value scan PASS; .env ignored)
[ ] Production API URL verified (same-origin /api through reverse proxy)
[ ] Same-origin routing verified (frontend and /api/* served from one origin)
[ ] Password recovery configuration verified (hosted flow end-to-end)
[ ] Health endpoint verified (GET /health → 200 {status, service, environment})
[ ] Startup validation verified (all checks pass; no secret values in logs)
[ ] Student registration verified (lookup → register → pending)
[ ] Admin/staff approval verified
[ ] Student login verified (email / register number / university roll number)
[ ] Session restoration verified (page refresh keeps session)
[ ] Logout verified (session cleared)
[ ] Session-expiry behavior verified (401 → session cleared → login message)
[ ] Multi-tab behavior verified (logout/login propagation across tabs)
[ ] Production error sanitization verified (generic 500; stable error codes)
[ ] Production logging verified (no credentials/tokens in logs)
[ ] Backend tests passed (pytest tests -q)
[ ] Frontend tests passed (npm test)
[ ] Production build passed (npm run build)
[ ] Dependency audit passed (lockfiles pinned; runtime vs dev deps reviewed)
[ ] Secret scan passed
```

## 26. Final Verification

### Backend
```text
Full test count: 1698 collected (1683 passed + 15 skipped)
Passed:          1683
Skipped:         15   (pre-existing skips)
Failed:          0
Warnings:        6    (pre-existing third-party deprecations)
```

### Frontend
```text
Tests:   197 (18 files)
Passed:  197
Failed:  0
```

### Build
```text
TypeScript: PASS (tsc -b)
Build:      PASS (vite build, 63 modules → dist/)
Warnings:   1 pre-existing Tailwind CSS pseudo-class warning (cosmetic)
```

### Security
```text
Secret scan:              PASS (dist/ + 384 tracked files + .env.example placeholders)
Dependency audit:         PASS (lockfile-pinned; 1 accepted caveat: pytest in runtime deps)
Production configuration: PASS (fail-fast startup validation, value-free errors)
DEV_TEST_MODE:            false by default; true refused outside local environments; dev routes 404
Frontend secret exposure: NONE (only VITE_API_BASE_URL; bundle scan clean)
```

### Deployment
```text
Frontend:          same-origin static bundle (frontend/dist), /api base default
Backend:           FastAPI + startup configuration validation (fail-fast, value-free)
Supabase:          project URL + publishable + service-role + JWKS; auth/email-password
                   enabled; recovery redirects configured (manual, Section 9)
API routing:       reverse proxy /api/* → FastAPI; no CORS configured; cross-origin NOT
                   supported without an explicit allow-list
Password recovery: Supabase hosted flow (production); dev endpoints disabled in production
Health/readiness:  GET /health (public, stable, secret-free)
```

## 27. Git Scope

`git status` / `git diff --stat` / `git diff --name-only` at phase completion:

**1. Phase 6.15.8 files (this phase):**

- `backend/app/core/startup_validation.py` — NEW
- `backend/tests/test_config_phase_6_15_8.py` — NEW
- `frontend/src/config/env.test.ts` — NEW
- `scripts/verify_frontend_build_security.mjs` — NEW
- `backend/app/main.py` — MODIFIED (+6 lines: startup validation import + call)
- `backend/.env.example` — MODIFIED (+13 lines: `ENVIRONMENT`/`DEBUG` documentation)
- `PHASE_6_15_8_AUTH_DEPLOYMENT_OPERATIONAL_READINESS.md` — NEW (this document)

**2. Previous Phase 6.15.1–6.15.7 files:** all committed at `6484bae` on `main`
before this phase began; untouched in this phase (the working tree contains no
modifications to any prior-phase file).

**3. Unrelated existing modifications:** none — the working tree was clean at
phase start (`git status` empty) and contains only the Phase 6.15.8 files above.
Pre-existing untracked-but-ignored local files (`.env`, logs, `.venv/`) are
git-ignored and were not modified or cleaned.

**No commit was created.** Nothing was staged or committed; all changes remain
uncommitted working-tree state for review.

## 28. Phase Completion Status

Definition of Done — all satisfied:

- Environment configuration fully audited — Sections 3–5.
- Dev/test/prod configuration matrix documented — Section 4.
- Secret classification documented — Section 5.
- Frontend production configuration verified — Section 6.
- Backend production configuration verified — Section 7.
- DEV_TEST_MODE production behavior verified — Section 8.
- Supabase production requirements documented — Section 9.
- Password recovery deployment contract documented — Section 10.
- Same-origin deployment contract verified — Section 11.
- Health/readiness behavior verified — Section 12.
- Startup configuration validation verified — Section 13.
- Authentication smoke test documented (operator-executed at deploy time) — Section 14.
- Production error sanitization verified — Section 15.
- Logging audit completed — Section 16.
- Dependency configuration reviewed — Section 17.
- Clean frontend build succeeds — Sections 18/20.
- Backend startup/configuration validation succeeds — Sections 13/20.
- Full backend test suite passes — 1683 passed / 15 skipped / 0 failed.
- Full frontend test suite passes — 197 passed / 0 failed.
- Configuration tests pass — 25 backend + 3 frontend new tests green.
- Secret scan passes — dist + tracked files + env examples clean.
- No production secrets exposed in build artifacts — verified.
- Documentation contains exactly 28 required sections — this document.
- Git scope is clearly documented — Section 27.
- No unrelated Phase 6 work is modified — verified.
- No commit was created automatically — verified.

**Phase 6.15.8 — COMPLETE**











