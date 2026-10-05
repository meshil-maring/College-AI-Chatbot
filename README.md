# College AI Chatbot

An institution-scoped RAG chatbot for colleges: a **FastAPI + Supabase** backend that answers
academic questions strictly from institution-owned documents, plus a **React + TypeScript + Vite**
frontend with a typed API client.

```text
Browser (React/Vite :5173)
   --/api-->  Vite dev proxy (dev only)
                 --/api-->  FastAPI backend (:8000)
                               |-- Supabase (Postgres + pgvector, Auth, tenant-scoped data)
                               |-- Cloudflare R2 (uploaded document objects)
                               |-- OpenRouter (chat generation)
                               `-- embedding provider (EMBEDDING_MODEL)
```

## Repository layout

| Path | Contents |
| --- | --- |
| `backend/app/` | FastAPI application: API routers, services, repositories, schemas, core security/config |
| `backend/tests/` | Pytest suite (unit, API and integration tests over the `app` package) |
| `backend/evaluation/` | Retrieval evaluation harness (`evaluator.py`) |
| `backend/scripts/` | Manual debugging and physical-validation scripts (see `backend/scripts/README.md`) |
| `frontend/` | React + TypeScript + Tailwind UI, Vitest tests |
| `supabase/` | `config.toml` and the ordered SQL migrations in `supabase/migrations/` |
| `docs/` | Phase locks, status notes, reports, schema export, MCP notes, evidence JSON â€” see `docs/README.md` |
| `scripts/` | Historical one-off repository maintenance scripts â€” see `scripts/README.md` |

## Prerequisites

- Python >= 3.13 with [uv](https://docs.astral.sh/uv/) (the backend is uv-managed: `backend/uv.lock`)
- Node.js 20+ with npm (frontend)
- A Supabase project (Postgres + `pgvector`), a Cloudflare R2 bucket, and an OpenRouter API key

## Configure

```powershell
Copy-Item backend/.env.example  backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Fill in `backend/.env` (Supabase keys, R2 credentials, `OPENROUTER_API_KEY`). Keep
`DEV_TEST_MODE=false` everywhere except a local development/testing environment. `.env` files are
git-ignored â€” never commit real values.

## Super Admin registration (invitation-only)

There is no public Super Admin sign-up. An existing Super Admin opens **Super Admins** in the platform workspace and invites an email address. The single-use link (`/super-admin-invite/{token}`, valid 24 hours, stored only as a SHA-256 digest) is shown once to the inviter. The invitee chooses a name and password (8+ characters); the email, role (`super_admin`) and platform scope come from the server-side invitation, never the request. Apply migration `20261008000000_phase_9_super_admin_invitations.sql`. The very first Super Admin is still created with the local provisioning wrapper.
## Authentication security and session lifecycle

Supabase Auth remains the credential and session provider. The backend verifies
Supabase JWTs and resolves the application user, tenant, roles, and permissions
server-side through the existing `/auth/me` flow; the browser never supplies
authorization state.

| Operation | Behavior |
| --- | --- |
| Session creation | Login returns the provider access token, rotating refresh token, and `expires_in`. |
| Session restoration | The frontend persists those provider session values in browser local storage, then validates the access token through `/auth/me`. |
| Session renewal | The frontend refreshes about 60 seconds before access-token expiry, stores the rotated provider tokens, and revalidates identity through `/auth/me`. |
| Session expiration | If renewal fails or `/auth/me` rejects the token, the browser clears local session state and returns to sign-in. |
| Logout | `/auth/logout` revokes the current provider refresh session and clears the browser session. |
| Logout all | `/auth/logout-all` revokes all provider refresh sessions for the user and clears the browser session. |
| Password change | The current password is verified; after update, other provider sessions are revoked (`scope=others`). |
| Password reset | Only a recently issued Supabase recovery session is accepted; the provider session is single-use at the application boundary and successful reset revokes all refresh sessions. |

Supabase access JWTs are self-contained and remain usable by APIs that only
verify their signature until their configured expiry, even after the associated
refresh session has been revoked. Keep access-token lifetimes appropriately
short in Supabase Auth settings. The browser uses local storage for provider
session tokens, so protect the frontend against script injection and deploy
strong Content Security Policy controls.

Password recovery returns the same message whether or not an account exists.
Set `AUTH_RECOVERY_REDIRECT_URL` to the deployed frontend's `/reset-password`
URL and add that exact URL to the Supabase Auth redirect allowlist. Outside
local/test environments, the backend requires this setting. The new database
migration must be applied before deployment; it creates the security-event
audit table and the single-use recovery-session marker. The marker stores only
a SHA-256 fingerprint of Supabase's signed session ID, never a reset token.

Authentication limits default to 30 login attempts, 5 recovery requests, or
10 password operations per direct peer IP in a five-minute window. These
counters are process-local and reset on restart; production deployments must
also enforce shared rate limits at the gateway/edge across workers.

## Run the backend

```powershell
cd backend
uv sync
uv run start            # console entry point -> uvicorn app.main:app --reload on :8000
```

Equivalent: `uv run uvicorn app.main:app --reload`. Health probe: `http://127.0.0.1:8000/health`.

> `backend/app/config.py` loads `.env` relative to the **current working directory**
> (`env_file=".env"`), so run backend commands from `backend/`. This is documented as a known
> limitation in `docs/locks/PHASE_6_6_LOCK.md`.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev             # http://localhost:5173, proxies /api -> http://localhost:8000
```

`npm run build` type-checks (`tsc -b`) and builds; `npm run preview` serves the build.

## Tests

```powershell
# backend (run from backend/)
uv run python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py

# frontend (run from frontend/)
npm run test            # vitest run
```

`tests/test_physical_validation_phase_4_4.py` is a *physical* validation test that requires a live
backend plus real Supabase/OpenRouter credentials, so it is excluded from the default regression run.

## Manual and validation scripts

These need a running backend and real credentials in `backend/.env`. Run them with `backend/` as the
working directory (for `.env` discovery), for example:

```powershell
cd backend
python scripts/manual_tests/test_faq_api.py
python scripts/validation/test_physical_phase_4_2.py
```

Every script resolves the backend package root from its own file location, so `import app...` works
regardless of the invocation path. See `backend/scripts/README.md` for the full list.

## Documentation

Phase locks, status reports and validation evidence live in `docs/` â€” start at `docs/README.md`.