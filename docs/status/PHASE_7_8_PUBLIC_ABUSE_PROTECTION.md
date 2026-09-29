# Phase 7.8 — Public Chat Abuse Protection & Resource Controls

## 1. Objective

Phase 7.8 places bounded, server-authoritative resource controls in front of
the existing stateless public RAG path. It does not change authentication,
tenant resolution, public-knowledge authorization, provenance verification,
or authenticated chat behavior.

## 2. Threat model

The controls address request floods, automated repetition, parallel request
exhaustion, oversized and slow request bodies, costly embeddings/retrieval,
AI generation cost, accidental browser loops, and one institution consuming
an uncontrolled share of a shared process. They do not attempt CAPTCHA,
behavioral bot detection, billing, or user identity.

## 3. Existing architecture

The endpoint remains `POST /api/v1/chat/public`:

```text
browser -> body cap -> schema validation -> rate limits -> concurrency gate
        -> tenant resolution -> public policy -> bounded retrieval
        -> provenance validation -> bounded generation -> public projection
```

The browser keeps local history. The backend creates no anonymous
conversation/message records.

## 4. Rate limiting design

`app.services.public_abuse_controls` implements an atomic, thread-safe sliding
window in process memory. One accepted request is charged across three small
dimensions:

- direct peer IP: 60 requests per 60 seconds;
- normalized institution code: 180 requests per 60 seconds;
- process-wide public chat: 600 requests per 60 seconds.

The direct ASGI peer address is authoritative. `X-Forwarded-For`, `Forwarded`,
and similar client headers are ignored because the repository has no trusted
proxy configuration. Unknown peers share a conservative `unknown` bucket.
Expired identities are swept so rotating codes do not persist in memory.

An exceeded window returns safe `429 PUBLIC_RATE_LIMITED` plus `Retry-After`.
It exposes neither counter values nor provider/infrastructure details. Rate
limiting is enabled by default; disabling it requires the explicit
`PUBLIC_RATE_LIMIT_ENABLED=false` setting.

## 5. Concurrency design

The non-blocking gate permits at most eight active public requests in one
process and four for one normalized institution code. Saturation returns safe
`503 PUBLIC_CHAT_BUSY` plus a coarse `Retry-After` instead of queueing more
expensive work. A lease is released in `finally` after success, application
error, provider timeout, or unexpected exception. Authenticated endpoints do
not use this gate.

## 6. Request-size controls

`PublicChatRequest.message` retains its absolute 4,000-character Pydantic
contract. `PUBLIC_MAX_MESSAGE_CHARS` may lower but cannot raise that ceiling.
The public-route-only ASGI middleware rejects bodies over 8,192 bytes before
JSON parsing and rejects a body that takes over five seconds to arrive.
Responses are safe 413 and 408 envelopes. Other API routes are unaffected.

Verified boundaries: 3,999 accepted, 4,000 accepted, 4,001 rejected.

## 7. Retrieval limits

Public retrieval still uses server-owned `RETRIEVAL_TOP_K=4`. The client
cannot send top-K, source IDs, document IDs, model, or retrieval configuration.
The dedicated SQL RPC is institution-scoped and public-only. Canonical
repository provenance is rechecked after retrieval. Each accepted chunk is at
most 4,000 characters and total context is at most 12,000 characters; content
is excluded rather than truncated.

The existing exact-query embedding cache now keys entries by SHA-256 digest,
not full message text. It stores no response, history, or retrieval result.
No semantic response cache or cross-tenant answer cache was introduced.

## 8. Generation limits

The public `AIContext` remains server-created. Output is capped at 800 tokens,
the public provider call remains capped at 30 seconds, and projected response
text is capped at 12,000 characters. Empty verified context deterministically
bypasses generation. Clients cannot select model, provider, temperature,
system instructions, output tokens, or timeouts.

Provider usage metadata may be consumed internally by the existing provider
abstraction but is not sufficiently portable for quota accounting and is
never returned publicly. No invented token ledger or billing was added.

## 9. Timeout strategy

- request-body receive: 5-second whole-body deadline;
- embedding HTTP call: explicit configurable 30-second timeout;
- Supabase/PostgREST: the installed SDK has a finite 120-second request
  timeout; query counts and returned rows remain bounded;
- public generation: explicit configurable 30-second timeout;
- browser request: existing 35-second abort timeout.

The application does not falsely claim cancellable whole-request deadlines
for synchronous database work: Python cannot safely kill an in-flight worker
thread. Each external stage is finite, concurrency remains bounded, and a
provider timeout releases its gate lease.

## 10. Error handling

Public mappings are intentionally coarse:

| Status | Public meaning |
|---|---|
| 400/422 | malformed or invalid request |
| 408/504 | body or provider timeout |
| 413 | request body too large |
| 429 | local/provider rate limited |
| 500 | unexpected safe service failure |
| 502 | invalid upstream response |
| 503 | concurrency saturation or generation unavailable |

No stack trace, SQL, database identifier, provider body, model data, internal
quota, or diagnostic metadata is returned. The frontend maps 429 and 503 to
“The chatbot is busy right now. Please try again shortly.” It never retries
automatically; the saved user turn can be retried only by explicit action.

## 11. Logging and telemetry

Operational logs contain event name, normalized institution code, status, and
duration. Rate/concurrency rejection events are logged without request text.
Full messages, answers, local history, credentials, provider secrets, and API
keys are not logged. Telemetry failure is not part of enforcement and cannot
disable the endpoint.

## 12. Privacy

Operational telemetry is not conversation persistence. No anonymous account,
server-side conversation, message, answer, or history is created. The only
short-lived repetition optimization is a bounded in-memory query-embedding
cache keyed by a one-way digest rather than the anonymous message.

## 13. Configuration

All listed settings use the project's Pydantic environment convention:

| Variable | Default |
|---|---:|
| `PUBLIC_MAX_MESSAGE_CHARS` | 4000 |
| `PUBLIC_MAX_BODY_BYTES` | 8192 |
| `PUBLIC_BODY_READ_TIMEOUT_SECONDS` | 5 |
| `PUBLIC_RATE_LIMIT_ENABLED` | true |
| `PUBLIC_RATE_LIMIT_REQUESTS` | 60 |
| `PUBLIC_RATE_LIMIT_WINDOW_SECONDS` | 60 |
| `PUBLIC_INSTITUTION_RATE_LIMIT_REQUESTS` | 180 |
| `PUBLIC_GLOBAL_RATE_LIMIT_REQUESTS` | 600 |
| `PUBLIC_CONCURRENCY_LIMIT` | 8 |
| `PUBLIC_INSTITUTION_CONCURRENCY_LIMIT` | 4 |
| `PUBLIC_OVERLOAD_RETRY_AFTER_SECONDS` | 2 |
| `EMBEDDING_REQUEST_TIMEOUT_SECONDS` | 30 |
| `RETRIEVAL_TOP_K` | 4 |
| `PUBLIC_CONTEXT_MAX_CHUNK_CHARS` | 4000 |
| `PUBLIC_CONTEXT_MAX_CHARS` | 12000 |
| `PUBLIC_GENERATION_MAX_TOKENS` | 800 |
| `PUBLIC_GENERATION_TIMEOUT_SECONDS` | 30 |
| `PUBLIC_RESPONSE_MAX_CHARS` | 12000 |

Validation prevents zero/unbounded values, raising the 4,000-character
contract, and a per-institution concurrency limit above the global limit.

## 14. Safe defaults

Defaults favor a small public demo: four concurrent requests per institution,
eight total, modest rolling request budgets, four retrieved chunks, 12,000
context characters, and 800 generated tokens. No resource dimension silently
defaults to unlimited.

## 15. Failure behavior

Enforcement is in-process and has no network dependency. Internal limiter
errors fail closed through the generic 500 handler before expensive work.
Rate or concurrency rejection prevents tenant lookup, embedding, vector
search, and generation. Optional logging is fail-open with respect to service
availability and cannot grant capacity.

## 16. Tests

`backend/tests/test_public_abuse_controls_phase_7_8.py` covers window edges and
reset, independent clients, tenant isolation, spoofed forwarding headers,
global/institution concurrency, release after exception and timeout,
3,999/4,000/4,001 message boundaries, 413 body rejection, 408 slow-body
rejection, client control rejection, no message logging, and 100 bounded fake
requests with no real provider calls.

Frontend tests cover safe 429/503 presentation, loading reset, preservation of
the failed user message, explicit retry, and absence of automatic retries.

## 17. Deployment considerations

Repository evidence shows local/single-process Uvicorn startup, same-origin
reverse-proxy expectations, and no Redis, Upstash, API gateway, Cloudflare
rate limiter, or trusted-proxy middleware. The implementation is correct only
for one backend process. Multiple workers/instances each maintain independent
windows and concurrency counts.

Before horizontal scaling, put a trusted edge/gateway or distributed atomic
store in front of this route. Configure that layer to derive client identity
from a trusted connection chain; do not simply start trusting arbitrary
forwarding headers in the application. The process-local gate should remain as
defense in depth.

## 18. Known limitations

- Limits are process-local, not distributed.
- The peer address may be the reverse proxy address until an explicit trusted
  proxy design is deployed; this is conservative (shared bucket), not a
  spoofable bypass.
- Provider usage payloads are not used as authoritative accounting.
- Supabase's finite SDK timeout is shared by authenticated and public reads;
  this phase does not replace the client or database infrastructure.
- There is no hard cancellation of already-running synchronous Python/SDK
  calls beyond their individual transport timeouts.

## 19. Deferred work

Distributed/edge throttling, trusted proxy parsing, durable institution usage
budgets, CAPTCHA, bot scoring, billing, subscriptions, semantic answer caches,
authenticated-user quotas, and deployment changes are intentionally deferred.

## 20. Acceptance criteria

The implementation provides non-spoofable process-local identity, tenant and
global request isolation, bounded concurrency with leak tests, schema/body and
slow-client protection, fixed retrieval/context/generation budgets, safe
errors/logs, stateless privacy, explicit configuration, frontend overload
handling, and authenticated-boundary isolation. Verification results are
recorded in the final Phase 7.8 report after all suites complete.

### Verification record

- Focused: `$env:DEBUG='false'; uv run pytest -q tests/test_public_abuse_controls_phase_7_8.py`
  — 15 passed.
- Phase 7.3–7.5 backend regression: `$env:DEBUG='false'; uv run pytest -q
  tests/test_narrow_public_chat_api_phase_7_3.py
  tests/test_public_rag_integration_phase_7_4.py
  tests/test_public_ai_generation_phase_7_5.py` — 65 passed.
- Full backend: `$env:DEBUG='true'; uv run pytest -q tests` — 2,111 passed,
  15 skipped, 6 warnings.
- Full frontend: `npm.cmd run test` — 50 files passed, 431 tests passed.
- TypeScript: `npx.cmd tsc --noEmit -p tsconfig.json` — exit 0.
- Production build: `npm.cmd run build` — 97 modules transformed, build passed.
- Diff hygiene: `git diff --check` — passed (line-ending notices only).

The first full-backend diagnostic run with `DEBUG=false` produced 2,109
passes, 15 skips, and two expected failures in development-diagnostics tests;
rerunning with the repository's expected `DEBUG=true` development setting
passed all 2,111 runnable tests. This was an environment-mode mismatch, not a
Phase 7.8 regression.
