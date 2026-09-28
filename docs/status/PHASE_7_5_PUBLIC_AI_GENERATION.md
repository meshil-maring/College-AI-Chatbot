# Phase 7.5 — Public AI Generation & Safe Response

Status: **COMPLETE**  
Phase type: backend generation hardening, tests, and documentation  
Date: 2026-09-28

## 1. Objective

Finalize the anonymous generation boundary so the model receives only canonical,
policy-authorized public knowledge for the resolved institution and the HTTP response
contains only public-safe fields. Retrieval authorization remains the security
boundary; model instructions and output checks are defense in depth.

## 2. Generation architecture

```text
PublicChatRequest
  -> institution-code resolution and lifecycle validation
  -> public-only retrieval RPC
  -> PublicKnowledgePolicy canonical provenance verification
  -> bounded verified chunks
  -> AIContext(public=True)
  -> shared AIGenerationService and GenerationProvider
  -> targeted output validation and sanitization
  -> PublicChatResponse
```

The public path reuses the existing provider stack. It does not retrieve inside the
generation layer, accept generation settings from the caller, load personalization,
or persist anonymous conversation history.

## 3. Public AIContext

`AIContext.public` is the explicit internal boundary marker. Only
`process_public_request` sets it, after `PublicKnowledgePolicy.authorize_chunks` has
replaced retrieval candidates with canonical repository content. A public context
also carries the server-resolved institution internally for inspection and requires:

- no client-selected model;
- no student context;
- no conversation history;
- a server-controlled output-token limit.

The marker does not authorize chunks by itself. The invariant is:

```text
AIContext(public=True).retrieved_knowledge
    subset of canonical VerifiedPublicChunks for AIContext.institution_id
```

The institution ID, marker, output limit, chunks, and all other internal context
fields are absent from `PublicChatResponse`.

## 4. Grounding rules

Public instructions require the provider to use supplied verified context, prefer it
over general assumptions, avoid unsupported institution facts, treat questions and
retrieved text as untrusted data, ignore instruction-like retrieved content, and
never reveal prompts, credentials, database details, identifiers, provider details,
diagnostics, or private records. Source conflicts must be reported as uncertainty,
not silently resolved.

These rules are not authorization. Private and cross-tenant chunks are removed
before context assembly.

## 5. No-context behavior

An empty verified chunk list bypasses the provider in `AIGenerationService`. The
public endpoint returns the stable response:

```json
{"answer": null, "status": "insufficient_context", "sources": []}
```

There is no model-only or general-knowledge fallback.

## 6. Unsupported-question behavior

The product remains a college-knowledge assistant. An unrelated question is answered
only when verified public college context supports it; otherwise the normal
insufficient-context behavior applies. If semantically irrelevant context reaches
generation, the public instructions require the model to state that the question is
outside the available college information. Phase 7.5 does not broaden the product to
general knowledge or programming assistance.

## 7. Hallucination protection

Canonical verified chunks are the only institution facts supplied to generation.
Empty context skips generation, grounding instructions forbid facts absent from the
context, and conflicting context must be surfaced as conflicting. Lifecycle and
recency selection remain retrieval responsibilities; generation does not reinterpret
publication state.

## 8. Prompt-injection behavior

User questions and retrieved content are explicitly framed as untrusted. Injection
cannot add chunks, tenant scope, history, or student data. Exact disclosure of the
system/public prompt, stack-trace-shaped output, obvious local application paths, and
API-key-shaped values are rejected as invalid generation output. Internal chunk
labels and UUID-shaped identifiers are removed by the targeted public projection.

## 9. Private-record protection

The public path has no student repository or personalization access. Deterministic
pre-retrieval checks reject requests for the caller's or a named person's attendance,
marks, results, email, phone number, profile, registration/roll number, student
records/database, or private staff/admin information with `401 AUTH_REQUIRED`.
General policy questions such as attendance requirements remain eligible for public
knowledge retrieval.

## 10. Source and citation handling

The model may refer only to retrieved chunk markers. The server extracts markers,
discards references not present in verified context, and projects only canonical
`title`, `section`, and `quote` fields. The public response never includes chunk,
document, version, processing-run, institution, or tenant IDs. Invented markers
cannot create citations because they do not match verified chunks. The final source
projection also removes chunk labels and UUID-shaped text from every exposed source
field.

## 11. Output limits

The server supplies `max_tokens=800` to the public provider call through the internal
context. The public answer has a second fixed 12,000-character ceiling; an oversized
provider result is rejected rather than silently truncated. Neither control appears
in `PublicChatRequest`.

## 12. Provider configuration

The configured OpenRouter provider and `settings.openrouter_model` are reused. The
public client cannot select the model, provider, endpoint, temperature, output token
budget, or timeout. Authenticated contexts leave `max_output_tokens` unset, preserving
their existing provider request behavior.

## 13. Provider failure handling

Public generation maps provider timeout to `504 PUBLIC_GENERATION_TIMEOUT`. Provider
HTTP, authentication, rate-limit, network, configuration, malformed-result, and
unexpected failures become a stable `PUBLIC_GENERATION_UNAVAILABLE` or
`PUBLIC_GENERATION_INVALID_RESPONSE` envelope. Raw bodies, exception strings, keys,
request IDs, stack traces, models, and provider configuration are never returned.

## 14. Timeout handling

Public OpenRouter calls use a server-controlled 30-second timeout. The provider now
passes its configured timeout explicitly to both shared and injected HTTP clients.
The authenticated provider keeps its existing 60-second default.

## 15. Output sanitization

Sanitization is deliberately narrow. It removes internal retrieved-chunk labels and
UUID-shaped identifiers, normalizes punctuation/spacing left by those removals, and
rejects high-confidence prompt/diagnostic leakage or oversized output. It does not
perform broad keyword rewriting of normal answers.

## 16. Safe response projection

All successful public results pass through strict `PublicChatResponse` and contain
only `answer`, `status`, and a list of `PublicSource(title, section, quote)`. Extra
fields are forbidden. Provider/model data, token usage, timings, diagnostics, raw
context, and internal identifiers remain internal.

## 17. Observability

No verbose or content logging was added. Existing normalized exception handlers and
server-side exception logging remain in effect. Public responses expose no diagnostic
metadata. The stateless public path does not write messages, retrieval operations, or
AI-response rows.

## 18. Tests

`backend/tests/test_public_ai_generation_phase_7_5.py` covers public-context
validation, grounding rules, empty context, private-record denial, policy-question
non-regression, provider timeout/failures/malformed results, server-owned token and
timeout settings, prompt/diagnostic leakage, UUID/chunk-marker sanitization, and the
hard response limit.

The Phase 7.4 HTTP integration test captures the actual provider `AIContext` and
asserts `public=True`, the correct resolved institution, no model/student/history,
the fixed output budget, and only the one canonical eligible public chunk. Existing
Phase 7.3/7.4 tests continue to cover the full HTTP → public RAG → provenance →
generation → safe response flow and private/cross-tenant exclusion.

## 19. Files changed

- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/schemas/generation.py`
- `backend/app/services/context.py`
- `backend/app/services/generation.py`
- `backend/app/services/generation_provider.py`
- `backend/app/services/public_chat.py`
- `backend/tests/test_narrow_public_chat_api_phase_7_3.py`
- `backend/tests/test_public_rag_integration_phase_7_4.py`
- `backend/tests/test_public_ai_generation_phase_7_5.py`
- `backend/tests/test_ai_context_builder_6146.py`
- `docs/status/PHASE_7_5_PUBLIC_AI_GENERATION.md`

Verification executed from `backend/` with a valid test environment setting:

```text
$env:DEBUG='false'; uv run pytest -q tests/test_public_ai_generation_phase_7_5.py tests/test_public_rag_integration_phase_7_4.py tests/test_narrow_public_chat_api_phase_7_3.py tests/test_generation_provider.py tests/test_generation_service.py tests/test_generation.py tests/test_generation_api.py
154 passed, 1 warning

$env:DEBUG='true'; uv run pytest -q tests
2097 passed, 15 skipped, 6 warnings
```

The repository has no configured Ruff, Black, mypy, or Pyright task in
`backend/pyproject.toml`; no unconfigured lint/type command was claimed as run.

## 20. Deferred work

- public frontend and route;
- anonymous/client conversation UI and persistent anonymous history;
- rate limiting and concurrency controls;
- AI cost controls;
- CAPTCHA and external abuse prevention;
- production deployment.

## 21. Acceptance criteria

- [x] Public generation receives only canonical verified public context.
- [x] The public `AIContext` boundary is explicit and documented.
- [x] Public grounding and prompt-injection instructions are implemented.
- [x] Empty context bypasses generation safely.
- [x] Unsupported-question scope is defined without general-knowledge fallback.
- [x] Hallucination and contradictory-context behavior are defined and tested.
- [x] Private-record claims are blocked before retrieval/generation.
- [x] Sources are projected from verified context without internal IDs.
- [x] Provider/model/settings remain server-controlled.
- [x] Generation output and public answer size are bounded.
- [x] Provider failures and timeouts use sanitized errors.
- [x] Public output passes through a strict safe response projection.
- [x] End-to-end and provider-context inspection tests pass.
- [x] Authenticated generation behavior remains separate and covered by regression.
- [x] No frontend, rate limiting, concurrency, cost, or CAPTCHA work was added.
- [x] Phase 7.2–7.4 authorization and provenance guarantees remain intact.
