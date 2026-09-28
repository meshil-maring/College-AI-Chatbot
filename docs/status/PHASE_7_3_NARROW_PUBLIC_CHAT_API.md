# Phase 7.3 — Narrow Public Chat API

Status: **COMPLETE**  
Endpoint: `POST /api/v1/chat/public`  
Authentication: **Not required**

## 1. Objective

Phase 7.3 finalizes the existing anonymous backend boundary as a narrow,
single-turn API. It accepts only a public institution code and one bounded
message, resolves the tenant server-side, retrieves and re-verifies only Phase
7.2-authorized public knowledge, generates only from that verified context, and
returns a public-safe projection.

No frontend, rate limiter, concurrency limiter, cost-control system, deployment
change, or anonymous persistent history was added.

## 2. Existing endpoint and investigation

The repository already registered `POST /api/v1/chat/public` in `app.main`
without `Depends(get_current_user)`. Phase 7.2 had already added the strict
`PublicChatRequest`, safe `PublicChatResponse`, code-based institution lookup,
dedicated public retrieval RPC, centralized `PublicKnowledgePolicy`, and final
repository-backed provenance verification.

The following areas were inspected before modification:

- architecture and policy locks:
  `PHASE_7_1_PUBLIC_AI_CONVERSATION_ARCHITECTURE.md` and
  `PHASE_7_2_PUBLIC_KNOWLEDGE_ACCESS_POLICY.md`;
- API registration, authenticated/public routes, exception handlers, and
  OpenAPI behavior in `backend/app/main.py`;
- public and authenticated schemas in `backend/app/schemas/chat.py` and the
  internal generation/retrieval schemas;
- public orchestration, context assembly, generation, retrieval, and policy in
  `backend/app/services/public_chat.py`, `context.py`, `generation.py`,
  `retrieval.py`, and `public_knowledge_policy.py`;
- tenant resolution in `backend/app/repositories/tenancy.py`;
- public retrieval/provenance access in
  `backend/app/repositories/public_knowledge.py`;
- Phase 7.2, legacy public security, authenticated chat, validation, and
  OpenAPI test suites.

The remaining material gap was that the HTTP path delegated to the legacy
public compatibility orchestrator, which created conversations and messages
under the shared `PUBLIC_USER_ID`. The HTTP path is now stateless. The legacy
internal entry point remains unchanged for backward compatibility with older
service callers and tests, but it is no longer used by the public route.

## 3. Request contract

```json
{
  "institution_code": "COLLEGE001",
  "message": "What courses does the college offer?"
}
```

`PublicChatRequest` uses `extra="forbid"`. It is the sole request body model for
the public endpoint. The API does not accept internal IDs, source selection,
retrieved chunks, retrieval limits or thresholds, embedding/generation models,
providers, temperature, token limits, debug flags, session IDs, conversation
IDs, roles, student identifiers, or authorization controls.

## 4. Response contract

```json
{
  "answer": "The college offers ...",
  "status": "success",
  "sources": [
    {
      "title": "Academic Handbook",
      "section": "Programs",
      "quote": "..."
    }
  ]
}
```

`PublicChatResponse` and `PublicSource` are strict models. Status is restricted
to `success` or `insufficient_context`. The projection contains no database,
chunk, document, version, processing-run, user, tenant, model, provider, usage,
timing, diagnostics, or debug fields.

## 5. Authentication boundary

The route has no authentication dependency and succeeds without an
`Authorization` header. This does not bypass authorization: public access is
authorized through deterministic institution resolution, institution and
organization eligibility, public visibility/lifecycle checks, tenant-scoped
retrieval, and final provenance verification.

The authenticated endpoint remains separate at
`POST /api/v1/generation/chat`, still uses `Depends(get_current_user)`, derives
tenant/user identity server-side, and retains its existing request, response,
history, personalization, and persistence behavior.

## 6. Tenant validation

The normalized public `institution_code` is resolved with
`get_institution_by_code`. An unknown code returns `404
INSTITUTION_NOT_FOUND` before retrieval. The resolved internal ID is then
validated through the existing active-institution and organization eligibility
rules. Only that resolved ID is used in the retrieval request, retrieval scope,
and provenance policy.

No public request field can provide or override the internal institution ID.
Tests inject a higher-scoring Institution B result into an Institution A
request and verify that it is removed before context assembly.

## 7. Request validation

- `institution_code`: trimmed, uppercased, non-empty, maximum 32 characters;
- `message`: whitespace-normalized, non-empty, maximum 4,000 characters;
- oversized messages are rejected rather than truncated;
- missing fields, whitespace-only values, malformed JSON, and extra fields
  return the established sanitized `422 VALIDATION_ERROR` envelope;
- validation occurs before public service, retrieval, embedding, or generation
  execution.

## 8. Retrieval integration

The stateless public orchestrator constructs its own internal
`RetrievalRequest` from server configuration and the resolved tenant. It always
sets `public_only=True`, uses the configured retrieval limit and embedding
model, and never copies retrieval controls from the client.

The Phase 7.2 path remains authoritative:

1. the dedicated public SQL RPC applies institution, visibility, publication,
   effective-date, version, processing, and embedding predicates;
2. `PublicKnowledgePolicy.authorize_chunks` re-resolves each returned chunk's
   repository provenance;
3. only verified chunks proceed to context assembly.

Empty or wholly rejected retrieval results remain empty and produce
`insufficient_context`; there is no generic or unscoped fallback.

## 9. Generation integration

The endpoint reuses `AIRequest`, `RetrievalScope`, `assemble_context`,
`AIGenerationService`, `GenerationProvider`, and
`OpenRouterGenerationProvider`. Conversation history is always empty for this
stateless contract. The generation service receives only the post-policy chunk
list and does not decide knowledge authorization. Public-only grounding guidance
also tells the model not to reproduce prompts, database/implementation details,
credentials, internal identifiers, provider/model data, usage, diagnostics, or
retrieved-chunk labels.

When no verified chunks exist, `AIGenerationService` returns
`insufficient_context` without calling the provider.

Citation labels are parsed internally before projection. Retrieved-chunk labels
and UUID-shaped internal identifiers are stripped from the answer while safe
structured citations are retained, so a model-generated citation marker cannot
leak a chunk ID to the anonymous caller.

## 10. Error handling

- validation errors use the global sanitized `422 VALIDATION_ERROR` envelope;
- unknown institution codes use `404 INSTITUTION_NOT_FOUND`;
- ineligible institutions use the existing safe eligibility errors;
- provider failures use `500 GENERATION_FAILED` without the provider exception;
- unexpected repository/retrieval failures use the global generic `500
  INTERNAL_ERROR` response;
- SQL, table names, credentials, stack traces, provider details, and raw
  exception messages remain server-side.

The endpoint's documented OpenAPI responses use `PublicAPIErrorResponse` for
401, 403, 404, 422, and 500 outcomes.

## 11. Logging

No new request-body or message logging was introduced. Existing global error
logging records the request path and server-side traceback for operations while
the response remains generic. The public orchestrator does not log JWTs, API
keys, raw request payloads, student information, or authorization metadata.

## 12. OpenAPI

The generated operation documents:

- `POST /api/v1/chat/public`;
- `Authentication: Not required`;
- `PublicChatRequest` as the request schema;
- `PublicChatResponse` as the success schema;
- safe 401/403/404/422/500 responses;
- no operation security requirement;
- only `institution_code` and `message` in the request schema.

Automated verification also checks that all internal retrieval, provider,
model, and debug properties are absent.

## 13. Security tests

`backend/tests/test_narrow_public_chat_api_phase_7_3.py` covers:

- unauthenticated valid requests and normalization;
- missing, blank, whitespace-only, oversized, malformed, and extra input;
- rejection of source/document/version/run IDs, retrieval tuning, model,
  provider, temperature, token, and debug controls;
- unknown institution rejection before retrieval;
- same-tenant retrieval and cross-tenant chunk removal before generation;
- an API-level eligibility matrix covering authenticated/restricted visibility,
  unpublished/archived/future/expired sources, invalid versions, failed
  processing, and unembedded content;
- strict stateless behavior with persistence/history functions guarded by
  failure sentinels;
- safe insufficient-context behavior;
- safe generation and unexpected retrieval error envelopes;
- response-field safety and strict response models;
- OpenAPI request/response/authentication/error documentation.

Phase 7.2 tests continue to cover public/authenticated/restricted visibility,
source lifecycle and effective dates, version validity, failed processing,
embedding state, explicit-source denial, repository provenance, and SQL policy
parity.

## 14. Regression tests

Verification performed on 2026-09-28:

```text
Focused Phase 7.2 + 7.3:
  DEBUG=false uv run pytest -q tests/test_narrow_public_chat_api_phase_7_3.py tests/test_public_knowledge_policy_phase_7_2.py
  43 passed

Legacy public security + authenticated chat:
  DEBUG=false uv run pytest -q tests/test_public_protected_ai_phase_6_13_8.py tests/test_security_final_validation_phase_6_13_9.py tests/test_generation_api.py tests/test_personalized_chat_phase_6_10.py tests/test_personalized_chat_6147.py
  206 passed

All automated backend tests:
  DEBUG=false uv run pytest -q tests
  2058 passed, 15 skipped, 2 failed
  The two failures are existing development-diagnostics assertions that require
  DEBUG=true; they are unrelated to Phase 7.3 and both pass under their intended
  environment:

  DEBUG=true uv run pytest -q tests/test_conversational_rag.py::test_dev_diagnostics_attach_to_generation_metadata tests/test_conversational_rag.py::test_standalone_question_diagnostics_rewritten_query_is_none
  2 passed
```

A bare `uv run pytest -q` additionally collected six live-server scripts under
`backend/scripts`. Collection failed because no localhost backend was running.
Those scripts are manual/deployment validation utilities rather than isolated
automated tests; `uv run pytest -q tests` is the complete backend unit/integration
suite.

## 15. Files changed

- `backend/app/main.py`
- `backend/app/schemas/chat.py`
- `backend/app/services/public_chat.py`
- `backend/tests/test_narrow_public_chat_api_phase_7_3.py`
- `docs/status/PHASE_7_3_NARROW_PUBLIC_CHAT_API.md`

No frontend or database migration files were changed.

## 16. Deferred controls

The following remain explicitly deferred to later Phase 7 work:

- rate limiting;
- concurrency limiting;
- AI request budgets and cost controls;
- CAPTCHA and external abuse-prevention services;
- public frontend, routing, components, hooks, and API client;
- anonymous multi-turn or persistent history;
- production deployment and edge configuration.

## 17. Known limitations

- The endpoint is intentionally single-turn; follow-up context is not retained
  or accepted.
- The application still requires later abuse controls before an unrestricted
  production launch.
- Institution-specific answers depend on published, processed, embedded public
  knowledge being available and current.
- Legacy `process_chat_request` in the public service retains its historical
  persistence behavior for internal backward compatibility, but the HTTP route
  cannot reach it through `PublicChatRequest`.

## 18. Acceptance criteria

- [x] `/api/v1/chat/public` is unauthenticated.
- [x] `PublicChatRequest` is the only public request contract.
- [x] Unknown and internal request fields are rejected.
- [x] Institution code is normalized, resolved, and validated server-side.
- [x] Tenant isolation is applied at retrieval and provenance verification.
- [x] Public retrieval uses the Phase 7.2 policy path.
- [x] Client input cannot broaden retrieval authorization.
- [x] Generation receives only verified public context.
- [x] `PublicChatResponse` is a strict, safe projection.
- [x] Internal metadata is absent from responses.
- [x] Safe validation, provider, retrieval, and unexpected errors are verified.
- [x] Explicit request-size validation exists (4,000 characters).
- [x] OpenAPI describes the public contract and no-auth boundary accurately.
- [x] Focused public API and policy tests pass.
- [x] Legacy public security tests pass.
- [x] Authenticated chat regressions pass.
- [x] No public frontend was implemented.
- [x] No rate limiter was implemented.
- [x] No anonymous persistent history is used by the endpoint.
- [x] Documentation is complete.

## Final status

**PHASE 7.3 STATUS: COMPLETE**

