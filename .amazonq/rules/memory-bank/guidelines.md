# College AI Chatbot — Development Guidelines

## Backend (Python / FastAPI)

### Code Structure Conventions
- **Layered architecture is strictly enforced**: API router → Service → Repository. No layer may skip another.
- Each domain has a parallel vertical slice across `api/`, `services/`, `repositories/`, `schemas/`.
- Private helpers are prefixed with `_` (e.g., `_validate`, `_extension`, `_safe_filename`, `_build_chunks`).
- Public entry points are minimal wrappers that call private helpers (e.g., `chunk_text` calls `_build_chunks`).
- Module-level constants are `UPPER_SNAKE_CASE`; compiled regexes are module-level constants.

### Error Handling
- All application errors use `AppError` from `app.core.errors` with `status_code` and `code` kwargs:
  ```python
  raise AppError("File is empty", status_code=422, code="EMPTY_FILE")
  ```
- Error codes are `UPPER_SNAKE_CASE` strings (e.g., `INVALID_FILE_TYPE`, `REGISTRATION_FAILED`).
- Raw exceptions (SQL text, storage paths, provider detail) must never reach HTTP responses — log with `logger.exception(...)` and raise a sanitized `AppError`.
- Use `from exc` chaining when re-raising to preserve the traceback.
- Cleanup side effects (e.g., R2 file deletion) in `except` blocks before re-raising.

### Configuration (`app/config.py`)
- All settings are in a single `Settings` class using `pydantic-settings` with `SettingsConfigDict(env_file=".env")`.
- Numeric limits use `Field(default=..., gt=..., le=...)` for validated bounds.
- Computed/derived values are `@property` methods (e.g., `effective_allowed_hosts`, `effective_cors_allowed_origins`).
- Environment-sensitive defaults: properties check `is_local_environment` to provide safe local fallbacks while rejecting missing values in production.
- `DEV_TEST_MODE` must always be `False` in production — never bypass this.
- A singleton `settings = Settings()` is instantiated at module level and imported everywhere.

### Security Patterns
- File uploads: validate extension, MIME type, size, and content magic bytes before any processing.
- Filenames from clients are untrusted: strip directory components, restrict to `[A-Za-z0-9._-]`, cap at 128 chars.
- DOCX archives: check entry count, path traversal (`..`), uncompressed size, and compression ratio.
- Rate limits are process-local; comments explicitly note that production requires shared gateway limits.
- SHA-256 digests are used for sensitive tokens (never store raw tokens).
- Phase/version comments (e.g., `# Phase 6.21 — production hardening:`) document security decisions inline.

### Logging
- Use `logger = logging.getLogger(__name__)` at module level.
- Log with structured context: `logger.exception("...(document_id=%s)", doc_id)`.
- Never log sensitive data (tokens, passwords, PII).

### Async Patterns
- Service functions that perform I/O are `async def`.
- Pure computation helpers (chunking, validation logic) are synchronous `def`.
- `await file.read(chunk_size)` with a bounded loop for streaming uploads; handle `TypeError` for test doubles.

### Docstrings and Comments
- Module-level docstrings describe the phase, purpose, and algorithm (e.g., chunking.py).
- Function docstrings explain *why*, not just *what*, especially for non-obvious decisions.
- Inline comments reference the phase that introduced a constraint (e.g., `# Phase 5.7b`).
- Conservative heuristics are documented with explicit rationale (see `_is_title_case_heading`).

### Type Annotations
- All function signatures use type annotations including return types.
- Use `str | None` (union syntax, Python 3.10+) rather than `Optional[str]`.
- Use `list[dict]`, `list[str]` etc. (lowercase generics, Python 3.9+).

---

## Frontend (TypeScript / React)

### Hook Design (`useChat.ts` pattern)
- Hooks return a typed interface (`ChatState`) with `readonly` fields — callers cannot mutate state directly.
- Identity guards: serialize all identity-relevant values into a stable string (`identity`) and compare with `useRef` to detect stale closures or user switches.
- Epoch counters (`epoch.current`) prevent stale async responses from updating state after unmount or identity change.
- `pending.current` (ref, not state) prevents double-submission without triggering re-renders.
- `useCallback` with explicit dependency arrays on all exported functions.
- Separate `accept` / `deny` helpers for success/failure paths keep the main `perform` function readable.

### State Management
- TanStack Query (`useMutation`, `useQuery`) for all server interactions; `queryClient` is a shared singleton from `src/lib/queryClient.ts`.
- `mutationKey` includes identity to scope mutations per user/session.
- `retry: false` on chat mutations — recovery is handled explicitly via `useTurnRecovery`.
- Local UI state (`useState`) for messages, errors, session IDs; server state via TanStack Query.

### Error Handling (Frontend)
- `ApiError` carries `status` and optional `code`; error codes match backend `AppError` codes.
- `errorCode(failure)` utility extracts the code safely from unknown errors.
- Distinguish recoverable errors (network, 5xx, `CHAT_TURN_PENDING`) from terminal errors (403, 404, 409 with resource context).
- User-facing error messages come from `chatErrorMessage(failure)` — never expose raw error objects.

### TypeScript Conventions
- Interfaces for public hook contracts; types for unions and aliases.
- `readonly` on all fields of returned state objects.
- Explicit `null` vs `undefined`: use `null` for "intentionally absent" values in state.
- Import types with `import type { ... }` when only used as types.

### File Organization
- Feature-local types in `src/features/<domain>/` (e.g., `chatTypes.ts`).
- Shared types in `src/types/`.
- Service modules in `src/services/<domain>/api.ts` — one file per domain.
- State factory functions (e.g., `userMessage`, `assistantMessage`) in `state/` subdirectories.

### Component and Hook Patterns
- Hooks are the primary abstraction for stateful logic — components stay thin.
- `useEffect` cleanup returns a function that sets `mounted.current = false` and increments epoch.
- `useCallback` wraps all functions passed as props or used in effects.
- Avoid inline object creation in JSX props that would cause unnecessary re-renders.

---

## Database / Supabase

- All queries are tenant-scoped by `institution_id`; Row Level Security enforces isolation at the DB layer.
- Migrations are ordered SQL files in `supabase/migrations/` with timestamp prefixes.
- The admin client (`get_admin_client()`) is used for service-layer operations; never expose it to the API boundary.
- RPCs are used for complex multi-step operations (e.g., student approval).

---

## Testing

### Backend
- Tests live in `backend/tests/`; run with `uv run python -m pytest tests`.
- Physical/live tests (requiring real credentials) are in files named `test_physical_*` and excluded from CI.
- Use `httpx` for API-level tests against the FastAPI app.
- Test doubles for `UploadFile` may use the older no-argument `read()` protocol — production code handles both.

### Frontend
- Tests use Vitest + `@testing-library/react`.
- Test fixtures in `src/test/`; integration support files in `src/__tests__/`.
- `npm run check` runs structure check + build + tests together.

---

## General Conventions
- Never commit `.env` files or real credentials.
- `DEV_TEST_MODE=false` everywhere except local dev/test.
- Run backend commands from `backend/` (config loads `.env` relative to CWD).
- Phase references in comments (`# Phase X.Y`) are intentional — they link code to design decisions in `docs/locks/`.
- Security-sensitive decisions (rate limits, token handling, file validation) always include a comment explaining the constraint and its production implications.
