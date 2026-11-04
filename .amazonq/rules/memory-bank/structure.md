# College AI Chatbot — Project Structure

## Repository Layout

```
CollegeAIChatbot/
├── backend/                  # FastAPI Python application (uv-managed)
│   ├── app/                  # Application source
│   │   ├── api/              # Route handlers (thin controllers)
│   │   ├── core/             # App wiring, security, permissions, errors
│   │   ├── db/               # Supabase client factory
│   │   ├── middleware/        # Rate limiting, body limits, security headers
│   │   ├── models/           # (reserved)
│   │   ├── repositories/     # Data-access layer (Supabase queries)
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── services/         # Business logic layer
│   │   ├── config.py         # Pydantic-Settings configuration
│   │   └── main.py           # Uvicorn entry point
│   ├── tests/                # Pytest suite (unit + API + integration)
│   ├── evaluation/           # Retrieval evaluation harness
│   ├── scripts/              # Manual debug and validation scripts
│   ├── pyproject.toml        # Dependencies and build config
│   └── STRUCTURE.md          # Backend file placement rules
├── frontend/                 # React + TypeScript + Vite SPA
│   ├── src/
│   │   ├── app/              # Top-level routing, auth gates, layout
│   │   ├── features/         # Feature slices (admin, auth, chat, student, …)
│   │   ├── hooks/            # Shared React hooks (useChat, useApiQuery, …)
│   │   ├── services/         # Typed API client modules per domain
│   │   ├── types/            # Shared TypeScript type definitions
│   │   ├── lib/              # queryClient, navigation helpers
│   │   ├── providers/        # React context providers (QueryProvider)
│   │   ├── styles/           # CSS tokens, base, component styles
│   │   └── test/             # Vitest setup and fixtures
│   ├── package.json
│   └── vite.config.ts
├── supabase/
│   ├── migrations/           # Ordered SQL migration files
│   └── config.toml
├── docs/                     # Phase locks, status reports, schema exports, evidence
├── scripts/                  # Repo-level maintenance scripts
└── logs/                     # Local test/diagnostic output (git-ignored)
```

## Backend Domain Modules
Each domain (academics, admin, ai, auth, email, invitations, knowledge, platform, students) has a consistent vertical slice:

```
api/<domain>/        → FastAPI router (HTTP boundary)
services/<domain>/   → Business logic, orchestration
repositories/<domain>/ → Supabase data access
schemas/<domain>/    → Pydantic I/O models
```

## Frontend Feature Slices
`src/features/<domain>/` contains co-located components, hooks, and service calls for each product area. Shared concerns live in `src/hooks/`, `src/services/`, and `src/types/`.

## Architectural Patterns

### Backend
- **Layered architecture**: API → Service → Repository; no layer skips
- **Dependency injection via FastAPI `Depends`**: auth, DB client, config injected into route handlers
- **Pydantic-Settings** for typed, validated environment configuration
- **Supabase** as the primary database (Postgres + pgvector) and auth provider
- **Cloudflare R2** (S3-compatible via boto3) for document object storage
- **OpenRouter** for LLM generation; pluggable embedding model via `EMBEDDING_MODEL` env var

### Frontend
- **React 19 + TypeScript** SPA served by Vite dev server (proxies `/api` → `:8000`)
- **TanStack Query v5** for server-state management and caching
- **Feature-slice layout**: each feature owns its UI, local hooks, and service calls
- **Typed API client** in `src/services/` mirrors backend domain structure
- **Tailwind CSS v4** for styling via `@tailwindcss/vite` plugin

### Data Flow (RAG Chat)
```
User message
  → frontend useChat hook
  → POST /api/ai/chat
  → generation_qualification service (decide if retrieval needed)
  → knowledge retrieval (pgvector similarity search)
  → OpenRouter LLM generation with retrieved context
  → streamed/returned response
  → frontend renders with react-markdown
```

### Multi-Tenancy
All data queries are scoped by `institution_id` (tenant). Row-level security in Supabase enforces isolation at the database layer.
