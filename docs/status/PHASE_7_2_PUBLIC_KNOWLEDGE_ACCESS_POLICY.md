# Phase 7.2 — Public Knowledge/Data Access Policy

Status: **COMPLETE**  
Completed: 2026-09-28

## 1. Objective

Phase 7.2 makes this invariant server-authoritative:

> Public AI context consists only of explicitly public knowledge owned by the
> resolved institution and backed by a published, effective source and document
> version plus a completed, embedded processing run.

The frontend, authentication design, AI provider, vector database, and
authenticated retrieval policy were not redesigned.

## 2. Existing implementation investigated

The investigation traced `POST /api/v1/chat/public` through `app.main`,
`app.schemas.chat.ChatRequest`, `app.services.public_chat`, generic retrieval,
`search_similar_chunks`, context assembly, generation, citations, and response
serialization. It also inspected authenticated chat, tenant/security services,
knowledge/admin/ingestion repositories, source/document/version/run schemas,
FAQ and notice publication, schema export, migrations, indexes, constraints,
grants, and the existing Phase 6.13.8/6.13.9 security suites.

The existing storage chain is:

```text
knowledge_sources
  -> documents
  -> document_versions
  -> document_processing_runs
  -> knowledge_chunks
  -> chunk_embeddings
```

Existing lifecycle vocabularies are:

- source/version: `draft`, `under_review`, `approved`, `published`, `archived`,
  `superseded`;
- processing run: `queued`, `processing`, `ready`, `failed`;
- embedding: `pending`, `processing`, `embedded`, `failed` (nullable in the
  historical migration).

Documents and chunks have no independent lifecycle/deletion column. Deletion is
physical and enforced by the required foreign-key provenance chain.

## 3. Security risks discovered

The old public service inferred visibility from `faq`, `notice`, and `handbook`
source types. Its explicit `knowledge_source_id` branch did not require a
published lifecycle. Generic vector search filtered metadata but not public
visibility, effective dates, version lifecycle, or run validity. Final filtering
resolved only a run-to-source relationship. The HTTP route accepted `ChatRequest`
and returned `ChatResponse`, exposing source/document controls, supplied chunks,
model selection, UUIDs, model data, usage, and diagnostics.

The canonical FAQ/notice create paths also synchronized new records before the
record-level `is_published` flag was true. Creation now remains outside RAG;
publish performs the first sync, and update/unpublish removes content whenever
the record is inactive or unpublished.

The backend uses the Supabase service-role client. RLS therefore cannot be the
application's public authorization boundary.

## 4. Public knowledge definition

A chunk is public only when every condition is true:

```text
resolved institution is active and belongs to an allowed organization
AND knowledge source belongs to that institution
AND knowledge source visibility = public
AND knowledge source lifecycle_status = published
AND source effective_from/effective_until contains the current date
AND document and provenance links exist
AND document version lifecycle_status = published
AND version effective_from/effective_until contains the current date
AND processing run status = ready
AND processing run embedding_status = embedded
AND processing run has completed_at
AND the returned chunk ID belongs to that processing run
```

Missing, malformed, or unknown policy values fail closed.

## 5. Visibility model

`knowledge_sources.visibility` supports:

- `public`: eligible for anonymous retrieval if every other rule passes;
- `authenticated`: reserved for authenticated policy expansion;
- `restricted`: private/fail-closed default.

`source_type` remains descriptive metadata. It is not an authorization input.
Admin knowledge DTOs expose and validate the new field. Generic sources default
to `restricted`. The existing canonical FAQ/notice publication workflow writes
`public` deliberately.

## 6. Publication model

Visibility does not publish a source. Public retrieval separately requires
`knowledge_sources.lifecycle_status = published`. Approved, under-review, and
draft records are denied. The dedicated SQL function and application policy
both apply this rule.

## 7. Lifecycle rules

Archived, superseded, revoked/deleted-like unknown states, ineffective sources,
and missing provenance are denied. Effective date bounds are inclusive. Physical
deletion or a broken FK chain prevents authorization because the policy cannot
resolve complete provenance.

## 8. Version rules

The exact version that produced the chunk must be `published` and currently
effective. Draft, approved-only, archived, and superseded versions are denied.
This prevents an older or not-yet-released version from becoming context merely
because its embedding remains present.

## 9. Processing-state rules

The producing run must be `ready`, have `embedding_status = embedded`, and have a
completion timestamp. Queued, processing, failed, incomplete, legacy-null, and
failed-embedding runs are denied. The final verifier resolves the actual chunk
row and its run; client-shaped metadata is not sufficient.

## 10. Tenant isolation

The public request accepts the globally unique institution code. The server
normalizes and resolves it, validates the institution and organization lifecycle,
and carries only the resolved UUID internally. Both the SQL vector predicate and
the final provenance predicate require the same institution.

## 11. Public retrieval policy

`PublicKnowledgePolicy` is the reusable application boundary. Pure functions
evaluate source dates/state and complete provenance; repository-backed methods
authorize explicit sources, enumerate eligible candidates, and verify chunks.

Defense in depth is:

```text
strict request
  -> public code resolution and tenant validation
  -> source policy
  -> search_public_knowledge_chunks SQL predicate
  -> vector similarity ranking
  -> chunk-ID/full-provenance re-verification
  -> context assembly
  -> generation
  -> safe response projection
```

No rejected chunk reaches context assembly or the generation provider.

## 12. Explicit source authorization

The public HTTP DTO no longer accepts `knowledge_source_id`. The internal
compatibility path still validates a supplied ID through the same explicit
visibility, tenant, publication, and effective-date source policy, then restricts
final chunk verification to that source. Missing, private, cross-tenant,
unpublished, and ineffective IDs return the same non-enumerating 403 decision.

## 13. Public request contract

```json
{
  "institution_code": "GIT",
  "message": "What courses does the college offer?"
}
```

Both strings are normalized and bounded (`institution_code` 32 characters,
`message` 4000 characters). Pydantic `extra="forbid"` rejects source/document/
version/run IDs, supplied chunks, model selection, debug flags, and all other
unexpected controls.

## 14. Public response projection

```json
{
  "answer": "...",
  "status": "success",
  "sources": [
    {"title": "Admissions FAQ", "section": "Eligibility", "quote": "..."}
  ]
}
```

The projection contains no chunk/document/version/run/conversation/message/user/
tenant UUIDs, similarity scores, provider/model fields, usage, diagnostics,
embeddings, raw metadata, or authorization details.

## 15. Database and RLS considerations

The inspected schema export and migrations contain service-role table grants and
no public RLS policy that can safely express this joined vector predicate. The
new `SECURITY INVOKER` function is revoked from `PUBLIC`, `anon`, and
`authenticated`, and granted only to `service_role`. No broad anon table policy
was added. This preserves ingestion/admin/authenticated workflows while keeping
application authorization explicit. Authenticated search continues using the
existing `search_similar_chunks` RPC unchanged.

## 16. Tests

New focused tests cover public/authenticated/restricted visibility, tenant
isolation, source and version lifecycle, effective dates, processing and embedding
states, explicit IDs, strict request rejection, SQL predicate presence, safe
response shape, and an HTTP integration attack in which a private chunk returned
by a mocked retriever is removed before generation.

Executed results:

```text
Phase 7.2 + public/retrieval focused suite:
  98 passed

Final public-policy + publication/admin boundary suite:
  57 passed

Updated security/debug regression subset:
  191 passed, 4 skipped

Complete backend automated suite (DEBUG=true):
  2032 passed, 15 skipped

Frontend full suite:
  401 passed, 1 timed out (unrelated RegistrationForm timing test)
Frontend isolated retry of timed-out file:
  25 passed
Frontend TypeScript + production build:
  passed
```

The repository-wide bare `pytest` command also collects manual/live-server
scripts and failed collection because no backend was running. `pytest tests` is
the project's hermetic automated regression command and passed as recorded.

## 17. Files changed

Created:

- `backend/app/repositories/public_knowledge.py`
- `backend/app/services/public_knowledge_policy.py`
- `backend/tests/test_public_knowledge_policy_phase_7_2.py`
- `supabase/migrations/20260928000000_phase_7_2_public_knowledge_policy.sql`
- this status document

Modified:

- public route, request/response schemas, public chat, and retrieval service;
- admin FAQ/notice publication services and API tests;
- admin/ingestion/tenancy knowledge projections and canonical publication;
- existing security fixtures/assertions to express explicit visibility and full
  provenance.

No frontend runtime source was changed.

## 18. Migration details

The migration adds the non-null checked visibility field and a composite policy
index. Its default is `restricted`. It backfills only rows that the prior public
policy already exposed: `published` sources whose types are FAQ, notice, or
handbook. It then creates the lifecycle-aware public vector RPC and restricts its
execution grant.

## 19. Backward compatibility

The backfill does not make any previously private category public. Existing
published FAQ/notice/handbook behavior is retained, while future sources require
an explicit visibility decision. Authenticated chat, its broad internal DTO, its
generic vector RPC, personalization, and tenant authorization remain unchanged.
Admin response DTOs default missing historical fixture values to `restricted`;
the database remains authoritative and non-null after migration.

## 20. Known limitations

- The migration was validated by code review and automated predicate tests; it
  was not applied to a live remote Supabase project in this workspace.
- Public conversations still use the earlier shared persistence/session design
  internally, although the new HTTP contract exposes no session capability.
  Phase 7.1 already defers stateless/anonymous-history redesign.
- The source title and section are safe metadata but no public URL is yet modeled.

## 21. Deferred Phase 7 requirements

Public frontend/routing, anonymous history redesign, rate/concurrency/cost limits,
CAPTCHA, external abuse prevention, and deployment remain deferred. None is used
as a substitute for retrieval authorization.

## 22. Acceptance criteria

- [x] Explicit public visibility exists and fails closed.
- [x] Public knowledge is tenant-scoped.
- [x] Publication, lifecycle, dates, version, processing, and chunk provenance
  are enforced before generation.
- [x] Explicit source IDs cannot bypass policy.
- [x] Cross-tenant, private, unpublished, archived, invalid-version, and
  failed/incomplete-run data are denied.
- [x] Public request and response contracts are narrow and strict.
- [x] Authenticated retrieval behavior is preserved.
- [x] HTTP security integration and complete automated backend regressions pass.
- [x] Migration, backward compatibility, database grants, and limitations are
  documented.
- [x] No unrelated runtime functionality was changed.

**PHASE 7.2 STATUS: COMPLETE**
