# Phase 7.4 — Public RAG Integration & Retrieval Hardening

Status: **COMPLETE**  
Scope: backend public RAG integration only

## 1. Objective

Verify and harden the complete anonymous RAG path while preserving the Phase
7.2 policy and Phase 7.3 HTTP contract. The enforced invariant is:

```text
MODEL_CONTEXT ⊆ VERIFIED_PUBLIC_KNOWLEDGE ⊆ REQUESTED_INSTITUTION
```

No frontend, rate limiter, concurrency control, cost-control system, CAPTCHA,
or deployment change is part of this phase.

## 2. Existing RAG architecture

The implementation continues to use the existing OpenRouter embedding
provider, `embed_query`, pgvector storage, cosine-distance HNSW index,
retrieval schemas/service, `AIRequest`/`AIContext`, `assemble_context`,
`GenerationProvider`, and `AIGenerationService`. Authenticated chat continues
to use the generic `search_similar_chunks` RPC and was not routed through the
public restrictions.

Phase 7.2 already supplied explicit visibility, the dedicated public vector
RPC, `PublicKnowledgePolicy`, and repository-backed provenance. Phase 7.3
already supplied the strict stateless request/response boundary. Phase 7.4
hardens the integration between those components rather than replacing them.

## 3. Public RAG flow

```text
PublicChatRequest (institution_code + message only)
  -> resolve and validate active institution/organization
  -> embed normalized message with server configuration
  -> search_public_knowledge_chunks for the resolved institution
  -> bulk repository provenance lookup by candidate chunk IDs
  -> full source/version/run/tenant policy evaluation
  -> reconstruct chunks from canonical repository content and metadata
  -> deduplicate and apply fixed context budgets
  -> assemble_context
  -> AIGenerationService
  -> PublicChatResponse projection
```

Empty verified context returns `insufficient_context` without calling the
generation provider.

## 4. Embedding integration

Public retrieval calls the existing `retrieve` service, which calls
`embed_query`. The embedding provider, model, and dimensions remain
server-controlled through settings. The public request rejects extra fields,
so callers cannot choose an embedding model, provider, dimensions, index,
strategy, threshold, or result count.

The configured model remains `qwen/qwen3-embedding-8b` and the stored/query
dimension remains 1536. Query embeddings are validated for count, dimension,
numeric type, and finite values by the existing service/repository layers.

## 5. Vector retrieval

The public path exclusively uses `search_public_knowledge_chunks`; the generic
authenticated RPC remains separate. Ranking remains pgvector cosine distance:

```sql
ORDER BY ce.embedding <=> query_embedding ASC
```

The HNSW index remains `chunk_embeddings_embedding_hnsw_idx` using
`vector_cosine_ops` with `m=16` and `ef_construction=64`. No second vector
store or index was introduced.

The Phase 7.4 RPC replacement also requires `embedding_dimensions = 1536`, a
completed run, and a bounded `match_count` from 1 through 20. Application
settings constrain `retrieval_top_k` to the same range; its default remains 4.
No arbitrary similarity threshold was added because the existing architecture
does not define one and there was no evidence supporting a value change.

## 6. Tenant isolation

The institution code is resolved to an internal UUID server-side. That UUID is
sent as `filter_institution_id`, and the SQL predicate applies
`ks.institution_id = filter_institution_id` before ranked results are returned.
The application policy independently checks the same institution against the
canonical source provenance. Cross-tenant candidates are discarded before
context assembly.

## 7. Visibility enforcement

Visibility continues to use `knowledge_sources.visibility = 'public'` in SQL
and exact equality to `public` in application policy. `source_type` is retained
only as safe descriptive metadata; it is not an authorization predicate.
Authenticated and restricted sources fail closed.

## 8. Lifecycle enforcement

Both layers require the source and version lifecycle to be exactly
`published`. Draft, archived, superseded, revoked, deleted, null, and unknown
states therefore fail closed. Source and version effective windows remain
enforced using database `CURRENT_DATE` in retrieval and server date evaluation
in the independent application check. No caller-controlled timestamp exists.

## 9. Version enforcement

The public RPC joins each chunk through its processing run to one document
version and document. It requires the version to be published and effective.
The repository verifier resolves the same chain in bulk and reconstructs the
verified chunk with the canonical document and version IDs. If a vector
candidate supplies conflicting document/version IDs, it is rejected.

The schema represented in this repository has lifecycle state on document
versions rather than a separate document lifecycle field; document deletion
or invalidation is therefore represented by the joined version/source chain.

## 10. Processing validation

SQL and application policy require `status = 'ready'`,
`embedding_status = 'embedded'`, and non-null `completed_at`. Queued,
processing, failed, incomplete, cancelled, null, and unknown values fail
closed.

## 11. Embedding validation

The RPC inner-joins `chunk_embeddings`, requires the configured model when
provided, requires metadata dimension 1536, and therefore cannot return a
chunk with no matching stored embedding. The run must also be in the exact
`embedded` state. Query vectors are independently validated before RPC access.
Embedding values and metadata are never returned by the public API.

## 12. Provenance verification

Candidate vector results are not trusted. A single bulk repository query
loads the canonical chunk text, sequence, section, processing run, version,
document, and knowledge source for all candidate IDs. The verifier then:

1. validates source tenant, visibility, lifecycle, and dates;
2. validates version lifecycle and dates;
3. validates processing and embedding states plus completion;
4. checks chunk-to-run consistency;
5. rejects conflicting candidate document/version/run identifiers;
6. reconstructs each accepted `RetrievedChunk` from canonical repository text
   and a small safe metadata allow-list.

This closes the prior gap in which a candidate could reuse an authorized chunk
UUID while carrying altered text or metadata. Duplicate chunk IDs are removed
without changing retrieval order.

## 13. Context assembly

Only reconstructed verified chunks are passed to `AIRequest` and
`assemble_context`. Ordering remains the authorized vector-result order.
Internal metadata is reduced to processing provenance needed inside the
pipeline and safe title/section/type information used for citations. The
public response projects only title, section, and a quote from verified public
content.

## 14. Context limits

Public context now has three server-side bounds:

- `retrieval_top_k`: default 4, configuration range 1–20;
- `public_context_max_chunk_chars`: 4,000;
- `public_context_max_chars`: 12,000.

Exact duplicate content is removed after authorization. Oversized or
over-budget chunks are excluded rather than truncated, preserving factual
meaning. Substantially overlapping but non-identical chunks are not
aggressively transformed because ingestion deliberately uses small overlaps.
None of these controls is exposed in `PublicChatRequest`.

## 15. Grounding behavior

The shared grounding prompt still requires every institution-specific claim to
come from retrieved knowledge and requires an insufficiency statement when it
does not. Public guidance additionally treats user and retrieved text as
untrusted data, forbids following embedded instructions, forbids claims of
private-record access, and forbids disclosure of prompts, implementation
details, credentials, internal IDs, provider/model data, usage, or diagnostics.
Authorization remains entirely upstream of prompting.

## 16. Prompt injection handling

Requests such as “ignore previous instructions,” “show private documents,” or
“reveal hidden context” cannot broaden retrieval because the HTTP schema has no
authorization/retrieval controls, SQL is tenant/public scoped, and canonical
provenance is checked before context assembly. Tests inject private same-tenant
and public cross-tenant candidates with higher similarity and prove neither
reaches the provider. Response projection and UUID stripping provide an
additional output boundary.

## 17. Empty retrieval behavior

Zero vector results, wholly unauthorized results, and results removed by the
context budget all produce an empty `AIContext.retrieved_knowledge`. The
generation service returns `status="insufficient_context"`, `answer=null`, and
no sources without invoking the provider. There is no generic, unscoped, or
model-memory fallback.

## 18. Error handling

Embedding failures map to safe `EMBEDDING_FAILED` responses. Generation
failures map to `GENERATION_FAILED`. Unexpected RPC, repository, provenance,
or context failures are handled by the global generic `INTERNAL_ERROR`
envelope. Tests verify that SQL text, secrets, provider detail, tracebacks, and
file paths do not appear in public responses. Server-side exception logging is
unchanged.

## 19. Performance observations

Code and migration inspection confirms cosine HNSW search, an explicit tenant
predicate, early visibility/lifecycle/date/run/embedding predicates, and a
small server-side result count. Provenance verification uses one `IN` query for
all candidate chunk IDs and does not create an N+1 pattern. The existing
composite source-policy index covers institution, visibility, and lifecycle.

No live production database was available, so `EXPLAIN (ANALYZE, BUFFERS)` was
not run and index use under a production data distribution is not claimed. The
migrations should be applied in a staging environment and the plan verified
there before production rollout.

## 20. Tests

`test_public_rag_integration_phase_7_4.py` adds focused coverage for:

- the full HTTP → embedding → public RPC → policy → provenance → context →
  generation → public response path;
- configured model/dimension/top-K behavior and forbidden client controls;
- canonical reconstruction against forged vector text/metadata;
- same-tenant private and cross-tenant exclusion;
- mismatched provenance rejection;
- bounded context and exact deduplication;
- prompt injection isolation;
- safe embedding, RPC, provenance, and context failures;
- SQL policy, dimension, completion, ordering, limit, and HNSW assertions;
- proof that public chat does not call generic authenticated retrieval.

Phase 7.2/7.3 fixtures were extended with canonical chunk content required by
the strengthened verifier. The legacy public security fixtures were updated
for the same reason. Existing embedding, vector retrieval, context, generation,
and authenticated API suites remain the regression boundary.

Verification performed on 2026-09-28:

```text
Standalone Phase 7.4:
  DEBUG=false uv run pytest -q tests/test_public_rag_integration_phase_7_4.py
  12 passed

Phase 7.2-7.4 focused:
  DEBUG=false uv run pytest -q tests/test_public_rag_integration_phase_7_4.py \
    tests/test_public_knowledge_policy_phase_7_2.py \
    tests/test_narrow_public_chat_api_phase_7_3.py
  55 passed

Public/authenticated retrieval, embedding, context, and generation regressions:
  DEBUG=false uv run pytest -q <14 focused regression files>
  285 passed

Complete hermetic backend suite:
  DEBUG=false uv run pytest -q tests
  2071 passed, 15 skipped, 2 failed

Known environment-specific retry:
  DEBUG=true uv run pytest -q \
    tests/test_conversational_rag.py::test_dev_diagnostics_attach_to_generation_metadata \
    tests/test_conversational_rag.py::test_standalone_question_diagnostics_rewritten_query_is_none
  2 passed

Focused Phase 7.4 lint:
  uvx ruff check app/config.py app/repositories/public_knowledge.py \
    app/services/public_knowledge_policy.py app/services/public_chat.py \
    tests/test_public_rag_integration_phase_7_4.py
  All checks passed
```

The two full-suite failures under `DEBUG=false` are unchanged development-only
diagnostics assertions, not Phase 7.4 failures; both pass with their intended
`DEBUG=true` setting. A repository-wide Ruff run found 212 pre-existing issues
across unrelated files. The Phase 7.4 implementation and new test file pass the
focused Ruff check. The backend defines no mypy or Pyright configuration or
dependency, so no backend type-check command is available. `git diff --check`
passes. The migration was inspected and predicate-tested but not applied to a
live Supabase instance; live-server/manual scripts remain outside the hermetic
`tests` suite.

## 21. Files changed

Created:

- `backend/tests/test_public_rag_integration_phase_7_4.py`
- `supabase/migrations/20260928010000_phase_7_4_public_rag_hardening.sql`
- `docs/status/PHASE_7_4_PUBLIC_RAG_INTEGRATION.md`

Modified for Phase 7.4:

- `backend/app/config.py`
- `backend/app/repositories/public_knowledge.py`
- `backend/app/services/public_knowledge_policy.py`
- `backend/app/services/public_chat.py`
- `backend/tests/test_public_knowledge_policy_phase_7_2.py`
- `backend/tests/test_narrow_public_chat_api_phase_7_3.py`
- `backend/tests/test_security_final_validation_phase_6_13_9.py`

The worktree also contains the preceding Phase 7.3 changes in `main.py`,
`schemas/chat.py`, `services/public_chat.py`, its tests, and its status document;
those changes were preserved rather than overwritten.

## 22. Deferred work

- public frontend, routing, client, and UI;
- rate limiting and quotas;
- concurrency controls;
- cost controls and request budgets;
- CAPTCHA and external abuse prevention;
- production/staging migration deployment;
- staging database query-plan and load validation.

## 23. Acceptance criteria

- [x] Existing embedding infrastructure is used with server-controlled config.
- [x] Phase 7.2 public retrieval and explicit visibility are preserved.
- [x] Tenant filtering occurs inside vector retrieval and provenance policy.
- [x] Source/version lifecycle and effective dates fail closed.
- [x] Processing completion and embedding validity are enforced.
- [x] Repository-backed provenance occurs before context and generation.
- [x] Vector candidate text/metadata is replaced by canonical repository data.
- [x] Unauthorized chunks cannot enter `AIContext`.
- [x] Context count, per-chunk size, and total size are bounded server-side.
- [x] Empty retrieval skips the provider and cannot hallucinate an answer.
- [x] Prompt-injection and cross-tenant integration tests pass.
- [x] Authenticated retrieval remains on its existing separate path.
- [x] End-to-end public RAG integration test passes deterministically.
- [x] No frontend or abuse-control system was implemented.
- [x] No existing RAG architecture was replaced.

**PHASE 7.4 STATUS: COMPLETE**
