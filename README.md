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
| `docs/` | Phase locks, status notes, reports, schema export, MCP notes, evidence JSON — see `docs/README.md` |
| `scripts/` | Historical one-off repository maintenance scripts — see `scripts/README.md` |

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
git-ignored — never commit real values.

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

Phase locks, status reports and validation evidence live in `docs/` — start at `docs/README.md`.