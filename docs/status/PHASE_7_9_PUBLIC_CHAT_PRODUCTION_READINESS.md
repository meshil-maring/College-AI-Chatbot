# Phase 7.9 — Public Chat Production Readiness & Deployment Verification

Date: 2026-09-28  
Scope: production audit, configuration hardening, verification, and deployment runbook  
Status: **INCOMPLETE — production infrastructure gates remain open**

## 1. Phase objective

Determine whether the Phase 7 public chatbot can be deployed safely as one
backend process and identify the exact prerequisites for horizontal scaling.
The existing public API, RAG authorization, generation, browser-local history,
and process-local abuse-control architecture was preserved.

## 2. Architecture reviewed

The audit traced the complete path:

```text
/public-chat/{institution_code}
  -> anonymous Vite client (no Authorization header)
  -> POST /api/v1/chat/public
  -> body/rate/concurrency controls
  -> institution resolution
  -> search_public_knowledge_chunks RPC
  -> canonical public provenance verification
  -> bounded context and OpenRouter generation
  -> safe public response
  -> bounded per-institution localStorage history
```

Reviewed areas include all Phase 7.1–7.8 documents, backend settings and
startup validation, FastAPI startup/routes/errors/logging, Supabase clients and
migrations, public retrieval/policy/generation, R2 storage, OpenRouter clients,
Vite configuration and environment access, frontend routing/storage/API client,
test/build scripts, dependency manifests, root/backend documentation, and all
deployment files discoverable in the repository.

No Dockerfile, Compose file, Render/Fly/Vercel/Netlify configuration, Nginx
configuration, Procfile, or other production-host definition is present.

## 3. Environment audit

### Required production secrets

| Variable | Purpose | Verification |
| --- | --- | --- |
| `SUPABASE_SECRET_KEY` | Server-side service-role database access | configured locally; not tracked or bundled |
| `R2_ACCESS_KEY_ID` | Server-side R2 credential | configured locally; not tracked or bundled |
| `R2_SECRET_ACCESS_KEY` | Server-side R2 credential | configured locally; not tracked or bundled |
| `OPENROUTER_API_KEY` | Server-side embeddings/generation | configured locally; not tracked or bundled |

### Required non-secret/server configuration

| Variable | Production requirement |
| --- | --- |
| `ENVIRONMENT` | Explicit non-local value such as `production` |
| `DEBUG` | Exactly a parseable false value |
| `DEV_TEST_MODE` | `false` |
| `ALLOWED_HOSTS` | Comma-separated exact public API host names; wildcard forbidden |
| `SUPABASE_URL` | Configured project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Configured Supabase publishable key used by the server client |
| `SUPABASE_JWKS_URL` | Configured JWT key-set URL |
| `R2_ENDPOINT_URL` | Configured HTTPS R2 S3 endpoint |
| `R2_BUCKET` | Existing private document bucket |
| `AI_PROVIDER` | `openrouter` |
| `VITE_API_BASE_URL` | Public build-time API base; `/api` is the same-origin default |

The local developer `.env` has configured Supabase, R2, and OpenRouter values,
but `ENVIRONMENT`, `DEBUG`, and `ALLOWED_HOSTS` are absent. It also has
`DEV_TEST_MODE` enabled, as confirmed by the value-free startup warning. This is
a local development configuration and is **not** production configuration.

### Optional/defaulted configuration

`API_DOCS_ENABLED`, `APP_NAME`, `APP_VERSION`, `MAX_UPLOAD_SIZE_MB`,
`OPENROUTER_SITE_URL`, `OPENROUTER_APP_NAME`, `OPENROUTER_BASE_URL`,
`OPENROUTER_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`,
`EMBEDDING_BATCH_SIZE`, `EMBEDDING_REQUEST_TIMEOUT_SECONDS`,
`CONVERSATION_HISTORY_MAX_MESSAGES`, `RETRIEVAL_TOP_K`,
`REWRITE_HISTORY_EXCHANGES`, `REWRITE_MAX_HISTORY_CHARS`, and every
`PUBLIC_*` resource-control setting in `app.config.Settings` have bounded or
documented defaults. Deployments may tune them without exposing them to the
browser. `API_DOCS_ENABLED` defaults on locally and off outside local/test
environments.

## 4. Secret audit

- `.env` is ignored and is not tracked. Only backend/frontend `.env.example`
  files are tracked.
- A comparison of configured secret values against tracked files reported
  `TRACKED_SECRET_VALUE_MATCHES=NONE`.
- Frontend source reads only `VITE_API_BASE_URL`; no secret-shaped `VITE_*`
  variable exists.
- The production bundle scanner passed across four generated files. No
  localhost URL, OpenRouter key, Supabase secret/service-role reference, R2
  secret, database URL, PEM key, or hard-coded password was detected.
- Public request/response and browser-storage schemas contain no credentials,
  provider metadata, internal IDs, or storage paths.
- Expected public provider/database failures now produce coarse operational
  events without exception text or traceback; public responses remain fixed.

## 5. DEBUG and diagnostics

Production startup rejects `DEBUG=true` and rejects `DEV_TEST_MODE=true` for a
non-local environment. Public responses never include generation diagnostics.
Development-only auth routes are not registered when `DEV_TEST_MODE=false`.
The production runbook must explicitly override the current local settings.

## 6. CORS audit

No CORS middleware is configured. This is intentional for the verified
same-origin design: the browser uses `/api`, public chat sends no credentials,
and the backend returns no wildcard CORS headers. A split-origin deployment is
not supported by the current configuration and must add a reviewed explicit
origin allow-list; it must not combine wildcard origins with credentials.

## 7. Host and trusted-proxy audit

`TrustedHostMiddleware` now validates the configured exact host names. Local
development falls back to `localhost`, `127.0.0.1`, and `testserver`; production
startup rejects missing or wildcard `ALLOWED_HOSTS`.

The repository identifies no Render, Fly.io, Cloudflare, Nginx, load balancer,
or other trusted reverse proxy. The packaged Uvicorn command therefore disables
proxy-header processing, and public rate limiting continues to use the direct
ASGI peer address. Arbitrary `Forwarded`/`X-Forwarded-For` trust is not enabled.
If a proxy is later selected, its exact hop/network must be configured at the
server/edge and tested before forwarded client identity may be used.

## 8. HTTPS audit

No production hosting or TLS-termination configuration exists in the repository.
The API emits HSTS in non-local environments, but HSTS is useful only after a
real HTTPS deployment exists. TLS termination and HTTP-to-HTTPS redirect must be
verified at the selected platform, reverse proxy, or Cloudflare edge.

**HTTPS status: NOT VERIFIED / deployment blocker.**

## 9. Security headers

Backend responses now set `X-Content-Type-Options: nosniff`,
`Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, and a restrictive
camera/microphone/geolocation `Permissions-Policy`; deployed environments also
set HSTS. A backend CSP was deliberately not added because the API returns JSON
and Swagger uses external assets locally. The frontend static host must supply
and test its own CSP and HSTS/redirect policy; no host configuration exists to
verify those headers.

## 10. Database migrations and RPC

Migration order is filename ordered:

1. `20260928000000_phase_7_2_public_knowledge_policy.sql` adds fail-closed
   `visibility`, its constraint/index, performs the compatibility backfill,
   creates the service-role-only public RPC, and revokes anon/authenticated
   execution.
2. `20260928010000_phase_7_4_public_rag_hardening.sql` replaces that RPC with
   bounded match count, completed-run, and embedding-dimension checks.

Neither migration drops tables or deletes rows. Phase 7.2's DDL is structurally
rerunnable, but its unconditional backfill can re-publicize an eligible row that
was deliberately changed to restricted after the first application; it must be
treated as a one-time ordered migration, not an operational repair script.
Phase 7.4's `CREATE OR REPLACE FUNCTION` is idempotent for the represented
schema. No down/rollback migration exists.

The read-only remote migration ledger check succeeded and showed both Phase 7
migrations as local-only. It also showed `20260914000000` as local-only. A
read-only remote RPC invocation reported `PUBLIC_RPC_AVAILABLE=FAIL`.

```text
REMOTE MIGRATION STATUS: VERIFIED NOT APPLIED
REMOTE PUBLIC RPC: FAIL / NOT AVAILABLE
```

The required public/authenticated/restricted, lifecycle/date, processing,
embedding, and cross-tenant RPC behavior is comprehensively verified by local
SQL-contract and service tests, but cannot be claimed for the current remote
database until the migrations are applied and the live matrix is rerun.

## 11. Database connectivity

The value-free read-only infrastructure script reported
`SUPABASE_CONNECTIVITY=PASS`. It selected at most one institution identifier and
did not modify or print remote data. `/ready` now performs the same bounded
dependency class and returns only `ready` or `unavailable`.

Public retrieval against the remote database is not operational because its RPC
is absent. Authenticated behavior remains locally regression-tested; no
destructive live authenticated operation was performed.

## 12. R2 status

R2 credentials remain backend-only. Storage operations use server-side boto3,
return object keys internally, and the public chat projection exposes no object
key, storage path, or private URL. A read-only one-object-list connectivity
check reported `R2_CONNECTIVITY=PASS`. Error responses remain sanitized. Bucket
backup/versioning/retention policy is not represented in the repository.

## 13. OpenRouter status

The API key, provider, model, base URL, timeout, and output-token budget remain
server-controlled. Public generation uses a 30-second timeout and an 800-token
default ceiling; provider errors are normalized and provider metadata is not
projected publicly. One minimal configured-model request reported
`OPENROUTER_GENERATION=PASS`. No stress/load test was performed.

## 14. Health and readiness

- `GET /health`: liveness only; no dependency access.
- `GET /ready`: bounded, read-only Supabase dependency check; returns 503 with
  a detail-free body on failure.
- OpenRouter and R2 startup configuration is mandatory, but they are not called
  by readiness because no zero-cost provider operation is required per probe.

Tests verify public access, the database/no-database distinction, bounded query,
503 sanitation, and absence of credentials/infrastructure details.

## 15. API documentation

Swagger, ReDoc, and `openapi.json` remain enabled by default in local/test
environments for established tests and development. They default to disabled in
non-local environments, with `API_DOCS_ENABLED` as an explicit operator choice.
OpenAPI schemas contain no secrets; production does not require public docs.

## 16. Frontend and API routing

The production bundle uses only `VITE_API_BASE_URL` and defaults to same-origin
`/api`; bundle scanning found no `localhost` or `127.0.0.1`. The public client
calls `/api/v1/chat/public` without `Authorization` and serializes only
`institution_code` and `message`.

The built app was served with Vite preview and direct navigation to
`/public-chat/COLLEGE001` returned HTTP 200 with the SPA root. This proves the
application route/build, not an unknown production host. The selected static
host must add a history fallback equivalent to `/* -> /index.html` while
preserving `/api/*` proxying to the backend. No such host rule exists today.

## 17. Worker configuration and shutdown

The packaged `uv run start` path now uses exactly one Uvicorn worker, disables
reload outside local development, and disables proxy-header trust. Phase 7.8
rate windows and concurrency counts remain process-local. Request leases release
in `finally`, including error and timeout paths. The public API has no persistent
anonymous server state or public background tasks, so normal Uvicorn draining
does not lose public history; browser localStorage remains authoritative.

## 18. Abuse controls

Local tests verify direct-peer identity, ignored spoofed forwarding headers,
client/institution/global 429 limits, global/institution 503 concurrency limits,
lease release, 8,192-byte body cap, five-second body timeout, 4,000-character
message cap, bounded retrieval/context/output, and no automatic browser retry.

These controls are valid only for one process. Multiple workers or instances
have independent counters and are not protected by a distributed quota.

## 19. Logging and observability

Public operational logs contain event name, normalized institution code,
status, duration, and coarse failure category. They do not contain questions,
answers, tokens, credentials, provider bodies, SQL, storage paths, or expected
public-error tracebacks. The application currently exposes standard process
logs from which request counts, status/error rates, 429/503 counts, latency,
generation failures, database/readiness failures, and provider failures can be
aggregated. No metrics exporter, dashboard, alert policy, trace collector, or
durable analytics platform exists.

## 20. Smoke and negative tests

Local deterministic tests passed for the complete HTTP-to-public-RAG-to-provider
projection using controlled repositories/providers, safe sources, refresh/local
history restoration, invalid institution, private/authenticated/restricted and
cross-tenant exclusion, unpublished/expired/future/invalid-run/invalid-embedding
exclusion, oversized message/body, 429, 503, provider timeout, database failure,
frontend network failure, protected-endpoint authentication, no server-side
anonymous persistence, and absence of provider/diagnostic/internal-ID fields.

The real deployed smoke flow was **not passed**. Remote Supabase lacks the Phase
7 migrations/RPC, so proceeding to an OpenRouter-backed public answer would not
establish production correctness. No private student data was used.

## 21. Browser storage

Version-2 local storage is namespaced by normalized institution and bounded to
40 messages/256,000 serialized characters. Validation retains only local IDs,
roles, text, timestamps, public status, and safe `title`/`section`/`quote`
sources. Tests verify malformed/wrong-tenant/oversized reset, no auth token,
provider key, internal database ID, storage path, or provider metadata, and
refresh restoration.

## 22. Dependency audit

- Python dependencies are locked in `backend/uv.lock`; no configured Python
  vulnerability-audit command exists. No blind upgrade was made.
- `npm audit --audit-level=high` reported zero vulnerabilities.
- Production frontend dependencies are React and React DOM; test/build tooling
  remains in `devDependencies`.
- The complete backend and frontend suites, TypeScript, and build pass. Existing
  FastAPI/TestClient, Supabase client, and collection warnings are recorded in
  the verification results and do not indicate a newly discovered advisory.

## 23. Backup, recovery, and rollback

Supabase backup ownership, retention, and point-in-time recovery availability,
R2 object versioning/retention, and hosting-artifact rollback are not described
in the repository.

```text
EXTERNAL INFRASTRUCTURE VERIFICATION REQUIRED
```

No destructive recovery test was run. Phase 7 has no down migrations; database
rollback requires an operator-reviewed forward repair or a verified managed
backup/PITR procedure. Application rollback is to redeploy the previous
known-good backend and frontend artifacts using the selected platform's own
rollback mechanism; no repository-specific command can be documented because
no platform is selected. Do not roll back application code to a version that is
incompatible with already-applied schema changes.

## 24. Deployment runbook

### Before deployment

- Create platform secrets/config from the table in Section 3; set
  `ENVIRONMENT=production`, `DEBUG=false`, `DEV_TEST_MODE=false`, and exact
  `ALLOWED_HOSTS`.
- Select one same-origin HTTPS hosting design and document TLS termination,
  `/api` proxying, frontend security headers, and SPA history fallback.
- Review backups/PITR, take the platform-supported pre-migration backup, then
  apply all ordered pending migrations using the project's normal Supabase
  migration workflow. Do not rerun Phase 7.2 as a repair script.
- Confirm remote migration ledger parity; verify the public RPC signature,
  grants, index, and full eligibility matrix with safe fixture data.
- Run backend/frontend tests, TypeScript, production build, bundle security
  scan, dependency audit, and `git diff --check`.

### Deployment

- Start the backend via the packaged production path with one process/worker.
- Route only HTTPS public traffic; do not enable proxy-header trust until the
  exact proxy chain is known and tested.
- Deploy `frontend/dist`; keep `VITE_API_BASE_URL=/api` for same origin.
- Configure `/api/*` to the backend and all non-file frontend routes to
  `index.html`, without rewriting API requests.
- Configure platform probes: `/health` for liveness and `/ready` for readiness.

### After deployment

- Confirm `/health`, `/ready`, `/public-chat/{known-safe-code}`, and direct
  refresh of that public route over HTTPS.
- Run one safe public question through retrieval/generation and confirm only
  safe sources appear; refresh and confirm local conversation restoration.
- Verify invalid institution, oversized request, controlled 429, mocked/staging
  503, protected endpoint auth, and public tenant/private-knowledge isolation.
- Inspect browser storage/network headers and operational logs for forbidden
  tokens, IDs, messages, answers, diagnostics, SQL, and provider details.

### Rollback

- Stop new rollout traffic using the selected platform's deployment controls.
- Redeploy the previous known-good immutable backend/frontend artifacts.
- Do not execute ad-hoc reverse SQL. If schema rollback is essential, use the
  reviewed managed backup/PITR process after confirming compatibility and data
  loss boundaries. Platform-specific commands remain intentionally unspecified.

## 25. Production checklist

- [ ] Production secrets configured in the deployment secret store
- [ ] `DEBUG=false`
- [x] CORS verified for the same-origin deployment constraint
- [ ] Host validation configured with the real production hosts
- [ ] HTTPS verified at the selected TLS terminator
- [ ] Security headers verified at both API and frontend hosts
- [x] Public API URL verified in the production bundle
- [ ] SPA rewrite verified on the selected production host
- [ ] Supabase migrations verified remotely (currently absent)
- [ ] Public RPC verified remotely (currently unavailable)
- [x] R2 configuration/connectivity verified read-only
- [x] OpenRouter configuration/minimal generation verified
- [x] Health endpoint verified
- [x] Startup validation verified
- [x] Single-worker constraint documented and enforced by packaged start
- [x] Rate limiting verified locally
- [x] Concurrency limits verified locally
- [x] Public RAG verified locally
- [x] Public generation verified locally/provider smoke
- [x] Safe errors verified
- [x] Browser persistence verified
- [x] No secrets in frontend
- [x] No sensitive public logging
- [ ] Deployed end-to-end smoke test passed
- [x] Local negative tests passed
- [x] Production build passed

## 26. Verification results

```text
Phase 7.2–7.9 backend regression (DEBUG=false):
  uv run pytest -q <six Phase 7 policy/API/RAG/generation/abuse/readiness files>
  109 passed, 1 warning

Complete backend (repository's diagnostic test mode):
  DEBUG=true uv run pytest -q tests
  2127 passed, 15 skipped, 6 warnings

Complete frontend:
  npm.cmd run test
  50 files passed, 431 tests passed

TypeScript:
  npx.cmd tsc --noEmit -p tsconfig.json
  exit 0

Production build:
  npm.cmd run build
  97 modules transformed; build passed

Bundle security:
  node scripts/verify_frontend_build_security.mjs
  PASS (4 files; only VITE_API_BASE_URL allow-listed)

Dependency audit:
  npm.cmd audit --audit-level=high
  0 vulnerabilities

SPA preview direct route:
  GET /public-chat/COLLEGE001
  HTTP 200; SPA root present

Remote migration ledger:
  supabase migration list
  command passed; Phase 7.2 and 7.4 remote entries absent

Read-only live infrastructure:
  SUPABASE_CONNECTIVITY=PASS
  PUBLIC_RPC_AVAILABLE=FAIL
  R2_CONNECTIVITY=PASS
  OPENROUTER_GENERATION=PASS

Local production-mode startup smoke:
  application import/startup validation passed
  /docs = 404
  HSTS present = true
  untrusted Host = 400

Final affected backend rerun after logging hardening:
  102 passed, 1 warning

Diff hygiene:
  git diff --check
  exit 0 (line-ending notices only)
```

One non-authoritative frontend attempt with explicit single-worker threads was
stopped after it stalled before collection; the exact requested `npm run test`
command then completed successfully and is the authoritative result.

## 27. Deployment limitations and deferred work

- Single-process only: process-local rate/concurrency enforcement is not shared.
- Trusted proxy: none selected or trusted; direct-peer behavior is preserved.
- Distributed rate limiting/concurrency: absent; required before horizontal
  workers/instances.
- Remote Phase 7 migrations/RPC: absent and must be applied/verified.
- Production platform, TLS, frontend headers, API proxy, SPA rewrite, health
  probe wiring, log aggregation, alerts, backups/PITR, and artifact rollback:
  external and unverified.
- After migrations, perform the live public eligibility matrix and one complete
  browser smoke flow with a known safe public knowledge record.

## 28. Readiness classification

```text
Demo readiness: NOT READY
Single-instance production: NOT READY
Horizontal scaling: NOT READY
```

Demo and single-instance production are blocked by the missing remote Phase 7
migrations/RPC and absent verified HTTPS/static-host routing configuration.
Horizontal scaling is additionally blocked by process-local rate/concurrency
state and the absence of trusted edge/distributed enforcement.

## 29. Final status

```text
PHASE 7.9 STATUS: INCOMPLETE
```

Exact blockers: apply and verify remote migrations/RPC; select and verify the
single-instance HTTPS deployment; configure real `ALLOWED_HOSTS` and production
flags; configure/test frontend security headers and SPA/API rewrites; verify
backup/rollback operations; then pass the real public-chat smoke and live public
knowledge eligibility matrix.

## 30. Phase 7.9.1 follow-up (2026-09-29)

Phase 7.9.1 confirmed that the linked Supabase project matches the backend
configuration, then queried the remote backup API before any mutation. PITR is
disabled and zero physical backups are available. The safety gate therefore
prohibited migration application. The remote ledger still shows Phase 7.2 and
7.4 unapplied, alongside the earlier pending Phase 6.11 notification migration;
read-only checks also confirm that `knowledge_sources.visibility` and
`search_public_knowledge_chunks` are absent.

No remote data or migration ledger state was changed. Full evidence, test
results, and the remaining external deployment prerequisites are recorded in
`PHASE_7_9_1_PRODUCTION_BLOCKER_RESOLUTION.md`.
