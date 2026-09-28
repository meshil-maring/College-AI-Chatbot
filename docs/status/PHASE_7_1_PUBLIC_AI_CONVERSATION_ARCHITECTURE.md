# Phase 7.1 — Public AI Conversation Architecture & Scope Lock

Status: **COMPLETE — architecture verified and scope locked**  
Phase type: architecture and documentation only  
Next phase: **Phase 7.2 — Public Knowledge/Data Access Policy**

## 1. Purpose

Phase 7 defines an unauthenticated AI experience for general, institution-approved
college information. Its primary invariant is:

> A public user may access only explicitly public knowledge belonging to the
> correctly resolved institution.

The feature is additive. It must reuse the existing retrieval, context assembly,
generation-provider, and response patterns without weakening authenticated student,
faculty, staff, or administrator boundaries.

Repository inspection found that Phase 6.13.8 already introduced a partial public
backend at `POST /api/v1/chat/public`. Phase 7 therefore hardens and productizes an
existing capability; it does not assume a blank slate. Phase 7.1 makes no runtime or
schema changes.

## 2. Scope

In scope:

- document the current public and authenticated paths;
- lock authentication, tenant, knowledge, retrieval, generation, session, frontend,
  error, and abuse boundaries;
- define the intended public HTTP contract;
- identify gaps that Phase 7.2 and later phases must close;
- define the threat model and future test requirements.

## 3. Non-goals

Phase 7.1 does not implement a public page or client, change the existing endpoint,
add a migration, modify the embedding/vector pipeline, add an AI provider, change
student personalization, redesign authentication/RBAC, add persistent anonymous
history, add deployment infrastructure, or repair the gaps recorded below.

## 4. Existing architecture summary

### 4.1 Backend

- `app.main` registers authenticated `POST /api/v1/generation/chat` with
  `Depends(get_current_user)` and unauthenticated `POST /api/v1/chat/public`
  without an authentication dependency.
- `app.core.security` verifies Supabase JWTs, resolves the application user, defines
  RBAC helpers, and treats `institution_id` as the tenant key.
- Authenticated chat calls `scope_tenant`, derives identity and personalization from
  the verified user, and persists conversations under that user.
- Public chat validates the requested institution and its organization, never loads
  student personalization, and persists under the shared sentinel `PUBLIC_USER_ID`.
- `app.services.retrieval` embeds a query and calls the pgvector
  `search_similar_chunks` RPC through the service-role client. The RPC requires at
  least one scope and supports institution, knowledge-source, document, version,
  processing-run, and model filters.
- `app.services.context.assemble_context`, `AIGenerationService`, the
  `GenerationProvider` protocol, and `OpenRouterGenerationProvider` are shared by
  both chat paths.
- `AppError` is serialized as `{ "error": { "code", "message" } }`; validation and
  unexpected exceptions have normalized handlers in `app.main`.
- No application-level rate limiter, request throttle, CAPTCHA, or suspicious-request
  detector exists. Provider HTTP 429 responses are normalized, but that does not
  protect this application from public abuse.

### 4.2 Knowledge and retrieval model

- `knowledge_sources` carries `institution_id`, `source_type`, `authority_level`,
  `lifecycle_status`, and effective dates.
- `documents` belongs to a knowledge source; `document_versions` has its own
  lifecycle and effective dates; processing runs produce `knowledge_chunks` and
  `chunk_embeddings`.
- The database RPC scopes vector candidates by metadata but does not itself enforce
  public visibility or lifecycle state.
- Current public code defines `faq`, `notice`, and `handbook` as public source types.
  The canonical FAQ and notice ingestion paths create published knowledge sources.
- Public retrieval first scopes by the validated institution and then post-filters
  returned chunks through processing-run provenance to an allowed knowledge source.

### 4.3 Frontend

- The React application has no router library or URL route table. `App.tsx` always
  mounts `AuthProvider`, then renders the login form or a server-authoritative
  role shell.
- `useChat` and `services/api.ts` support only authenticated chat. They require an
  access token and call `/api/v1/generation/chat`.
- There is no public chat client, state hook, or page. The authenticated `ChatShell`
  must not be repurposed in a way that initializes authenticated state for visitors.
- Vite already proxies `/api` to the backend during development.

## 5. Public conversation definition

Public conversation answers general questions using only approved public RAG
knowledge for one institution. Based on current data and ingestion behavior, the
present candidate categories are:

- published FAQs (`source_type=faq`);
- published notices (`source_type=notice`);
- published handbook content (`source_type=handbook`).

Programs, departments, admissions, campus information, contacts, and learning
resources are public only when an institution has deliberately represented and
published them inside an approved public knowledge source. Their names alone do not
create a new authorization category.

The public path must never query or assemble attendance, test/exam results, student
profiles or identifiers, student email/authentication data, private academic records,
staff/faculty/admin data, internal documents, tokens, secrets, or another tenant's
data.

## 6. Public conversation architecture

```text
Untrusted visitor
    -> public-specific request validation
    -> public institution-code resolution
    -> active institution + organization validation
    -> public knowledge policy at data access
    -> institution-scoped embedding/vector search
    -> public/lifecycle/provenance post-verification
    -> shared context assembly and generation provider
    -> public-safe response projection
```

No model call may occur until tenant and public-knowledge checks have completed.
Empty authorized context produces `insufficient_context`; it must not fall back to
unscoped retrieval or model knowledge for institution-specific facts.

## 7. Authentication boundary

```text
Public
  -> /api/v1/chat/public (no JWT dependency)
  -> public request schema
  -> public tenant resolver
  -> public-only retrieval policy
  -> non-personalized generation
```

```text
Authenticated student
  -> /api/v1/generation/chat (JWT required)
  -> get_current_user + server-side role/tenant
  -> scope_tenant
  -> authorized student context + tenant-scoped RAG
  -> personalized generation
```

The public endpoint must not call `get_current_user`, accept a role, accept a student
identifier, or use a JWT claim as optional personalization. The protected endpoint
and all student APIs retain their existing JWT/RBAC requirements.

The current personal-question classifier is useful UX defense but is not an access
control. Security comes from the fact that public code has no route to student
repositories and only authorized public chunks may reach generation.

## 8. Tenant boundary

The repository already has a public, globally unique institution code lookup:
`GET /api/v1/institutions/lookup?code=...`, backed by
`get_institution_by_code`. Phase 7 will reuse that established mechanism.

Locked future request resolution:

1. Accept `institution_code`, not an internal institution UUID, in the public chat
   contract.
2. Normalize and resolve it server-side.
3. Require an active institution and an allowed organization state.
4. carry only the resolved `institution_id` internally;
5. apply it to vector search and again to provenance verification.

The current endpoint accepts `institution_id` directly and validates it. That is
tenant-safe when all downstream checks hold, but it exposes an internal identifier
and is not the preferred public discovery contract.

Invariant:

```text
Public request -> resolved institution -> public knowledge only -> same institution only
```

An unknown code must return a non-enumerating `INSTITUTION_NOT_FOUND`. An inactive
institution must not return public knowledge.

## 9. Public knowledge boundary

### 9.1 Current controls

The current code uses all of the following:

- an institution-scoped vector query;
- published knowledge-source enumeration;
- a source-type allow-list (`faq`, `notice`, `handbook`);
- processing-run-to-document-to-knowledge-source provenance resolution;
- an institution and allow-list post-filter before context assembly.

### 9.2 Verified gaps and Phase 7.2 prerequisites

1. **No explicit visibility attribute.** Public status is inferred from
   `source_type`. Type and visibility are different concerns. The smallest durable
   schema addition is a fail-closed `knowledge_sources.visibility` value such as
   `private | authenticated | public`, defaulting to `private`, with an explicit
   backfill and database constraint. Phase 7.2 must decide and specify this migration;
   Phase 7.1 does not create it.
2. **Explicit-source publication bypass.** `_knowledge_source_is_public` checks
   institution and source type but not `lifecycle_status`. Supplying a specific
   `knowledge_source_id` can therefore take a different path from published-source
   enumeration. The future public schema must not accept this internal filter, and
   the repository policy must enforce publication regardless of call path.
3. **Incomplete lifecycle chain.** The final public chunk decision does not currently
   prove that the document version is published, effective, non-archived, and from a
   completed/valid processing run. Phase 7.2 must define one authoritative query or
   repository policy that evaluates the complete provenance chain.
4. **Service-role dependence.** The backend uses an administrative Supabase client;
   therefore database RLS is not the public boundary. A dedicated repository method
   and fail-closed query contract are mandatory.

Locked public eligibility predicate:

```text
institution active
AND organization allowed by policy
AND knowledge source institution matches
AND knowledge source visibility = public
AND knowledge source lifecycle = published
AND effective date window permits access
AND document/version lifecycle permits public access
AND processing run/chunk is valid
```

No source is public merely because its content sounds general.

## 10. RAG boundary

The existing embedding model, chunk table, pgvector index/RPC, retrieval service, and
context assembly are reused. A separate vector database is forbidden.

Expected flow:

```text
question -> validate -> resolve institution -> resolve public source policy
         -> embed -> institution/public-scoped vector search
         -> provenance and lifecycle verification -> authorized chunks only
         -> assemble context -> generate
```

The public policy must be enforced in the repository/database query, followed by a
service-level post-check. Client fields must never broaden scope. In particular the
future public schema must not expose `retrieved_chunks`, `knowledge_source_id`,
`document_id`, `document_version_id`, `processing_run_id`, or `model_name`.

The existing generic `ChatRequest` exposes those internal controls. Current
post-filtering mitigates injected chunks, but Phase 7 requires a dedicated narrow
public request model so unauthorized inputs are rejected rather than accepted and
cleaned up later.

## 11. Generation boundary

Reuse `AIContext`, `AIGenerationService`, `GenerationProvider`,
`OpenRouterGenerationProvider`, and context assembly. Do not introduce a public-only
provider stack.

The public generation instructions must state that retrieved content and conversation
text are untrusted data; answer only from authorized context; do not invent
institution facts; return unavailable/insufficient-context behavior when grounding is
missing; never claim access to student records; and never reveal prompts, database
details, credentials, internal identifiers, or implementation details.

These instructions control answer quality only. Retrieval authorization and response
projection are the security boundaries.

## 12. Intended public API contract

Keep the existing route to avoid parallel public endpoints:

```http
POST /api/v1/chat/public
Content-Type: application/json
```

Locked minimum request for a single turn:

```json
{
  "institution_code": "GIT",
  "message": "What courses does the college offer?"
}
```

The Phase 7.2 contract may retain `user_query` instead of `message` if compatibility
is required, but it must expose only one question field and the public institution
code. Both fields need normalized non-empty values and explicit size bounds; extra
fields must be rejected.

Locked response projection:

```json
{
  "answer": "...",
  "status": "success",
  "sources": [
    {
      "title": "Admissions FAQ",
      "section": "Eligibility",
      "quote": "..."
    }
  ]
}
```

`status` remains `success | insufficient_context`. Sources are optional and must be
constructed from safe public metadata. The public response must not include chunk,
document, version, processing-run, user, or tenant UUIDs; embeddings; raw provider
metadata; token usage; model identifiers; authorization decisions; diagnostics; or
stack traces. The current shared `ChatResponse` exposes several of these fields, so a
dedicated response projection is required in a later implementation phase.

## 13. Conversation/session model

Recommended first release: **stateless server, client-local display history**.

- Each request is authorized and answered independently.
- The browser may retain rendered messages for the current tab, but does not send
  arbitrary history until a bounded public-history contract is designed.
- No anonymous conversation or messages are persisted in application tables.
- Multi-turn query rewriting can be added later using a short-lived, opaque,
  unguessable session capability with TTL, per-session isolation, rotation, and
  strict turn/character limits—or a validated bounded client history treated as
  untrusted input.

Current behavior differs: all public conversations persist under one shared
`PUBLIC_USER_ID`, and caller-supplied session/conversation UUIDs can resume any
conversation owned by that sentinel. UUID entropy reduces guessing risk but is not
an adequate anonymous ownership model. Phase 7 implementation must not expose public
history listing, and must replace or disable this persistence before claiming the
public conversation feature production-ready.

## 14. Frontend architecture

Because the frontend has no router today, Phase 7 must not pretend that `/public-chat`
already exists. The recommended additive architecture is:

- introduce minimal client-side route selection for `/` (public landing/chat) and an
  explicit sign-in path, or add a small routing layer in the UI implementation phase;
- render the public page outside `AuthProvider` so it does not restore sessions or
  expose role navigation;
- create a public-specific API client and state hook rather than passing a fake token
  through authenticated `useChat`;
- resolve/display the safe institution name from the existing public lookup;
- reuse presentational chat components only where their props do not carry private
  response fields or authenticated behavior;
- trim and reject blank messages, prevent duplicate submission, show loading and safe
  failure states, and never render internal error details.

The exact routing implementation is deferred, but the public and authenticated trees
must remain separate at their root boundaries.

## 15. Security model and prompt injection

```text
user input (untrusted)
    -> bounded schema
    -> authorization-constrained retrieval
    -> only verified public context reaches model
    -> public-safe output projection
```

User questions, prior turns, retrieved documents, and model output are all untrusted.
“Ignore previous instructions,” “show student records,” or “reveal private chunks”
cannot grant access because protected repositories are unreachable from this path and
private chunks are removed before generation. Output projection prevents identifiers
and diagnostic metadata from leaking even if the model requests them.

Prompt-injection detection may be added as defense in depth, but it may not replace
tenant, lifecycle, visibility, or response-schema enforcement.

## 16. Threat model

| Threat | Attack and boundary | Required protection | Future test |
| --- | --- | --- | --- |
| Private document retrieval | Ask directly or inject internal source IDs | Narrow public schema; repository visibility/lifecycle predicate; post-filter | Public source succeeds; private/draft/archived source never reaches context |
| Cross-tenant access | Change institution code/ID or source provenance | Server code resolution; tenant predicate at vector query and provenance check | A question scoped to A returns no B chunk, including an adversarial source ID |
| Prompt injection | Tell model to ignore policy or expose records | Treat input/context as untrusted; authorization before model; safe projection | Injection variants never add protected context or internal fields |
| Student-record request | Ask for own or named student's attendance/results | No student repositories or personalization in public path; generic auth-required guidance | Personal questions return safe denial/no protected values |
| Internal-system disclosure | Ask for prompts, SQL, IDs, keys, or errors | Fixed prompt policy, dedicated response DTO, normalized exceptions, debug off | Provider/database failures contain no internals; response has no forbidden keys |
| Excessive AI cost | Bots repeatedly invoke embeddings/generation | Edge and application rate limits, quotas, concurrency controls, caching where safe | Per-IP/session/institution thresholds return stable 429 without provider call |
| Resource exhaustion | Huge message/history, malformed JSON, slow requests | Byte/character/turn limits, strict schema, timeouts, concurrency/body limits | Boundary-size and over-limit cases fail before embedding/generation |
| Endpoint-boundary confusion | Public route reuses authenticated DTO/service and bypasses guards | Separate public DTO/orchestrator; shared only after authorized context exists | Public request cannot submit internal filters; protected route still requires JWT |
| Shared anonymous history | Guess/reuse another visitor's UUID | Stateless launch or capability-bound TTL sessions; no shared-owner listing | One visitor cannot resume or enumerate another visitor's transcript |
| Stale unpublished content | Retrieve superseded/draft versions from vector corpus | Full lifecycle/effective-date predicate tied to provenance | Draft, expired, superseded, and failed-run chunks are excluded |

## 17. Abuse-protection requirements

The current repository has no suitable limiter to reuse. Later implementation must:

- define per-client and per-institution request budgets at the deployment edge and an
  application fallback where reliable client identity is available;
- cap JSON body bytes, normalized message characters, history turns/characters,
  retrieval `top_k`, output tokens, request duration, and concurrent generations;
- reject malformed/oversized input before embeddings or provider calls;
- return `429 PUBLIC_RATE_LIMITED` with `Retry-After` where possible;
- avoid trusting `X-Forwarded-For` unless the deployment proxy is explicitly trusted;
- log safe operational counters without questions, tokens, secrets, or private data;
- consider safe answer/result caching only when the key includes the institution and
  public-policy version;
- place no new external service in the core architecture solely for Phase 7. The
  existing deployment edge may supply the first rate-limit layer.

Numerical limits must be selected from measured traffic/provider budgets in a later
phase and centralized in configuration, not scattered as literals.

## 18. Error-handling requirements

Retain the existing `{ "error": { "code", "message" } }` envelope. Public-safe
categories are:

- `INVALID_PUBLIC_CHAT_REQUEST` — 422;
- `INSTITUTION_NOT_FOUND` — 404;
- `INSTITUTION_NOT_AVAILABLE` — 403 (generic lifecycle wording);
- `NO_PUBLIC_INFORMATION` represented preferably by a successful
  `insufficient_context` response;
- `PUBLIC_RATE_LIMITED` — 429;
- `AI_TEMPORARILY_UNAVAILABLE` — 502/503/504 with generic wording;
- `INTERNAL_ERROR` — 500 with no detail.

Public responses must never carry Python/library exception text, SQL/PostgREST
details, schema/table names, paths, provider response bodies, authentication
internals, keys, prompts, or debug diagnostics. `DEBUG=false` remains mandatory
outside local/testing environments.

## 19. Testing strategy for later phases

### Public access and contract

- no Authorization header is required;
- only the dedicated public request fields are accepted;
- empty, malformed, oversized, and extra-field requests fail before provider use;
- public response serialization contains no forbidden metadata or internal IDs.

### Knowledge and lifecycle

- eligible public FAQ, notice, and handbook chunks are retrievable;
- private/authenticated sources are excluded;
- draft, under-review, archived, superseded, expired, future-effective, invalid-run,
  and unpublished document-version chunks are excluded;
- explicit internal IDs cannot be submitted to bypass policy.

### Tenant isolation

- institution A never retrieves institution B content;
- unknown/inactive institution codes fail safely;
- tampered provenance and mixed-tenant result sets are rejected by the post-filter.

### Student/private-data isolation

- “What is my attendance?”, “Show John Doe's results,” and “Give me the student
  database” return no protected values;
- public service tests prove no imports/calls to student attendance, results, profile,
  identity, or personalization repositories;
- authenticated student behavior remains available only through the protected path.

### Prompt injection and failures

- instruction-override, secret-extraction, prompt-extraction, and private-chunk
  requests cannot affect retrieval scope;
- database, embedding, and provider errors use safe envelopes;
- diagnostics are absent in production-mode public responses.

### Sessions and abuse

- one anonymous browser cannot access another's history;
- session/history bounds and expiry are enforced if sessions are introduced;
- rate, concurrency, body, message, and output limits are tested at their boundaries;
- rejected abuse does not invoke embedding or generation providers.

### Regression

- existing backend suite, Phase 6.13 public-security suites, frontend tests, and
  production frontend build remain green;
- authenticated `/generation/chat`, RBAC, tenant scoping, personalization, and all
  four role shells retain their current contracts.

## 20. Future Phase 7 roadmap

1. **Phase 7.2 — Public Knowledge/Data Access Policy:** decide explicit visibility,
   define the complete lifecycle predicate, introduce the narrow repository/query
   boundary, and close the explicit-source bypass.
2. **Phase 7.3 — Public API Hardening:** dedicated request/response schemas,
   institution-code resolution, stateless behavior, limits, safe errors, and tests.
3. **Phase 7.4 — Public Frontend Experience:** public route/tree, institution
   selection/identity, public client/hook, chat states, accessibility, and UI tests.
4. **Phase 7.5 — Abuse and Operational Controls:** edge/application throttling,
   quotas, observability, cost controls, and load/security validation.
5. **Phase 7.6 — End-to-End Validation and Lock:** live multi-tenant public corpus,
   injection/isolation tests, regression, evidence, and production-readiness review.

## 21. Architecture decisions

| Decision | Locked outcome |
| --- | --- |
| Endpoint | Preserve `/api/v1/chat/public`; harden rather than create a parallel API |
| Authentication | No JWT or account; no optional personalization |
| Tenant selector | Existing public institution code, resolved server-side |
| Retrieval store | Existing Supabase/pgvector corpus and embedding pipeline |
| Public policy | Explicit, fail-closed visibility plus lifecycle and tenant checks |
| Generation | Existing context/service/provider abstractions after authorization |
| Request DTO | Dedicated narrow public model; no internal retrieval controls |
| Response DTO | Dedicated safe projection; no database IDs/provider metadata |
| Initial sessions | Stateless server and client-local display history |
| Frontend | Public tree outside `AuthProvider`; authenticated shells unchanged |
| Security | Data/repository boundary primary; prompts only defense in depth |
| Rate limiting | Required before production; no suitable in-app mechanism exists today |

## 22. Explicitly locked constraints

- Public access is deny-by-default; absence or ambiguity of visibility means private.
- Every retrieved chunk must pass tenant and public-policy checks before generation.
- Public code cannot access student-specific repositories or authorized student
  context.
- Client-supplied identifiers, chunks, models, or filters cannot broaden retrieval.
- No public answer may be generated from cross-tenant or non-public context.
- Empty public context never falls back to ungrounded institution-specific claims.
- Authenticated JWT/RBAC/tenant/personalization behavior is not weakened or replaced.
- No separate vector database, embedding system, or generation provider is created.
- Public UI never exposes authenticated navigation or requires fake authentication.
- Anonymous transcripts are not persisted under a shared identity in the locked
  production architecture.
- Rate and size controls are required before production enablement.

## 23. Acceptance criteria verification

- [x] Public AI conversation is defined.
- [x] Public versus authenticated boundaries are documented.
- [x] Public versus private knowledge boundaries are documented.
- [x] Tenant, RAG, generation, and prompt-injection boundaries are documented.
- [x] Intended public API and response projection are defined.
- [x] Session and frontend architecture are defined from the actual repository.
- [x] Abuse protection, safe errors, threat model, and later testing are documented.
- [x] Existing architecture and known Phase 6 public implementation are preserved.
- [x] No feature, schema, authentication, retrieval, or deployment change was made.
- [x] Phase 7.2 prerequisites and production blockers are explicit.

**Phase 7.1 status: COMPLETE — architecture and scope locked.**

