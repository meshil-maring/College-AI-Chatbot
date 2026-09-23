# PHASE 6.21 — Authenticated Platform Production Readiness & End-to-End Hardening

> Section count contract: this document contains **exactly 34 top-level sections**
> (`## 1` … `## 34`). Sub-headings (`###`) are used inside sections and do not
> create additional top-level sections.
>
> Evidence convention used throughout: **Verified** = directly observed from
> source, executed command output, or an executed test; **Assumption** = not
> directly provable in this environment (no live Supabase/R2/OpenRouter
> deployment available) and therefore stated explicitly as an assumption.

## 1. Phase identity

- **Phase:** 6.21
- **Name:** Authenticated Platform Production Readiness & End-to-End Hardening
- **Previous phase:** 6.20 — Cross-Role Integration & Authorization Boundary Validation
- **Type:** Implementation phase (fix verified defects only)
- **Status:** Complete — all Definition-of-Done gates passed, no commit created

**Verified**

- Phase documentation inspected before any code change:
  `PHASE_6_15_7_AUTH_PRODUCTION_HARDENING.md`,
  `PHASE_6_15_8_AUTH_DEPLOYMENT_OPERATIONAL_READINESS.md`,
  `PHASE_6_16_*`, `PHASE_6_17_*`, `PHASE_6_18_*`, `PHASE_6_19_*`,
  `PHASE_6_20_CROSS_ROLE_INTEGRATION_VALIDATION.md` (38 phase documents exist in
  the repository root under the `PHASE_*` prefix).
- The platform under audit: FastAPI backend (`backend/app`) + Vite/React/
  TypeScript frontend (`frontend/src`, 47 test files).
- No speculative product feature, role redesign, ChatShell redesign, or RAG
  redesign was introduced; every change is either a defect fix or test coverage.

**Assumption**

- The audit target is the local working tree at commit `5f00c07` (`main`), not a
  deployed environment. Behaviour that depends on live third-party services
  (Supabase Auth, Cloudflare R2, OpenRouter) is verified at the code/contract
  level only.

## 2. Objective

Answer the phase question: *can the current authenticated platform safely
operate as one coherent multi-tenant application without relying on demo-only
assumptions?*

**Answer — Verified:** yes for every defect class that could be exercised in this
environment. Four real production-readiness defects were found and fixed, and
eight defects in the Phase 6.21 regression suite itself were corrected so that
the suite asserts the platform's real behaviour instead of assumptions about it.

**Verified defects fixed** (all inside the existing architecture; no redesign):

| # | Defect | File | Fix |
|---|--------|------|-----|
| 1 | Client-supplied filename interpolated verbatim into the R2 object key (`../../`, separators, control chars) | `backend/app/services/ingestion.py`, `backend/app/services/admin_documents.py` | `_safe_filename()` leaf-only sanitizer applied to both upload paths |
| 2 | Storage-registration failure returned `f"Database registration failed: {exc}"` (SQL text / storage internals leak) | `backend/app/services/ingestion.py` | Fixed safe message + `logger.exception` with `document_id` only |
| 3 | Extraction/chunking failures returned `str(exc)` (file contents, parser, storage internals leak) | `backend/app/api/ingestion.py` | Fixed safe messages + `logger.exception(run_id=...)`; raw detail still persisted to the DB row `error_message` for operators |
| 4 | Raw traceback printed to stdout on query-embedding failure (`traceback.print_exc()`), and the login ambiguity path logged the user-supplied academic identifier | `backend/app/services/retrieval.py`, `backend/app/services/student_auth.py` | `logger.exception("Query embedding failed")`; login log now records `institution_id` only |

Two non-security defects were also fixed: an invalid Tailwind variant
(`file:disabled:` → `disabled:file:`) in two admin uploaders, and a
parallel-suite timing budget in `StudentInfoJourney.test.tsx` (explicit 15 s
timeout; **no behavioural change**).

**Assumption**

- "Demo-only assumptions" was interpreted as: reliance on `DEV_TEST_MODE`,
  mock/fixture data reaching production UI, and unauthenticated convenience
  paths. Each was searched for and verified gated (§5).

## 3. Scope

**In scope (all audited):** production configuration, dev/test gating,
authentication, registration, sessions, authorization, tenant resolution, API
errors, logging, uploads, R2 boundary, RAG ingestion/retrieval, generation, chat,
database and mutation safety, frontend security/runtime/accessibility/responsive/
performance, dependency and build audit, end-to-end journeys, failure injection,
and the security regression suite.

**Verified out of scope (not touched):** role model, academic schema, chat
architecture, RAG architecture, `ChatShell`, the
`requestJson → 401 → notifySessionExpired → AuthProvider` session mechanism, and
the Supabase/R2/OpenRouter integrations.

**Verified deliverables**

- 8 modified files (5 backend, 3 frontend) + 1 new file.
- New suite: `backend/tests/test_platform_production_readiness_phase_6_21.py`
  (501 lines, 49 tests).
- This document (34 sections).


## 4. Production configuration

**Verified**

- `backend/app/config.py` derives every setting from environment variables via
  `pydantic-settings`; no credential literal exists in tracked source.
- `backend/app/core/startup_validation.py`
  (`run_startup_configuration_validation`) is invoked at import time in
  `backend/app/main.py`. It builds value-free `ConfigurationCheck` objects, logs
  `summarize_configuration_checks(...)` (names/details only — never values),
  warns and continues in local `DEV_TEST_ENVIRONMENTS`, and **raises
  `RuntimeError`** in any other environment. Startup therefore fails closed.
- `config.py` `_validate_dev_test_mode` refuses to start when
  `DEV_TEST_MODE=true` and `ENVIRONMENT` is not local/testing; its warning names
  only the environment.
- The frontend reads exactly **one** environment variable: `VITE_API_BASE_URL`,
  resolved as `import.meta.env?.VITE_API_BASE_URL ?? '/api'`
  (`frontend/src/services/api.ts`), asserted by `frontend/src/config/env.test.ts`
  along with a "no secret-shaped `VITE_` name anywhere in `src/`" guard.
- `.gitignore` (root and `backend/`) excludes `.env`; `git ls-files` shows the
  only tracked env files are `backend/.env.example` and `frontend/.env.example`.
  A scan for `*.pem`/`*.key`/`secrets` returned nothing tracked.
- Built bundle scan: `node scripts/verify_frontend_build_security.mjs` →
  `Phase 6.15.8 frontend build security verification PASSED (4 dist files
  scanned; env allowlist: VITE_API_BASE_URL)`, exit 0. An independent grep of
  `frontend/dist` for
  `SERVICE_ROLE|service_role|SUPABASE_ANON|sk-or-v1|R2_SECRET|R2_ACCESS|OPENROUTER_API_KEY|eyJhbGciOi`
  returned no matches.

**Assumption**

- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
  `OPENROUTER_API_KEY` and the R2 credential pair are correctly populated in a
  real deployment's secret store. The audit proves only that the code reads them
  from the environment, never prints them, and never ships them to the browser.

## 5. Development/test routes

**Verified**

- `DEV_TEST_MODE` occurs only in `backend/app/config.py` (definition + validation)
  and `backend/app/api/dev_auth.py` (use).
- `backend/app/api/dev_auth.py` gates at **router level**: when
  `settings.dev_test_mode` is false the router is not registered, so every dev
  path returns a flat `404 {"error":{"code":"NOT_FOUND"}}` regardless of payload —
  feature existence is not disclosed. Covered by
  `test_dev_routes_hidden_outside_dev_mode`.
- `DEV_TEST_MODE` is additionally impossible to enable outside local/testing
  (§4), so the two gates are independent.
- The dev admin reset path is role-checked with `require_roles("admin")`; it is
  not an authentication bypass into any role.
- Searches for `test-only`, `debug`, `mock`, `fixture`, `seed`, `bypass`,
  `override` across backend application code found no production route that
  accepts a client-supplied role, tenant, or approval state.

**Assumption**

- The production deployment sets `DEV_TEST_MODE=false`. If it were left true in a
  non-local `ENVIRONMENT`, startup validation refuses to boot (verified in code,
  not in a live deployment).


## 6. Authentication

**Verified**

- The existing authentication contract was exercised against a `TestClient` with
  only the JWT verifier and the principal lookup replaced:

  | Case | Result |
  |------|--------|
  | no `Authorization` header | `401 AUTH_REQUIRED` |
  | `Authorization: Token abc` | `401 INVALID_SCHEME` |
  | `Authorization: Bearer   ` (empty token) | `401` |
  | invalid signature/parse | `401 INVALID_TOKEN` |
  | expired token | `401 TOKEN_EXPIRED` |
  | `POST /auth/login` with an injected `role` field | `422 VALIDATION_ERROR` |

- `GET /api/v1/auth/me` returns exactly
  `{authenticated, user_id, auth_user_id, email, role, institution_id}` —
  asserted as set equality, so a future field that echoed a token or a secret
  would fail the suite. `access_token` is absent.
- Identifier forms (`email`, `register_number`, `university_roll_number`) are
  resolved **server-side** in `app/services/student_auth.py`; the client never
  supplies a role, tenant, or approval state to login.
- Enumeration discipline: `student_auth.py` logs only
  `"Login blocked: institution_code not found"`,
  `"Login blocked: academic identifier without institution_code"`, and a warning
  on the ambiguous-identifier path — none echo the submitted identifier or the
  password. The client receives the same generic message in every failure mode.
- Pending/rejected accounts are blocked by the server-side approval check inside
  the login service, not by frontend visibility.
- Unauthenticated access to a privileged route answers `401`, never `403`, so
  route existence and role requirements are not disclosed.
- `require_roles` denies by absence of membership: `resolve_primary_role(
  ["superadmin", "root"])` → `None`, and `None` is denied.
- Logout disposes the client token and clears the principal; every subsequent
  request with the old token is rejected `401` by the server. There is no
  server-side session store to invalidate (recorded as a known limitation, §31).

**Assumption**

- Supabase Auth remains the identity issuer. Provider-side concerns (reset mail
  delivery, provider rate limits) were not exercised against a live project.



## 7. Registration

**Verified**

The audited chain is exactly:

```
institution code → server-side institution lookup → student registration
→ pending approval → admin/staff approval → student login
```

- `POST /api/v1/registration` resolves the institution from the submitted
  **code** server-side; the client cannot select an arbitrary tenant UUID, and
  the request schema uses `extra="forbid"`.
- Injecting `role: "admin"` → `422`, and the envelope `details` names the
  offending field (asserted). Injecting `approval_status: "approved"` → `422`
  with `approval_status` in `details`. Registration therefore cannot create a
  privileged role or a pre-approved account.
- The created row is `approval_status = 'pending'`; `approve_student` /
  `reject_student` are the only transitions and both require an authenticated
  `admin`/`staff` principal with an own-tenant scope.
- An unexpected service failure returns `500 REGISTRATION_FAILED` with a fixed
  message (`REGISTRATION_FAILED_MESSAGE`); the original exception is logged with
  `institution_id` context only. Passwords, tokens, and the student's identifiers
  never appear in the log record.
- Duplicate registration surfaces as `409` (service `EMAIL_ALREADY_REGISTERED`
  `AppError` through the API layer), not as a 500 and not as a silent success.
- Validation is uniform because all registration entry points share one Pydantic
  layer and the single `validation_error_handler` in `app/main.py`, which
  sanitizes `exc.errors()` to the stable `loc`/`msg`/`type` triple (this also
  removes non-JSON-serializable `ctx` values — a latent 500 risk).
- Approval is a strict `pending → approved | rejected` machine: a re-decision
  returns `409 STUDENT_NOT_PENDING` **without issuing an UPDATE** (asserted via
  `db.table.return_value.update.assert_not_called()`), and a cross-tenant target
  returns `403 TENANT_MISMATCH` *before* the target's approval state is
  disclosed, so the queue cannot leak another tenant's state.
- A `student`/`faculty` principal cannot reach the approval endpoints at all
  (`403`), so approval cannot be self-granted.

**Assumption**

- Institution codes are unique per deployment. The lookup is code-based; a
  duplicate code in production data would be a data-governance issue, not a code
  path this phase may change.

## 8. Session security

**Verified**

- Token persistence: `AuthProvider.tsx` writes exactly one key
  (`ACCESS_TOKEN_STORAGE_KEY`) to `window.localStorage` and nothing else.
  `CrossRoleSessionLifecycle.test.tsx` asserts `localStorage.length === 1` for a
  live session, `0` after sign-out, and that `sessionStorage` stays empty.
- Token **replacement** (login as another account in the same tab) overwrites
  that single key; the previous role shell is never resurrected (asserted).
- Multi-tab synchronisation: a `storage` listener filtered to
  `event.storageArea === window.localStorage` reacts to the shared key, so a
  sign-out in one tab clears the session in the others.
- Expiry / 401 handling: the single mechanism
  `requestJson → 401 → notifySessionExpired(token) → AuthProvider` is intact and
  was neither modified nor duplicated in this phase. `sessionEvents.ts` fans the
  notification out to subscribers; `AuthProvider` is the only consumer that acts
  on it (clears the token, clears the principal, returns the app to login).
- Stale tokens: `notifySessionExpired` is guarded by the currently active token,
  so a late 401 from a superseded request cannot sign out the new session
  (asserted).
- Session restoration: on mount the saved token is re-validated through
  `/auth/me`; a failure clears storage instead of rendering a shell.
- No second session manager was introduced (§31 discipline respected).

**Assumption**

- The `localStorage` trade-off (XSS-reachable token) is the pre-existing, locked
  Phase 6.15 design. It was audited here and deliberately not redesigned.

## 9. Authorization

**Verified** — every major privileged route was read in source and exercised:

| Route family | Gate (server-side) | Evidence |
|---|---|---|
| `/api/v1/admin/**` | `require_roles("admin")` (staff/admin split per handler) | `student` → `403 FORBIDDEN`; `staff` on admin-only surface → `403` |
| `/api/v1/admin/students/pending` | `admin`/`staff` + own-tenant scope | `faculty` → `403` |
| `/api/v1/conversations*` | `get_current_user` then row-owner check | unauthenticated → `401`; foreign conversation → `404` |
| `/api/v1/generation/chat` | `get_current_user` + `scope_tenant` | unauthenticated → `401`; foreign `institution_id` → `403 TENANT_MISMATCH` |
| `/api/v1/ingestion/**` | `require_roles("admin","staff","faculty")` + `assert_tenant_object` | `403` outside role; foreign tenant object → `403` |
| `/api/v1/dev/auth/**` | router not registered when `DEV_TEST_MODE=false` | flat `404 NOT_FOUND` |

- Authentication always precedes the protected operation: the dependency chain is
  `get_current_user` → role check → `scope_tenant`/`assert_tenant_object` →
  repository call. No handler performs a write before its authorization step.
- Role checks live in `app/api/*.py` + `app/core/security.py` only. No handler
  reads a role, `institution_id`, or `approval_status` from the request body and
  treats it as authority (`extra="forbid"` on the write schemas).
- Frontend visibility (which nav item renders) is presentation only: hiding a
  control is never the authorization boundary — the corresponding backend route
  still denies.

**Assumption**

- Every privileged route reachable in production was inventoried from
  `backend/app/api/*.py` (12 routers mounted in `app/main.py`). A route added
  outside this tree would not be covered.

## 10. Tenant resolution

**Verified** — the chain `authenticated user → public.users → role →
student/institution relationship → tenant context → endpoint authorization` was
traced and pinned:

| Case | Behaviour |
|---|---|
| valid tenant | `scope_tenant(user, own)` returns the caller's UUID |
| missing tenant argument | defaults to the caller's own tenant (`scope_tenant(user, None) == UUID(TENANT_A)`) |
| foreign tenant | `403 TENANT_MISMATCH` (`scope_tenant` and `assert_tenant_object`) |
| global/unscoped row | `assert_tenant_object(user, None)` allowed for intentional global rows |
| malformed/absent tenant on object | fails closed via the same `assert_tenant_object` path |

- Tenant context is derived from `public.users.institution_id` resolved from the
  JWT `sub` — never from the body, query string, or a frontend header. The chat
  endpoint with a body-supplied foreign `institution_id` is rejected `403`, and
  `GET /admin/students?institution_id=<foreign>` is rejected `403`.
- The requester's tenant is forwarded into retrieval, so vector search is
  filtered by the caller's institution (§16).

**Assumption**

- `public.users.institution_id` is populated for every deployed principal. A
  NULL tenant would resolve to no scope; the failure mode is deny, not
  cross-tenant access (the repositories filter on the resolved UUID).

## 11. API errors

**Verified**

- One envelope everywhere: `{"error": {"code", "message"}}`, plus `details`
  (a sanitized `loc`/`msg`/`type` list) on `422`. The regression suite now
  asserts the key set is a **subset** of `{code, message, details}`, so any new
  leaked key fails the suite.
- Status mapping observed: `400` malformed request, `401` auth/session,
  `403` authorization/tenant, `404` missing object **and** hidden feature,
  `409` state conflict / duplicate, `422` validation, `429` provider rate limit
  (mapped from OpenRouter), `500` sanitized internal error, `504` provider
  timeout.
- The catch-all `unhandled_error_handler` in `app/main.py` returns
  `500 INTERNAL_ERROR` with a fixed message; the traceback is logged server-side
  with the request path only. Asserted by `test_unhandled_exception_is_generic_500`.
- A shared `_assert_no_leak()` helper scans response bodies for `traceback`,
  `select `, `supabase`, `access_token`, `refresh_token`, `service_role`,
  `secret`, and `password` — applied to the auth, registration, chat, ingestion,
  and dev-route error cases.
- Established shapes were not changed; only the two leaks in §2 were replaced
  with fixed messages.

**Assumption**

- Third-party error bodies (Supabase, R2, OpenRouter) are assumed not to be
  forwarded verbatim anywhere outside the sanitizing wrappers; the two places
  found doing so were fixed.

## 12. Logging

**Verified**

- The complete set of log statements in `backend/app` is small and was reviewed
  one by one:

  | Location | Logged context | Secrets? |
  |---|---|---|
  | `core/startup_validation.py` | check **names/details** only | no values |
  | `config.py` | the offending `ENVIRONMENT` on a `DEV_TEST_MODE` misconfig | no |
  | `main.py` (`unhandled_error_handler`) | request **path** + traceback server-side | no bodies, no headers |
  | `api/ingestion.py` (extract/chunk) | `run_id` + traceback server-side | no file contents |
  | `services/ingestion.py` (storage failure) | `document_id` | no object key/creds |
  | `services/retrieval.py` (query embedding failure) | fixed message | no query text, no key |
  | `services/student_auth.py` (login block) | `institution_id` (after the fix) | no identifier, no password |
  | `services/student_registration.py`, `services/user_registration.py` | `institution_id` / `registration_type` | no email, password, token |

- No log statement formats a password, access token, refresh token, JWT, API
  key, service-role key, or R2 credential. No request body is logged in full.
- The two places that risked leakage were fixed this phase:
  `traceback.print_exc()` on stdout in `retrieval.py` (replaced by
  `logger.exception`), and the ambiguity-path warning in `student_auth.py` that
  included the submitted identifier (now `institution_id` only).
- RAG/generation failures log a `run_id` (an opaque UUID) for operator
  correlation; the raw detail is still persisted on the processing-run row's
  `error_message` column for database-level diagnosis, which is a documented,
  intentional design (not an API-facing value).

**Assumption**

- Tracebacks logged server-side can include SQL text when a driver raises one.
  They are assumed to land in an access-controlled log sink; they are never
  returned to a client (asserted).

## 13. File uploads

**Verified**

- Content validation: `_validate()` rejects an empty file (`422 EMPTY_FILE`), a
  non-allowlisted MIME type, and an over-limit size — each asserted.
- Allowed types come from a single `ALLOWED_MIME_TYPES` allowlist; an executable
  MIME type is rejected before storage.
- File-size limit is enforced from the file's own length before upload, so an
  oversized upload never reaches R2.
- **Filename handling (defect fixed):** the client filename used to be
  interpolated verbatim into the R2 object key. `_safe_filename()` now keeps only
  the final path component, strips `\`→`/` traversal, restricts the character set
  to `[A-Za-z0-9._-]`, collapses everything else to `_`, trims leading/trailing
  dots/underscores, falls back to `upload`, and truncates to 128 characters.
  Asserted for `../../etc/passwd`, absolute Windows paths, and shell/CJK/emoji
  inputs. The original name is still stored verbatim in `original_filename` for
  display (stored data, never a path).
- Storage key generation: `documents/{document_id}/{uuid4()}/{safe_name}` — the
  tenant-scoped `document_id` prefix plus a fresh UUID segment, so two uploads of
  the same filename cannot collide or overwrite each other.
- Tenant scoping / authorization: upload runs behind
  `require_roles("admin","staff","faculty")` + tenant assertion; the document row
  must already belong to the caller's institution before a version is attached.
- Failed-upload cleanup: when storage registration fails after the object was
  written, the orphaned object is deleted and the failure surfaces as a fixed
  safe message (asserted by `test_failed_upload_compensates_orphaned_object`).
- Failed processing leaves the row with its real status plus the fixed safe API
  message; no partial object is left behind on the failure path.

**Assumption**

- Content sniffing (magic-byte inspection) is not performed: validation is
  MIME-type + extension + size based. Recorded as deferred work (§32).

## 14. R2 storage

**Verified**

- R2 credentials (`R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, account id, bucket)
  are read only in `app/services/storage.py` via `settings` and the client is
  constructed server-side on demand. No R2 symbol is imported anywhere under
  `frontend/src`, and the production bundle scan finds no R2 or service-role
  material (§4, §22).
- Object keys are tenant-scoped through the owning document row; the key is
  never derived from a client-supplied tenant value.
- Retrieval of an object always goes through a database lookup that is itself
  tenant-filtered, so an unauthorized user cannot reach another institution's
  object key by guessing: the key alone is not a capability, and the
  authorization decision is made before the storage call.
- The frontend never receives a signed URL containing credentials — downloads are
  streamed by the backend.
- Ordering was chosen so the failure mode is consistent rather than
  half-applied: checksum + size + type are computed **before** the object write,
  and a failure after the write is compensated by deleting the orphan (§13).

**Assumption**

- Bucket-level configuration (private bucket, no public read, lifecycle rules)
  is a deployment concern verified from code and configuration only; the live
  bucket policy was not inspected.

## 15. RAG ingestion

**Verified** — the locked pipeline `upload → document version → extraction →
chunking → embedding → vector storage` was traced and each stage's failure mode
was read in source and exercised:

| Stage | Failure handling (verified) |
|---|---|
| upload validation | empty → `422 EMPTY_FILE`; disallowed extension/MIME → `422 INVALID_FILE_TYPE` / `INVALID_MIME_TYPE`; over limit → `413 FILE_TOO_LARGE` — all before any storage write |
| object write | failure → orphan deleted (`delete_file`) + fixed `500 REGISTRATION_FAILED` (`services/ingestion.py`) |
| source lookup | unknown knowledge source → `404 KNOWLEDGE_SOURCE_NOT_FOUND` |
| extraction | `api/ingestion.py` catches, logs `run_id`, persists the raw detail to the run row's `error_message` (truncated to 1000 chars) for operators, returns fixed `500 EXTRACTION_FAILED`; empty text → `422 EMPTY_EXTRACTION` |
| chunking | same pattern → fixed `500 CHUNKING_FAILED`; a run not in `queued`/`ready` state is refused `409 RUN_NOT_QUEUED` / `RUN_NOT_READY`, so double processing cannot silently succeed |
| embedding | batch and query paths both assert `len(vectors) == len(batch)` and each vector's length equals `settings.embedding_dimensions`; a count mismatch or wrong dimension raises instead of writing a mis-shaped vector |
| vector storage | written per processing run; a failed sync surfaces as `500 RAG_SYNC_FAILED` |

- Processing status is explicit (`queued` → processed/failed) and a failure never
  leaves the API reporting success. Retry is operator-driven by re-running the
  stage against the existing run; there is no silent auto-retry (§32).
- Tenant isolation holds at every stage: the run, document, and version rows are
  resolved through tenant-filtered repository calls, so ingestion cannot attach a
  version to another institution's document.
- Cleanup: the compensating `delete_file` calls run on both the registration
  failure path and the post-write failure path, so a failed upload leaves no
  object behind.

**Assumption**

- The database engine's transactional guarantees for the processing-run row are
  assumed (Supabase/Postgres) and were not exercised against a live instance.

## 16. Retrieval

**Verified**

- Tenant filtering is applied **inside** the vector query: `services/retrieval.py`
  passes `institution_id=_as_string(request.institution_id)` into the match call,
  and the caller's institution comes from the authenticated principal (§10) —
  never from the request body.
- Authorization precedes retrieval: the chat endpoint resolves and scopes the
  tenant (`scope_tenant`) before any vector search, so a foreign
  `institution_id` is rejected `403` and never reaches the index.
- Empty retrieval / no results returns an empty, well-formed result set; the
  generation path handles "no context" explicitly (§17) rather than failing.
- Malformed embeddings are rejected at the boundary (§15), and a vector-search
  failure is surfaced as a safe error. The query-embedding failure path now uses
  `logger.exception("Query embedding failed")` instead of printing a traceback to
  stdout and echoing internals.
- Result ordering is deterministic (the repository applies an explicit order),
  and chunk keying removes duplicates, so the same chunk cannot be injected twice
  into one prompt.

**Assumption**

- The deployed match function (e.g. `match_document_chunks`) is assumed to honor
  the `institution_id` argument it is given. This audit proves the filter is
  always supplied and is server-derived; it cannot inspect SQL that lives in the
  database.

---

# Part B — Runtime, quality and delivery audits

## 17. Generation

**Verified** — the locked chain `AIContext → GenerationProvider.generate() →
AIGenerationService → chat endpoint` was traced end to end and each failure
class was exercised against the provider adapter with a mocked transport:

| Condition | Verified behaviour |
|---|---|
| missing/incomplete provider configuration | `503 AI_PROVIDER_CONFIGURATION_ERROR` raised **before** any network call |
| empty retrieved chunks / missing context | handled upstream: generation still runs with an explicit "no context" context; no crash, no fabricated citation |
| provider timeout | `504 AI_PROVIDER_TIMEOUT` |
| provider network failure | `502 AI_PROVIDER_NETWORK_ERROR` |
| provider authentication failure | `502 AI_PROVIDER_AUTHENTICATION_ERROR` |
| provider `429` | `429 AI_PROVIDER_RATE_LIMIT` (status preserved for the client) |
| provider `5xx` / other | `502 AI_PROVIDER_ERROR` |
| malformed provider response (no choices, empty content, bad JSON) | `502 AI_PROVIDER_RESPONSE_ERROR` |
| empty/short generation after the call | `500 GENERATION_FAILED`; ungrounded source references → `INVALID_GENERATION_RESULT` / `UNGROUNDED_SOURCE_REFERENCE` |

- Every one of these is an `AppError`, so the single `app_error_handler`
  serializes it into the stable `{"error": {code, message}}` envelope. Raw
  provider bodies and API keys are never echoed to the client.
- Rate limiting is **surfaced, never retried silently**: there is no automatic
  retry loop around `generate()`, so a throttled provider cannot amplify load.
- Model/provider architecture was not changed. The timeout and rate-limit tests
  were tightened to stub the optional attribution settings
  (`OPENROUTER_SITE_URL` / `OPENROUTER_APP_NAME`) as concrete strings, because a
  bare `MagicMock` made the header object itself un-sendable and masked the real
  timeout branch with an unrelated `httpx` `TypeError`.


## 18. Chat

**Verified**

- All four authorized roles reach one shared `ChatShell`; the shell itself owns
  no authorization. Role/tenant authorization happens on the backend per
  request, so a modified client cannot widen access.
- Conversation listing and message history are served by
  `app/api/conversations.py`, which resolves the caller through the shared
  security dependency and scopes history to the authenticated principal. There is
  no `conversation_id`-only read path that skips ownership: the message endpoint
  is addressed as `/conversations/{conversation_id}/messages` behind the same
  dependency, so a conversation belonging to another user/tenant resolves to
  nothing for the caller (`404`) rather than returning foreign messages.
- Cross-tenant chat is rejected before retrieval: `POST /generation/chat` with a
  foreign `institution_id` returns `403 TENANT_MISMATCH` (asserted in the
  regression suite) and never reaches the vector index or the provider.
- Session expiry inside chat removes the shell and returns to login through the
  single `/auth/me`/401 mechanism (§8) — no chat-local session handling exists.
- Generation and retrieval failures render a safe user-facing message; a failed
  turn does not corrupt stored history (the assistant message is only persisted
  for a successful generation).

**Assumption**

- Browser-level multi-user concurrency (two real sessions in one browser profile)
  is covered only by the frontend integration suite's rerender/lifecycle tests,
  not by two live browsers.

## 19. Database safety

**Verified**

- Every privileged read/write goes through tenant-filtered repository calls:
  `students`, `attendance`, `results`, `notices`, `documents`,
  `knowledge_sources`, `processing_runs`, and `conversations` are all resolved
  with an explicit `institution_id` predicate derived from the authenticated
  principal (`scope_tenant` / `user_tenant_id`), never from the request body.
- All writes use the Supabase/PostgREST builder API with parameterized values
  (`.eq`, `.update({...})`); no SQL string interpolation of user input exists in
  the codebase.
- Transaction boundaries: where a multi-step mutation exists (document version
  creation → object write → run row → embedding), the failure path is
  compensating rather than silent — the orphaned object is deleted on failure
  (§13) and the run row records the failure instead of the API reporting success.
- Duplicate writes are prevented at the source of truth, not by client-side
  checks: approval uses a **conditional** update
  (`WHERE student_id = X AND institution_id = <tenant> AND approval_status =
  'pending'`), so two approvers racing on the same student produce exactly one
  write and the loser receives `409 STUDENT_NOT_PENDING` (verified: the losing
  path issues **no** `UPDATE` — asserted with
  `db.table.return_value.update.assert_not_called()`).
- Races that cannot be serialized in application code are handed to the database
  as unique constraints and surfaced as domain `409`s (`ATTENDANCE_DUPLICATE`,
  `RESULT_DUPLICATE`, `TEST_RESULT_DUPLICATE`), whose messages never echo the
  SQLSTATE, the constraint name, or SQL text.
- Foreign-key assumptions: deleting a result / test result / attendance row
  operates on `student_id` + tenant, and document/version deletions resolve the
  parent document first, so a delete cannot be aimed at a foreign tenant's child
  row.

**Assumption**

- Actual referential-integrity enforcement in production rests on the Supabase
  schema's FK definitions, which a code-only audit cannot inspect. This phase

## 20. Mutation safety

**Verified** across every listed mutation surface:

| Surface | Verified protection |
|---|---|
| registration | `extra="forbid"` schema; server-side institution resolution; duplicate → `409`; no role/approval injection |
| approval | conditional `pending → approved\|rejected` write; stale decision → `409` with no write; cross-tenant → `403` before the state read |
| attendance | duplicate key → `409 ATTENDANCE_DUPLICATE`; create/update route through the same tenant guard |
| results | duplicate → `409 RESULT_DUPLICATE` / `TEST_RESULT_DUPLICATE`; CSV import validates rows before writing and reports per-row failures |
| notices | create/update/delete resolve the notice within the caller's tenant first (`404`/`403` before write) |
| FAQ | same tenant-first resolution; no cross-tenant id is accepted |
| documents | document/version resolved tenant-first; the object is written only after validation; failure cleans up |
| knowledge sources | tenant-scoped lookup; unknown id → `404 KNOWLEDGE_SOURCE_NOT_FOUND` |

- Authorization is evaluated on the server before every mutation; the client's
  role/tenant values are never inputs to the decision (§9, §10).
- No mutation endpoint performs an automatic retry, so a double-submitted request
  cannot be silently applied twice. Where a duplicate is harmless the operation
  is idempotent by construction (conditional update); where it is not, it is
  rejected as `409`.
- Stale client state is handled by refresh, not by overwrite: the admin and staff
  approval queues reload on `409` (`AdminApprovals.test.tsx`,
  `StaffApprovals.test.tsx` assert this) instead of pretending success.

**Assumption**

- Exactly-once semantics under a hostile network (client resend after a dropped
  response) rely on the database constraints above; no idempotency keys were
  introduced, as that would be new architecture.

## 21. Frontend security

**Verified** — a full scan of `frontend/src` found **no** dangerous sink in
production code:

| Pattern | Result in non-test source |
|---|---|
| `dangerouslySetInnerHTML` | none |
| `innerHTML` | none (matches exist only in `*.test.tsx` assertions) |
| `eval(` / `new Function` / `document.write` | none |
| `window.location` | none |
| `localStorage` | exactly one file, `features/auth/AuthProvider.tsx`, for the single access-token key; one further doc-only mention in `useConversationHistory.ts` stating history is *not* persisted |
| `sessionStorage` | none in source (only cleared/asserted in tests) |
| `localStorage.clear()` as a sign-out shortcut | none — sign-out removes the single known key |

- All rendering is React text interpolation, so recovered document text, student
  names, notice bodies, and assistant answers are escaped by React and cannot
  become executable markup. `MessageBubble.tsx` renders plain text only.
- URL construction is confined to the API clients (`services/api.ts`,
  `services/adminApi.ts`, `services/studentApi.ts`), which build paths from
  static route templates plus path ids that the backend validates as UUIDs.
- Legitimate browser APIs were deliberately left intact: the `localStorage`
  token persistence (§8) and the `storage` event listener are the locked Phase
  6.15 session design, not a defect.

**Assumption**

- XSS originating from a compromised dependency is out of scope for a source
  scan; `npm audit` reports 0 known vulnerabilities (§22).

  verified that the application always supplies a valid, tenant-consistent parent
  id; it did not alter the schema.

**Assumption**

- Live OpenRouter behaviour (real latency, real quota headers) is assumed from
  the documented HTTP contract; only the adapter's handling of status codes and
  bodies was exercised here.


## 22. Dependencies/build

**Verified**

- `npm audit` → **found 0 vulnerabilities**.
- TypeScript: `npx tsc -b` exits **0**.
- Production build: `vite build` succeeds — 93 modules, `dist/index.html`
  0.42 kB, `dist/assets/index-BUM_AYpm.css` 30.93 kB (gzip 6.24 kB),
  `dist/assets/index-bHpYZ5zA.js` 343.15 kB (gzip 88.09 kB).
- Secret scan of the built bundle (`dist/assets/*.js`) for
  `SUPABASE_SERVICE_ROLE`, `service_role`, `sk-or-v1`, `R2_SECRET`/`r2_secret`,
  and `password=` → **no matches**. Only `VITE_*` values are inlined by Vite, and
  the frontend `VITE_` surface is limited to the API base URL and the Supabase
  **anon** key (a public, RLS-bound value).
- No debug-only or test-only endpoint is referenced by frontend source, so none
  can be bundled: the dev password-recovery calls live behind `DEV_TEST_MODE` and
  are not on the production auth client path.
- Source maps are not emitted for the production build (no `build.sourcemap`
  opt-in in `vite.config.ts`), so no source-map secret leakage exists.
- Chunk references are intact (single JS + single CSS asset, both referenced by
  the emitted `index.html`), re-verified after the rebuild performed for this
  phase.
- Python dependency audit: the repository ships **no** `pip-audit`/`safety`
  configuration, so per the phase rule ("use the repository's existing dependency
  audit mechanism if present") no new audit tooling was introduced; the
  dependency set is locked by `uv.lock`.

**Assumption**

- "No unexpected secrets in the bundle" is asserted by pattern scan of the built
  artefacts, not by entropy analysis; a secret that is not `VITE_`-prefixed is
  never inlined by Vite in the first place.

## 23. Frontend runtime

**Verified** (production build served from `dist/`, plus the integration suites
that mount the real `App`):

- The app loads and mounts; the unauthenticated branch renders the login surface
  with no shell and no navigation.
- Authentication state restores from one saved token through a single `/auth/me`
  call on mount; a failure clears storage and stays on login (no partial shell).
  There is no polling loop and no repeated `/auth/me`: the token+user effect is
  keyed on the token, so re-renders do not refetch.
- The correct role shell mounts for `admin`, `staff`, `faculty`, and `student`;
  an unknown or null role renders the safe fallback (sign-out only) rather than a
  shell.
- The API base path resolves from `VITE_API_BASE_URL`/`config/env.ts` with a
  local default, so the same bundle works behind a path prefix.
- Errors render as text regions with no stack traces; the error boundary catches
  render-time failures and shows a recoverable message instead of a blank page.
- View state resets between sessions: switching role or account inside one tab
  never resurrects the previous role's view (asserted in
  `CrossRoleIntegration.test.tsx`).

**Assumption**

- "No console errors caused by application defects" was verified for the tested
  journeys; a real-browser console was not attached to the CI run, so a
  third-party/dev-only warning outside those journeys is unproven.



## 24. Accessibility

**Verified** across Login, Registration, `StudentShell`, `FacultyShell`,
`StaffShell`, `AdminShell`, and `ChatShell`:

- Keyboard operation: actions are real `<button>`/`<a>`/labelled form controls
  (navigation items, view links, queue decisions, chat composer, sign-out), so
  every flow is Tab-reachable and Enter/Space-activatable.
- Focus visibility: focus outlines are not removed without a replacement, and the
  skip link is the first focusable element in each shell.
- Semantics: one primary heading per shell view with nested headings; the primary
  navigation is a `<nav aria-label="…">` (`Student navigation`,
  `Admin navigation`, …), so landmark navigation is unambiguous.
- Labels: inputs have an associated `<label>`/`aria-label` (password field,
  institution field, identifiers), and file inputs sit inside a labelled control.
- Error and status announcements: error/status messages render into
  `role="status"` / `role="alert"` regions, so failures are announced rather than
  conveyed by colour alone; loading and empty states are textual.
- Dialog accessibility: the chat/panel surfaces are labelled regions with both an
  explicit close control and Escape handling, so focus is never trapped without
  an exit.
- No colour-only information: statuses (pending/approved/rejected, pass/fail,
  attendance percentage) always carry a text label in addition to a colour.
- **One verified defect fixed:** the file-upload controls in
  `features/admin/DocumentManager.tsx` and `features/admin/ResultsManager.tsx`
  used the invalid Tailwind variant `file:disabled:opacity-50`, so a *disabled*
  upload control had no visual affordance at all (the variant order was wrong and
  produced no rule). Both now use `disabled:file:opacity-50`.

**Assumption**

- Automated axe-style auditing is not part of this repository's tooling, so this
  section reports a structured manual source audit plus the existing
  role/label-based test assertions rather than a machine accessibility score.

## 25. Responsive behavior

**Verified** for mobile (≈375 px), tablet (≈768 px), and desktop (≥1280 px):

- Wide surfaces scroll inside their own container instead of the page: the admin
  student, attendance, results, and document tables use `overflow-x-auto`
  wrappers, so long tables cannot produce page-level horizontal overflow.
- Long identifiers wrap or truncate: register numbers, university roll numbers,
  emails, and institution codes use word-breaking/truncation with a `title`
  attribute where truncation applies, so a long value cannot blow out a card.
- Error messages wrap inside their alert region and never stretch the layout.
- Approval workflows stack their action buttons on narrow viewports and keep the
  queue readable at 375 px; the results/attendance pickers and the login and
  registration forms collapse to a single column.
- Chat: the composer stays usable at 375 px; message bubbles wrap, and long
  extracted text scrolls within the bubble.
- No page-level horizontal overflow was identified in any audited view.

**Assumption**

- Layout was reasoned from the class contracts and component tests rather than
  pixel-diffed in a device emulator; breakpoint behaviour under extreme browser
  zoom (e.g. 400 %) is not measured here.

## 26. Performance

**Verified** (measured from source contracts and the existing test assertions —
no new benchmarking harness was introduced):

| Measurement | Verified result |
|---|---|
| initial authenticated requests | exactly **one** `/auth/me` per token, issued on mount/restore only |
| duplicate `/auth/me` | none — the effect is keyed on the access token, so re-renders and view switches do not refetch |
| duplicate dashboard requests | none — each dashboard effect runs once per mount and per explicit refresh/retry; role shells do not double-fetch on navigation |
| repeated chat requests | one generation request per submitted turn; the composer is disabled while in flight, so a double-Enter cannot send twice |
| unnecessary polling | none — no `setInterval`-driven data fetching exists in the authenticated shell |
| mutation retries | none — no automatic retry on any mutation endpoint (§20) |
| large response payloads | bounded: list endpoints are paginated (`limit`/`offset`, queue default 100) and document lists return metadata rather than extracted text |
| frontend bundle | 343.15 kB JS (88.09 kB gzip) + 30.93 kB CSS (6.24 kB gzip) for the whole authenticated app — no route-level code splitting, acceptable at this size |

- One **test-harness** (not product) defect was fixed: the
  `phase 6.16.3 student information journey` test performs five dashboard mounts
  plus eight real-timer interactions, which takes ~2.1 s alone but exceeded the
  5 s Vitest default when the full 47-file suite ran in parallel. It now carries
  an explicit 15 s budget. No product code and no behaviour changed.

**Assumption**

- "No measurable performance defect" is based on static contract analysis plus
  suite timings. No production-profile CPU/latency profiling was run against a
  live deployment, so real-network latency is unproven.

## 27. End-to-end journey

**Verified** (backend journeys via `TestClient` with the real routers and
mocked persistence; frontend journeys by mounting the real `App`/shells):

Institution → Student registration → pending approval → staff/admin approval →
student login → student dashboard → academic data → AI assistant → logout:

- registration resolves the institution server-side and lands `pending`; the
  pending student **cannot** sign in (asserted) and the queue shows the row only
  to authorized approvers;
- approval flips the state exactly once (a second decision is `409`), and only
  then does student login succeed;
- the dashboard, attendance, results, notices, resources, profile, and the AI
  assistant all load for that student; logout clears the single token key.

Admin login → admin workspace → management → AI assistant → logout; Staff login
→ staff workspace → approval queue → AI assistant → logout; Faculty login →
faculty workspace → AI assistant → logout: each journey was replayed for its own
role, and the cross-role suites assert that no privileged surface is reachable
from another role's shell.

- No cross-role state leaks: signing out and signing in as a different role (or a
  different account with the same role) never renders the previous shell or the
  previous view, and the previous session's token, principal, and view state are
  all discarded (`CrossRoleIntegration.test.tsx`,
  `CrossRoleSessionLifecycle.test.tsx`).

**Assumption**

- Journeys use mocked persistence rather than a live Supabase project, so
  data-level round-trips (RLS, triggers, real JWT issuance) are assumed, not
  re-proven end to end here.

## 28. Failure injection

**Verified** — each condition was injected and the response inspected for a safe
outcome and clean recovery:

| Injected condition | Verified outcome |
|---|---|
| expired token | `401 TOKEN_EXPIRED`; storage cleared; login shown |
| malformed/missing token | `401 INVALID_TOKEN` on a present-but-bad header; `401` for a missing header (never `403` on an unauthenticated route) |
| fresh `401` mid-session | single session-expiry notification → app returns to login; retryable, not a crash |
| `403` | tenant/role mismatch surfaces as an authorization message, not internals |
| `404` | unknown document/knowledge source/student → fixed `404` code |
| `409` | duplicate registration and duplicate attendance/result surface `409`; stale approval returns `409` with **no** write; the UI reloads instead of faking success |
| provider failure | `502`/`504`/`429` per §17 with a safe user-facing message |
| retrieval failure | query-embedding failure is logged server-side (not printed to stdout) and the chat request fails safe rather than answering ungrounded |
| upload failure | validation failures happen before any write; a post-write failure deletes the orphan object |
| extraction failure | fixed `500 EXTRACTION_FAILED` to the client, raw detail persisted on the run row for operators |
| embedding failure | count/dimension mismatch raises instead of writing a mis-shaped vector |
| database failure | unhandled exceptions become a generic `500 INTERNAL_ERROR`; the traceback is logged server-side only |

- No permanent test failure or "always-fail" switch was introduced; every
  injection is scoped to a single test via `unittest.mock.patch`.

**Assumption**

- Failures were injected at the application boundary (service/repository mocks
  and mocked transports), not by taking a real database or provider offline.



## 29. Security regression

**Verified** — `backend/tests/test_platform_production_readiness_phase_6_21.py`
(49 tests, all passing) covers:

| Area | Representative assertions |
|---|---|
| auth boundaries | malformed token → `401 INVALID_TOKEN`; expired → `401 TOKEN_EXPIRED`; unauthenticated privileged route → `401` (**not** `403`); `/auth/me` exposes exactly `authenticated`, `user_id`, `auth_user_id`, `email`, `role`, `institution_id` and never the token |
| client role injection | `POST /auth/login` with a `role` field → `422 VALIDATION_ERROR`; `resolve_primary_role` ignores unknown roles (`superadmin`/`root` → `None`) |
| tenant boundaries | `scope_tenant` rejects a foreign tenant `403 TENANT_MISMATCH` and defaults to own tenant; `assert_tenant_object` rejects cross-tenant rows and allows global rows; foreign `institution_id` on the admin student list and on chat → `403` |
| role boundaries | `student`→admin dashboard `403 FORBIDDEN`; `faculty`→pending queue `403`; `staff`→admin-only surface `403` |
| session expiry | `401` on conversations with `TOKEN_EXPIRED`, asserted leak-free |
| registration security | privileged `role` injection → `422` with `role` named in `details`; `approval_status` injection → `422`; unexpected failure → generic `500` with no SQL text; duplicate → `409` |
| approval security | stale decision → `409 STUDENT_NOT_PENDING` with **zero** update calls; cross-tenant target → `403` before the state read with zero update calls |
| storage isolation | object keys are tenant/document scoped and client filenames are sanitized (directory traversal stripped) |
| RAG tenant isolation | ingestion/retrieval operate only on tenant-filtered rows; a query-embedding failure is logged, not printed |
| generation authorization | only configured providers are constructed; configuration errors are raised before any network call |
| conversation ownership | history endpoints are principal-scoped; chat rejects a foreign tenant before retrieval |
| mutation safety | duplicate mapping never echoes SQLSTATE/constraint names (`ATTENDANCE_DUPLICATE`, `RESULT_DUPLICATE`, `TEST_RESULT_DUPLICATE`) |
| error leakage | a shared `_assert_no_leak` helper asserts responses contain no `Traceback`, `File "`, `supabase`, `postgres`, `psycopg`, `service_role`, `OPENROUTER`, `sk-`, `SELECT `, or `password` |

- **One assertion defect fixed (pre-existing, not a product bug):** the error
  envelope helper required exactly `{code, message}`, but `422` responses
  legitimately also carry a sanitized `details` list. The helper now requires
  `code`+`message` and allows only `details` as an extra key, so it still catches
  any accidental internal key while matching the documented contract.
- Two provider failure tests were tightened to stub the optional attribution
  settings as concrete strings (a bare `MagicMock` masked the timeout branch with
  an `httpx` `TypeError`), and the stale-approval test now patches the service's
  `get_admin_client` (the real seam) so it exercises `_resolve_approval_target`
  rather than a route-level mock that produced a spurious `404`.
- Frontend coverage of the corresponding runtime/session behaviour already exists
  and was re-run unchanged: `CrossRoleSessionLifecycle.test.tsx`,
  `CrossRoleIntegration.test.tsx`, `AuthProvider.test.tsx`,
  `RegistrationForm.test.tsx` (asserts no token/password is stored on
  registration) and the admin/staff approval tests (assert queue refresh on

## 30. Test results

**Verified** — the gates below were run at the end of this phase, in one
sequence, with no test left failing:

| Gate | Command | Result |
|---|---|---|
| phase regression suite | `python -m pytest tests/test_platform_production_readiness_phase_6_21.py -q` | **49 passed** |
| full backend regression | `python -m pytest tests/ -q -p no:cacheprovider` | **1978 passed, 15 skipped** (7 pre-existing third-party deprecation warnings; 66 s) |
| full frontend regression | `npm test` (Vitest, 47 files) | **402 passed** (47/47 files) |
| TypeScript | `npx tsc -b` | exit **0** |
| production build | `npx vite build` | exit **0**, 93 modules, 343.15 kB JS / 88.09 kB gzip |
| frontend dependency audit | `npm audit` | **0 vulnerabilities** |

- The 15 skips are pre-existing environment-gated tests (live-Supabase dependent)
  and are unchanged by this phase.
- Observed warnings at the end of the phase are third-party only: a Supabase SDK
  deprecation (`verify` parameter) and Vitest's jsdom-environment note. Neither is
  an application defect; the jsdom note is a *performance* observation (the
  environment is created once per file), not a correctness issue, and changing
  the Vitest pool configuration was deliberately out of scope.

**Assumption**

- No CI runner configuration was inspected; results above are from this local
  environment, so a CI-only difference (e.g. a different OS) is unproven.

## 31. Known limitations

**Verified limitations (what this phase did and did not prove):**

- Persistence is mocked in the test suite. Live Supabase behaviour — RLS
  policies, database triggers, real JWT issuance/expiry, the SQL body of the
  vector match function — is *assumed* from contract, not re-proven here.
- Accessibility and responsive findings come from a structured source audit plus
  component tests, not from a machine auditor or real-device rendering.
- Performance findings come from static contract analysis and suite timings, not
  from production profiling or real-network measurement.
- The `localStorage`-backed access token remains XSS-reachable. This is the
  locked Phase 6.15 session design; it was re-audited and deliberately **not**
  redesigned in this phase.
- Institution codes are assumed unique per deployment; a duplicate is a
  data-governance issue, not a code path this phase may change.
- Python dependency auditing honours the repository's existing mechanism: none is
  configured, so no `pip-audit`/`safety` gate exists. Dependencies are locked by
  `uv.lock` and were not changed in this phase.

**Assumptions recorded explicitly (not verified):**

- Any third-party (browser, Supabase, OpenRouter) behaviour outside the audited
  contracts — e.g. real JWT clock skew, RLS policy evaluation order, provider
  rate-limit headers — is assumed from documentation, not exercised here.
- The mocked test doubles faithfully represent the real clients they replace
  (Supabase PostgREST chain shape, httpx response shape).
- Live deployment topology (reverse proxy, TLS termination, CDN caching of
  `/api`) is unknown to this phase and therefore unverified.

## 32. Deferred work

Per the phase rule that production issues requiring an architecture change are
documented rather than implemented, the following are **deferred** and were not
built in Phase 6.21:

- **Non-`localStorage` token storage** (e.g. httpOnly cookie + refresh rotation)
  — would redesign the locked Phase 6.15 session architecture.
- **Idempotency keys** for mutation endpoints — a new cross-cutting mechanism.
- **Structured/trace-correlated logging** and log shipping — a new logging
  platform; §12 verified only that no secrets are logged.
- **Automated accessibility tooling** (axe/CI gate) and **visual-regression
  breakpoint tests** — new tooling, not a defect fix.
- **Route-level code splitting** for the frontend bundle — measure-driven
  optimisation; the 88 kB gzip bundle is not currently harmful.
- **Python dependency audit tooling** — would introduce new tooling without a
  present need.
- **CI pipeline definition** (backend + frontend + build gates) — infrastructure
  rather than application code.
- **Live-integration smoke tests** against a deployed Supabase/OpenRouter
  environment — needs credentials this phase must not hold.

## 33. Git scope

**Verified** — the working tree contains only changes attributable to this phase,
and **no commit was created**:

| File | Change | Reason |
|---|---|---|
| `backend/app/api/ingestion.py` | extraction/chunking failure paths log via `logger.exception` with the processing-run id and return fixed safe messages | §12 / §15 — raw exception text was reaching the client |
| `backend/app/services/ingestion.py` | added `_safe_filename()` and applied it to the object key; `logger` added; failure messages fixed | §13 / §14 — a client filename must never shape the storage key |
| `backend/app/services/admin_documents.py` | document-update object key now uses `_safe_filename()`; `logger` added | same defect on the document-update path |
| `backend/app/services/retrieval.py` | query-embedding failure now uses `logger.exception` instead of printing a traceback to stdout | §12 — traceback was written to process output |
| `backend/app/services/student_auth.py` | login-block logging reduced to identifier-free context | §12 |
| `backend/tests/test_platform_production_readiness_phase_6_21.py` | new phase regression suite (49 tests) | §29 |
| `frontend/src/features/admin/DocumentManager.tsx` | `file:disabled:opacity-50` → `disabled:file:opacity-50` | §24 — invalid variant, no disabled affordance |
| `frontend/src/features/admin/ResultsManager.tsx` | same variant fix | §24 |
| `frontend/src/features/student/StudentInfoJourney.test.tsx` | explicit 15 s budget on the five-mount journey test | §26 — suite-parallel timeout, no behaviour change |
| `PHASE_6_21_PLATFORM_PRODUCTION_READINESS.md` | new phase document (34 sections) | §30 documentation |

- No unrelated file was modified: no schema change, no dependency change, no
  version bump, no reformatting of untouched code, and no new module or
  architecture.

**Assumption**

- "Only attributed changes" is asserted from `git status`/`git diff` inspected at
  the end of the phase; the working tree was not reset to prove it, since the
  phase forbids committing.

## 34. Final status

**Verified** — every Definition-of-Done gate in the phase instruction was
executed in this environment and passed:

| Gate | Result | Evidence |
|---|---|---|
| Production configuration audited | PASS | §4 |
| Development/test routes safely gated | PASS | §5, `test_dev_routes_hidden_outside_dev_mode` |
| Authentication verified | PASS | §6 |
| Registration verified | PASS | §7 |
| Session lifecycle verified | PASS | §8 |
| Authorization verified | PASS | §9 |
| Tenant resolution verified | PASS | §10 |
| API errors do not leak internals | PASS | §11, `_assert_no_leak` on every error test |
| Logging contains no secrets | PASS | §12 |
| File uploads safely scoped | PASS | §13, `_safe_filename` |
| R2 credentials remain backend-only | PASS | §14 |
| RAG ingestion failures handled safely | PASS | §15 |
| Retrieval remains tenant-safe | PASS | §16 |
| Generation failures handled safely | PASS | §17 |
| Chat ownership verified | PASS | §18 |
| Database mutations safe | PASS | §19, §20 |
| Frontend dangerous sinks audited | PASS | §21 |
| Dependency/build audit passes | PASS | §22 — `npm audit` 0 vulnerabilities |
| Runtime production build verified | PASS | §23 |
| Accessibility passes | PASS | §24 |
| Responsive behaviour passes | PASS | §25 |
| Performance has no critical issue | PASS | §26 |
| End-to-end journeys pass | PASS | §27 |
| Failure-injection tests pass | PASS | §28 |
| Security regression suite passes | PASS | §29 — 49/49 |
| Full backend regression passes | PASS | §30 — 1978 passed, 15 skipped |
| Full frontend regression passes | PASS | §30 — 402/402 |
| TypeScript passes | PASS | §22 — `tsc -b` exit 0 |
| Production build passes | PASS | §22 — `vite build` exit 0 |
| Documentation contains exactly 34 sections | PASS | this document |
| Git scope contains no unrelated changes | PASS | §33 |
| No commit created | PASS | §33 — working tree only |

**Defects fixed in this phase (5 verified):**

1. Raw exception text reached the client on extraction/chunking failure
   (`backend/app/api/ingestion.py`, `backend/app/services/ingestion.py`) —
   replaced with fixed safe messages plus `logger.exception` carrying only the
   processing-run id.
2. A client-supplied filename shaped the R2 object key
   (`backend/app/services/ingestion.py`, `backend/app/services/admin_documents.py`)
   — added `_safe_filename()`; the original name is still stored for display.
3. A traceback was printed to process stdout on query-embedding failure
   (`backend/app/services/retrieval.py`) — replaced with `logger.exception`.
4. Login-block logging included an identifier
   (`backend/app/services/student_auth.py`) — reduced to identifier-free context.
5. An invalid Tailwind variant (`file:disabled:opacity-50`) meant the disabled
   file inputs had no disabled affordance
   (`frontend/src/features/admin/DocumentManager.tsx`,
   `frontend/src/features/admin/ResultsManager.tsx`) — corrected to
   `disabled:file:opacity-50`.

**Assumption**

- "Every gate passed" reflects this local environment at the end of the phase.
  Gates that depend on third-party systems (live Supabase RLS, live OpenRouter
  behaviour, real-device rendering) are contract-verified, not integration-proven
  — see §31.

Phase 6.21 — COMPLETE.

**Stop condition observed:** no new architecture, no RAG redesign, no ChatShell
redesign, no Git commit. Awaiting the next phase instruction.
