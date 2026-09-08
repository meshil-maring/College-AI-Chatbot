# PHASE 5.3 — API CLIENT & LOCKED CONTRACT TYPES LOCK

Status: LOCKED

Phase: 5.3
Name: API Client & Locked Contract Types
Lock date: 2026-09-08
Lock basis: Phase 5.3 implementation validated with `PHASE 5.3 — PASS`, then re-verified and locked at final lock time.

## Final Verdict

PHASE 5.3 — PASS

## Locked Deliverables

- `frontend/src/types/chat.ts`
- `frontend/src/services/api.ts`

## Locked Contract Types

- ChatRequest
- ChatResponse
- SourceReference
- StructuredSource
- ChatUsage
- ChatStatus

## API Endpoint

POST /api/v1/generation/chat

## API Client

- Native browser fetch
- VITE_API_BASE_URL
- JSON request body
- Authorization Bearer token support
- Typed ChatResponse
- ApiError for non-success HTTP responses

## Contract Integrity

The frontend TypeScript contract mirrors the authoritative Phase 4.4 backend JSON contract.

Snake_case JSON field names are preserved.

UUID values are represented as strings at the HTTP boundary.

Nullable and optional fields preserve the backend contract.

`retrieved_chunks` remains an internal backend concern and is not exposed by the frontend request type.

### Field-by-field basis (verified against backend schemas)

- `ChatRequest` mirrors `backend/app/schemas/chat.py::ChatRequest`:
  required `user_query`, `institution_id`; optional/nullable `session_id`,
  `conversation_id`, `knowledge_source_id`, `document_id`,
  `document_version_id`, `processing_run_id`, `model_name`.
  `retrieved_chunks` is intentionally absent.
- `ChatResponse` mirrors `backend/app/schemas/chat.py::ChatResponse`
  (extends `AIResponse` in `backend/app/schemas/generation.py`):
  `answer: string | null`, `source_references: SourceReference[]`,
  `status: ChatStatus`, `model_used: string | null`,
  `metadata: Record<string, unknown>`, `session_id`,
  `conversation_id`, `message_id: string | null`, `sources: StructuredSource[]`,
  `usage: ChatUsage | null`.
- `SourceReference` mirrors `backend/app/schemas/generation.py::SourceReference`:
  `chunk_id`, `quote` required; `document_id`, `document_version_id`,
  `similarity_score` optional/nullable.
- `StructuredSource` mirrors `backend/app/schemas/chat_response.py::StructuredSource`:
  `chunk_id`, `quote` required; `relevance_score`, `source_title`,
  `section` optional/nullable.
- `ChatUsage` mirrors `backend/app/schemas/chat_response.py::ChatUsage`:
  `input_tokens`, `output_tokens` optional/nullable.
- `ChatStatus` is exactly `'success' | 'insufficient_context'`, matching the
  backend `AIResponse.status` validator without broadening.

## Authentication Boundary

Authentication is NOT implemented in Phase 5.3.

The API client only accepts an access token supplied by its caller.

No Supabase client, login page, login service, JWT persistence, JWT refresh,
auth context, auth hook, or auth state management exists.

## UI Boundary

The API client is NOT integrated into the chat UI in Phase 5.3.

No chat screen, send button, message/loading/error UI, source/citation UI,
usage UI, session state, or conversation state exists.

`frontend/src/App.tsx` remains the Phase 5.2 starter UI and performs zero
network requests.

## Business Logic Boundary

No RAG, retrieval, embedding, LLM, provider-selection, database,
citation-generation, or business logic exists in the frontend API boundary.

No runtime schema-validation dependency was added.

## Validation

- TypeScript/build: PASS
- Contract comparison: PASS
- API client validation: PASS
- Backend integrity: PASS
- Phase 5.2 integrity: PASS
- Scope integrity: PASS

### Validation evidence (observed at implementation and re-verified at lock time)

- Build command `npm run build` (`tsc -b && vite build`): 0 TypeScript errors,
  29 modules transformed, production bundle emitted successfully
  (exit code 0).
- Contract comparison: field names, JSON names, optionality, nullability,
  nested structures, status values, and UUID-as-string boundary representation
  verified field-by-field against `backend/app/schemas/generation.py`,
  `backend/app/schemas/chat.py`, `backend/app/schemas/chat_response.py`, and
  the route in `backend/app/main.py` (`POST /generation/chat` mounted at
  `/api/v1`). No discrepancies found.
- API client validation: temporary isolated mock-`fetch` harness exercised the
  real client and verified: URL `/api/v1/generation/chat`; method `POST`;
  `Content-Type: application/json`; `Authorization: Bearer <token>`; JSON body
  serialized from `ChatRequest` with no token in the body and no
  `retrieved_chunks`; typed `ChatResponse` returned on 2xx; `ApiError` with
  `status`/`message`/`details` on 401/422/500 — HTTP failures are never
  converted into a fabricated `ChatResponse`. Harness was removed afterward.
- No UI integration: `App.tsx` untouched, no request originates from it.
- No authentication implementation: token is caller-supplied only.

## Backend Integrity

Phase 4.4 backend remains untouched.

No CORS middleware was added.

Protected paths verified unchanged via git at lock time:
`backend/app/main.py`, `backend/app/services/retrieval.py`,
`backend/app/services/generation_provider.py`, `backend/app/services/chat.py`,
`backend/app/schemas/generation.py`, `backend/app/schemas/chat.py`,
`backend/app/schemas/chat_response.py`, `supabase/`.
`git diff HEAD -- backend supabase` is empty.

## Phase 5.2 Integrity

`PHASE_5_2_LOCK.md` remains unchanged.

## Git / Working-Tree Notes

- HEAD is `178b8b7` (Phase 4.4 lock documentation commit).
- The Phase 5.3 deliverables `frontend/src/types/chat.ts` and
  `frontend/src/services/api.ts` are untracked and intentionally left
  uncommitted.
- No files were staged, reset, stashed, cleaned, or committed by this phase.
- No Phase 5.2 or Phase 4.4 files were modified by this phase.

## Lock Rule

Phase 5.3 is complete and locked.

Future phases must not silently alter the locked API contract or API-client boundary.

Changes require explicit change/revalidation.

## Next Phase

PHASE 5.4 — AUTHENTICATION & SESSION BOOTSTRAP