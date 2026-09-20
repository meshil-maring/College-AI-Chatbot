# Phase 6.14.5 Scope Report — Personalized Retrieval Boundary

## 1. Files Changed

| File | Change |
| --- | --- |
| `backend/app/schemas/personalized_context.py` | **New** — `PersonalizedContext` / `InstitutionalKnowledge` contracts (`extra="forbid"`; reuses the Phase 4 `RetrievedChunk` and Phase 6.14.4 `StudentAcademicContext` models verbatim) |
| `backend/app/services/personalized_retrieval.py` | **New** — the secure retrieval boundary (`get_personalized_context(current_user, query, academic_year_id=None, semester_id=None, client=None, top_k=None)`) |
| `backend/tests/test_personalized_retrieval_6145.py` | **New** — 26 hermetic tests |
| `PHASE_6_14_5_SCOPE_REPORT.md` | **New** — this report |

No existing file was modified. `backend/app/api/students.py` appears as
modified in `git status` only because the (already-reported) Phase 6.14.4
additive endpoints were not yet committed; it was **not** touched by this
phase. The generation pipeline (`AIContext`, `assemble_context`,
`AIGenerationService`, providers, prompts, model selection, token billing,
OpenRouter configuration), `app/services/chat.py`, `public_chat.py`,
`main.py`, retrieval, vector search, attendance, results, authentication,
tenancy, and RLS code are all unchanged.

## 2. Migration Created

**None.** No schema change is required — the boundary only orchestrates the
existing Phase 3 retrieval service, the Phase 6.13.8 knowledge-visibility
repo primitives, and the Phase 6.14.1–6.14.4 services.

## 3. Personalized Retrieval Contract

`get_personalized_context(current_user, query, academic_year_id=None,
semester_id=None, client=None, top_k=None) -> PersonalizedContext`

```text
PersonalizedContext                      (extra="forbid")
├── query: str
├── knowledge: InstitutionalKnowledge    (institutional RAG chunks)
│   ├── institution_id: UUID | None      (the student's OWN tenant label)
│   └── chunks: list[RetrievedChunk]     (existing Phase 4 contract)
└── academic: StudentAcademicContext     (private student academic data)
    ├── student   (identity labels)
    ├── institution (labels)
    ├── attendance (summary + records)
    └── results    (academic + test results, published only)
```

The two sources are never flattened: `knowledge` (institutional documents)
and `academic` (private student records) remain distinct, explicitly named
fields so later prompt construction and security tests can always tell them
apart.

Identity: derived EXCLUSIVELY from `current_user`. The signature contains no
`student_id` / `user_id` / `institution_id` / `organization_id` /
`scope_id` parameter — client identity overrides are structurally impossible
(and a `TypeError` if attempted).

## 4. Institutional RAG Behavior

```text
current_user → tenant/institution resolution → institution-scoped RAG → authorized chunks
```

* Tenant resolution is server-side only: `current_user["institution_id"]`
  (resolved by `get_current_user` from `students.institution_id`). An account
  without a tenant fails closed with 403 `NO_TENANT_BOUND`.
* Lifecycle guard (Phase 6.13.7 semantics, not weakened): the institution row
  must exist with `status == "active"` and `is_active` — otherwise 403
  `TENANT_INACTIVE` (pending / rejected / suspended all fail closed).
* Retrieval REUSES the existing Phase 3 service
  (`app.services.retrieval.retrieve` → `search_chunks` with the
  `institution_id` scope). No second vector-search implementation was
  created. The budget is the existing `settings.retrieval_top_k` (4) unless
  `top_k` is explicitly passed; no new limit system.
* The query is forwarded verbatim. Authorization is INDEPENDENT of wording —
  there is no `if "my" in query` keyword security anywhere.
* Defense-in-depth visibility filter (Phase 6.13.8 boundary semantics):
  chunk provenance (`processing_run_id` → knowledge source) is resolved and
  only chunks from a PUBLISHED knowledge source of the student's own
  institution with a whitelisted source type (`PUBLIC_SOURCE_TYPES`,
  imported from `public_chat` so the two boundaries cannot drift) survive.
  Draft/private sources, other institutions' sources, and chunks without
  resolvable provenance are dropped (fail closed). Chunks from another
  tenant can never enter the context even if a vector row were mis-scoped.

## 5. Academic Context Behavior

Delegated 1:1 to `student_academic_context.get_student_academic_context`
(Phase 6.14.4): identity + institution labels (6.14.1), own attendance
(6.14.2), own published academic + test results (6.14.3). Attendance,
results, and student tables are NEVER queried directly from the new service.
A service denial (400 `INVALID_USER_CONTEXT` / 404
`STUDENT_PROFILE_NOT_FOUND` / 403 `TENANT_MISMATCH` / 422 `INVALID_FILTER`)
propagates — never caught or bypassed. The existing limits are reused
(attendance 200 / test results 100; academic-year/semester filters
forwarded).

## 6. Context Separation

See §3. `model_dump()` of the context always yields exactly the top-level
keys `{query, knowledge, academic}`; the academic subtree contains no
internal database ids, and the knowledge subtree carries only chunk
provenance metadata from the existing Phase 4 contract plus the student's
own tenant label.

## 7. Tenant / Security Behavior

* JWT identity only; no identity parameter exists to override.
* Tenant-bound: retrieval scope is always the authenticated tenant;
  cross-institution requests are structurally impossible and a foreign chunk
  is dropped by the provenance filter (tested).
* Cross-student: the academic boundary (6.14.2/6.14.3 own-row filtering)
  keeps other students' attendance/results out (tested with mixed rows).
* Inactive / pending / rejected institution → 403 `TENANT_INACTIVE`, no
  retrieval performed (tested; same code as the locked 6.13.7 guard).
* Private/unpublished knowledge excluded; no secrets: no password / token /
  secret / credential / email field exists anywhere in the dumped contract.
* Empty data is NOT an authorization failure: no chunks, no attendance,
  no results, or both empty → valid context with empty collections.

## 8. Tests Run

`backend/tests/test_personalized_retrieval_6145.py` (26 tests, hermetic —
repo functions patched with `unittest.mock`, in-memory fake Supabase client,
no live Supabase/network/LLM):

1. `test_1_authenticated_student_retrieval_works`
2. `test_2_institution_rag_retrieval_works`
3. `test_3_student_academic_context_is_included`
4. `test_4_no_rag_results_returns_valid_context`
5. `test_5_no_attendance_returns_valid_context`
6. `test_6_no_results_returns_valid_context`
7. `test_7_both_empty_returns_valid_context`
8. `test_8_cross_institution_rag_retrieval_denied`
9. `test_9_cross_student_academic_data_denied`
10. `test_10_client_student_id_override_denied`
11. `test_11_client_institution_id_override_denied`
12. `test_12_client_organization_id_override_denied`
13. `test_13_unauthorized_scope_denied`
14. `test_14_inactive_institution_denied`
15. `test_15_pending_institution_denied`
16. `test_16_rejected_institution_denied`
17. `test_17_private_unauthorized_knowledge_excluded`
18. `test_18_another_students_attendance_excluded`
19. `test_19_another_students_results_excluded`
20. `test_20_raw_secrets_excluded`
21. `test_21_phase_6142_regression`
22. `test_22_phase_6143_regression`
23. `test_23_phase_6144_regression`
24. `test_24_phase_6137_scope_regression`
25. `test_25_existing_retrieval_regression`
26. `test_26_query_wording_does_not_change_authorization`

## 9. Exact Results

```text
backend$ python -m pytest tests/test_personalized_retrieval_6145.py -q
26 passed in 2.41s

backend$ python -m pytest tests/test_personalized_retrieval_6145.py \
           tests/test_student_academic_context_6144.py \
           tests/test_attendance_6142.py tests/test_results_6143.py \
           tests/test_academic_profile_6141.py tests/test_retrieval.py \
           tests/test_vector_search_service.py \
           tests/test_vector_search_repository.py \
           tests/test_role_scope_enforcement_phase_6_13_7.py -q
182 passed, 1 warning in 3.88s

backend$ python -m pytest tests -q
1486 passed, 15 skipped, 6 warnings in 21.09s
```

Full backend regression: **0 failures**. Phases 6.14.1–6.14.4, 6.13.7, and
the existing retrieval/vector-search suites all pass unchanged.

## 10. Remaining Limitations

1. **No API endpoint / no `AIContext` wiring yet** — `get_personalized_context`
   is a server-side service only. Connecting it to the generation pipeline
   (prompt construction, compression/summarization) is Phase 6.14.6's work.
2. **Records, not digests** — the context carries the bounded raw retrieval
   chunks and academic records; no compression/summarization (deferred per
   scope).
3. **Knowledge allow-list is type-based** — visibility is
   institution + published + `PUBLIC_SOURCE_TYPES`; there is no per-user
   document ACL system in the project yet, so none is enforced here.
4. **RAG failures propagate** — an embedding/vector-search failure (500
   `EMBEDDING_FAILED` / `RETRIEVAL_FAILED`) aborts the whole context; only
   *empty* retrieval results are treated as valid empty knowledge.
5. **Institution label on knowledge block** — `knowledge.institution_id` is
   the student's own tenant label carried for provenance; no other internal
   identifier is introduced.
6. **`top_k` is a call-site knob** — it reuses `settings.retrieval_top_k`
   by default; there is no global context-budget system yet.


