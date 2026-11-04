# College AI Chatbot — Technology Stack

## Backend

| Concern | Technology |
|---|---|
| Language | Python ≥ 3.13 |
| Package manager | uv (lockfile: `backend/uv.lock`) |
| Web framework | FastAPI ≥ 0.141.1 |
| ASGI server | Uvicorn ≥ 0.52.4 |
| Configuration | pydantic-settings ≥ 2.9.1 |
| Database / Auth | Supabase (Postgres + pgvector) via `supabase` SDK ≥ 2.31.0 |
| Object storage | Cloudflare R2 via boto3 ≥ 1.38.0 (S3-compatible) |
| LLM generation | OpenRouter (HTTP, configurable model) |
| Embeddings | Pluggable via `EMBEDDING_MODEL` env var |
| JWT verification | PyJWT[crypto] ≥ 2.13.0 |
| Document parsing | pypdf ≥ 4.0.0, python-docx ≥ 1.1.0, xlrd ≥ 2.0.2, Pillow ≥ 11.1.0 |
| Email | aiosmtplib ≥ 5.0 |
| Testing | pytest ≥ 8.4.1, pytest-asyncio ≥ 1.0.0, httpx ≥ 0.28.1 |
| Linting | Ruff |

## Frontend

| Concern | Technology |
|---|---|
| Language | TypeScript ~5.9.2 |
| Framework | React 19 |
| Build tool | Vite 7 |
| Server-state | TanStack Query v5 |
| Styling | Tailwind CSS v4 (via `@tailwindcss/vite`) |
| Icons | lucide-react |
| Markdown rendering | react-markdown + remark-gfm |
| Excel parsing | read-excel-file |
| Testing | Vitest 5, @testing-library/react 16, jsdom |
| Formatting | Prettier 3 |

## Infrastructure

| Concern | Technology |
|---|---|
| Database | Supabase (hosted Postgres + pgvector extension) |
| Auth provider | Supabase Auth |
| Object storage | Cloudflare R2 |
| LLM API | OpenRouter |
| Migrations | SQL files in `supabase/migrations/` (ordered by timestamp prefix) |

## Development Commands

### Backend (run from `backend/`)
```powershell
uv sync                          # install dependencies
uv run start                     # start dev server on :8000 (--reload)
uv run uvicorn app.main:app --reload  # equivalent
uv run python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py
```

### Frontend (run from `frontend/`)
```powershell
npm install
npm run dev          # Vite dev server on :5173, proxies /api → :8000
npm run build        # tsc -b && vite build
npm run preview      # serve production build
npm run test         # vitest run
npm run format       # prettier --write .
npm run check        # structure check + build + test
```

## Environment Configuration

| File | Purpose |
|---|---|
| `backend/.env` | Supabase keys, R2 credentials, OpenRouter key, embedding model, auth settings |
| `frontend/.env` | Frontend-facing env vars (Vite `VITE_` prefix) |

Key backend env vars:
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`
- `OPENROUTER_API_KEY`
- `EMBEDDING_MODEL`
- `AUTH_RECOVERY_REDIRECT_URL`
- `DEV_TEST_MODE` (keep `false` in production)

## Health / Readiness Endpoints
- `GET /health` — confirms API process is running
- `GET /ready` — confirms database connectivity (check this for 503 errors)

## Notes
- Backend config loads `.env` relative to CWD; always run backend commands from `backend/`
- `DEV_TEST_MODE=true` is for local dev/test only — never deploy with it enabled
- Auth rate limits are process-local; production requires shared gateway-level limits
- Physical validation tests (`test_physical_validation_phase_4_4.py`) require live credentials and are excluded from CI
