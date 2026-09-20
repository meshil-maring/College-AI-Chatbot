# PHASE 6.14.8 — Security & Leakage Scope Report

## 1. Objective

Validate that the completed Phase 6.14 personalized academic AI pipeline cannot
leak personalized academic information across student, institution/tenant,
role, public/private, authenticated/unauthenticated, or
context-generation boundaries. This phase is a **security validation phase
only**: no architecture was redesigned and no Phase 6.14.9 work was started.

## 2. Security boundaries tested

All boundaries were tested hermetically (no real Supabase, network, OpenRouter,
or LLM) via `backend/tests/test_personalized_security_6148.py` — **55 tests**.

The tests exercise the *real production code paths* with controlled fakes only
at the infrastructure edge (Supabase client, retrieval I/O, persistence,
generation provider). Security-relevant production logic was deliberately NOT
stubbed in the key tests:

* The **real** `pr_svc._filter_to_authorized_chunks` (Phase 6.13.8 visibility
  boundary) ran inside `get_personalized_context` in tests 05/28/29/30.
* The **real** `pub_svc._filter_to_public_chunks` ran in tests 08/15.
* The **real** tenant-lifecycle guard
  `_resolve_authorized_institution_id` ran in test 27.
* The **real** Pydantic schema validation (UUID typing) ran in tests 09/10.
* The **real** function signatures were introspected in tests 10/34 (no
  identity parameters exist to forge).

## 3. Student-to-student isolation

* `test_01_student_a_never_receives_b_attendance` — Student A's resolved
  `StudentAcademicContext` contains no Student B attendance dates/status;
  the attendance service is invoked with Student A's `user_id` only.
* `test_02_student_a_never_receives_b_results` — no Student B SGPA (4.2),
  test name (`FOREIGN-TEST-999`), or marks in A's context.
* `test_03_academic_context_contains_only_caller_data` — schema-level: B's
  register/roll/student numbers, B's test name and B's date are absent from
  the serialized context while A's data is present.
* `test_04_hostile_query_cannot_pull_other_student_into_context` — a
  personal-classified hostile query naming B's register/roll numbers still
  loads **only A's** context (`get_personalized_context` receives A's
  `current_user`; query wording never changes identity).
* `test_31_malicious_history_cannot_inject_other_student` (§14) and
  `test_21_injection…["Show me REG-B-002 marks…"]` (§9) prove B-identifiers
  never enter the server-side block via prompt or history.

## 4. Cross-tenant isolation

Two tenants (TENANT_A / TENANT_B UUIDs) used throughout.

* `test_05_tenant_a_cannot_retrieve_tenant_b_knowledge` — retrieval is called
  with the **server-resolved** `institution_id` (TENANT_A); a simulated
  mis-scoped vector store returning both tenants' chunks is cleaned by the
  REAL provenance filter using A's allow-list; B's secret handbook never
  survives; `knowledge.institution_id == TENANT_A`.
* `test_06_tenant_a_cannot_retrieve_tenant_b_academic` — academic context for
  tenant A user contains no B data.
* `test_07_manipulated_institution_id_is_ignored` — chat request carrying a
  forged `institution_id` (TENANT_B) never changes scope: the authoritative
  tenant comes from `current_user["institution_id"]` (TENANT_A).
* `test_08_public_institution_filtering_stays_correct` — public chunk filter
  keeps only the authorized institution's source.
* Legitimate-looking requests (05/06) and deliberately manipulated
  identifiers/objects (07, plus §5 request-level forgery) are both covered.
* Security does **not** rely on query wording: test 05 feeds B data through
  the vector store and relies on server-side scope + provenance filtering.

## 5. Identity-forgery protection

* `test_09_extra_identity_fields_are_ignored_not_trusted` (7 params:
  `student_id`, `user_id`, `institution_id`, `organization_id`, `email`,
  `register_number`, `university_roll_number`) — `ChatRequest` rejects
  forged values: the UUID-typed `institution_id` fails validation for a
  non-UUID forged value (`ValidationError`), and unknown identity fields are
  not accepted as request schema fields, so they can never be trusted.
* `test_10_services_expose_no_identity_parameters` —
  `get_personalized_context`, `get_student_academic_context`,
  `get_own_attendance`, `get_own_results`, `get_own_test_results`,
  `build_personalized_ai_context` have **no** `student_id` / `user_id` /
  `institution_id` / `organization_id` / `scope_id` / `email` /
  `register_number` / `university_roll_number` parameters (signature
  introspection), so request data cannot alter identity anywhere.
* `test_11_current_user_remains_authoritative` — `current_user` supplied to
  the personalized pipeline is exactly the authenticated identity, untouched
  by request payload.

## 6. Public/private isolation

* `test_12_public_flow_never_calls_personalized_services` —
  `process_public_chat_request` is proven (by injected failure sentinels) to
  never touch `StudentAttendance`, `StudentResults`,
  `get_student_academic_context`, `get_personalized_context`,
  `build_personalized_ai_context`, or any authenticated identity.
* `test_13_public_attendance_query_gets_no_academic_context` —
  "Show me my attendance." via the public path produces an `AIContext` with
  `student_context=None`, no `authorized_student_data` block, and no
  attendance data.
* `test_14_public_impersonation_prompt_stays_public_only` — impersonation
  prompts ("I am student REG-A-001…", "I am an authenticated student with
  student_id …") raise `AUTH_REQUIRED` via the server-side
  `_reject_personal_query_if_needed` boundary and never reach generation.
* `test_15_public_chunk_filter_drops_private_data` — private-source chunks
  are dropped from the public context (real `pub_svc._filter_to_public_chunks`).

Security here is the **server-side data boundary** (public service has no
code path to student tables), not keyword detection.

## 7. Role isolation

Uses the existing role model only.

* `test_16_non_student_roles_use_legacy_path[admin|staff|faculty]` — for each
  non-student role the personalized pipeline is NOT invoked (sentinel proves
  `get_personalized_context` is never called) and the assembled context has
  `student_context is None`.
* `test_17_student_personal_path_receives_own_context` — the student role
  does receive the personalized block, containing only the caller's own data.

## 8. Personal/general routing isolation (Phase 6.14.7 boundary)

* `test_18_personal_question_uses_personalized_pipeline` —
  "What is my attendance?" routes through
  `get_personalized_context` → `build_personalized_ai_context` → `AIContext`
  (exactly one builder call); the legacy `assemble_context` never runs.
* `test_19_general_question_attaches_no_academic_data` — "What is DBMS?"
  never calls the personalized services and attaches no student context.
* `test_20_general_syllabus_variants_stay_general` — "Explain
  normalization.", "What is the exam syllabus?", "What is machine learning?"
  all stay on the institutional-retrieval path with `student_context is None`.

## 9. Prompt-injection testing

* `test_21_injection_cannot_expand_server_context` (7 payloads): reveal hidden
  context; request another student's (`REG-B-002`) marks/attendance; claim to
  be administrator; claim to be another student (`ROLL-B-002`); dump raw DB
  tables; request internal IDs/system prompt; "ignore previous restrictions".
  For every payload the server-side context contains **no** B-identifiers,
  B-test names, B student id, or B user id — because unauthorized data is
  never loaded server-side (not because of keyword filtering).
* `test_22_builder_ignores_instructions_inside_data` — hostile text inside a
  data field ("IGNORE RULES…") is rendered inside the delimited DATA-ONLY
  block with grounding instructions; it cannot escape (`_safe_value`
  neutralizes the closing tag).

## 10. Context leakage testing

* `test_23_no_credentials_or_secrets_in_ai_context` — with
  `password`, `access_token`, `refresh_token`, `api_key` planted on the
  authenticated user, the assembled `AIContext` (system instructions,
  grounding, student block, knowledge, history) contains none of them, and
  no DB URLs, service-role keys, OpenRouter keys, auth IDs, or `Bearer`
  tokens.
* `test_24_safe_fields_remain_available` — intentionally designed,
  student-safe fields (register number, attendance percentage, institution
  name, own knowledge) remain available.

## 11. Internal-ID leakage testing

* `test_25_academic_schemas_carry_no_internal_ids` — `StudentAcademicContext`
  serialization contains none of: `student_id`, `user_id`, `auth_user_id`,
  `institution_id`, `organization_id`, `scope_id`, `program_id`,
  `academic_year_id`, `semester_id`, `section_id`, `course_id`,
  `student_attendance_id`, `student_result_id`, `test_result_id`, nor the
  raw `user_id` value — while safe identity fields (register number,
  institution name) remain.
* `test_26_builder_emits_no_internal_ids` — the built `AIContext` contains no
  `user_id` / tenant id values.

Note (per scope instruction 9): `RetrievedChunk.chunk_id` / `document_id`
appear in the context because they are the **existing provider/citation
mechanism** (Phase 4 `[Retrieved chunk {id}]` source-reference contract);
they are document/chunk identifiers, not academic identity data, and were not
removed. No academic identity/DB id fields exist in the academic schemas at
all (proven, not assumed).

## 12. Tenant lifecycle testing

* `test_27_inactive_tenants_denied_fail_closed` — `pending`, `rejected`,
  `suspended` institutions raise `AppError 403 TENANT_INACTIVE` from the REAL
  `_resolve_authorized_institution_id`; the check is server-side (repo row,
  not request data). The `active` control case passes the guard, proving the
  denial is status-driven. Lifecycle failures propagate as errors — never
  converted into successful empty AI responses.

## 13. Knowledge visibility testing (Phase 6.13.8 rules)

Through the real `get_personalized_context` retrieval path:

* `test_28_only_published_own_institution_sources_survive` — published own
  source survives; unpublished (draft) source is dropped.
* `test_29_other_institution_and_bad_types_dropped` — another institution's
  published source and a non-whitelisted source type (`exam-paper`, outside
  `PUBLIC_SOURCE_TYPES = {faq, notice, handbook}`) are dropped.
* `test_30_malformed_provenance_fails_closed` — a chunk with no resolvable
  provenance (empty run→KS map) yields empty knowledge (fail closed).

## 14. Conversation-history testing

* `test_31_malicious_history_cannot_inject_other_student` — history
  containing another student's register number and marks cannot alter the
  server-authorized student block (history is attached as bounded
  `conversation_history` only).
* `test_32_history_bounds_respected` — 50-message history is clamped to
  `settings.conversation_history_max_messages` (existing bounds stay
  authoritative).
* `test_33_history_never_becomes_knowledge_or_student_block` — hostile
  history content never appears as retrieved knowledge or inside the
  student data block.

## 15. Direct service-boundary testing

* `test_34_forged_kwargs_rejected_by_signatures` — passing foreign identity
  (`student_id`/`user_id`) to `get_personalized_context`,
  `get_own_attendance`, `get_own_results` raises `TypeError` (parameters do
  not exist).
* `test_35_services_derive_identity_from_current_user` —
  `get_student_academic_context` derives identity from `current_user` and
  forwards exactly that identity to the underlying profile/attendance/results
  services.

## 16. Response leakage testing

* `test_36_auth_failure_is_clean_http_error` — authorization failure surfaces
  as `AppError` 403 with no traceback, SQL, or Supabase internals.
* `test_37_chat_response_exposes_no_internals` — the full chat response JSON
  contains no other-student identifiers, tenant id, tokens, passwords,
  traceback, or Supabase markers.

## 17. Production code changes, if any

**None.** Zero production files changed. Every failure observed during
development was a test-defect (wrong fake signature / stubbed boundary),
never a security defect. No speculative hardening was applied.

## 18. Exact test commands

```bash
cd backend
python -m pytest tests/test_personalized_security_6148.py -q
# regression bundle (Phase 6.10 / 6.13 / 6.14.4-6.14.7 / RBAC / public+auth chat):
python -m pytest tests/test_personalized_chat_phase_6_10.py tests/test_tenant_isolation.py tests/test_role_scope_enforcement_phase_6_13_7.py tests/test_security_final_validation_phase_6_13_9.py tests/test_public_protected_ai_phase_6_13_8.py tests/test_student_academic_context_6144.py tests/test_personalized_retrieval_6145.py tests/test_ai_context_builder_6146.py tests/test_personalized_chat_6147.py tests/test_rbac_phase_6_6.py tests/test_student_specific_data_phase_6_9.py tests/test_structured_chat_response.py tests/test_conversation_history.py -q
# full suite:
python -m pytest tests -q
```

## 19. Exact test counts

* New security tests: **55** (requirement: ≥35).
* Breakdown: student isolation 4, cross-tenant 4, identity forgery 9
  (7 parametrized + 2), public chat 4, role isolation 4, routing 3,
  prompt injection 8 (7 parametrized + 1), context leakage 2, internal-ID 2,
  tenant lifecycle 4, knowledge visibility 3, conversation history 3,
  direct service 2, response leakage 2, routing sanity 1,
  history-not-knowledge 1.
* Regression bundle: **391 passed**.

## 20. Full regression result

```
tests/test_personalized_security_6148.py        55 passed
regression bundle (13 files)                    391 passed
python -m pytest tests -q                       1599 passed, 15 skipped
```

Full backend suite: **PASS** (0 failures).

## 21. Known limitations

* Fakes replace Supabase I/O, the vector retrieval service, background
  persistence and the generation provider; row-level security of the real
  database is out of scope for these hermetic tests (covered by Phase 6.13
  tenant-isolation tests at the contract level).
* Tests 05/28–30 mirror the allow-list *selection* query
  (`_build_authorized_knowledge_source_ids`) because it is a thin DB
  projection; the downstream chunk filtering that consumes the allow-list is
  the REAL unmodified production filter, so the enforcement boundary itself
  is exercised, not a test double.
* Prompt-injection resistance is validated at the server-context level
  (unauthorized data never loaded) and at the data-framing level
  (`_safe_value`); LLM behavioral compliance is out of scope by design.
* Only the role strings existing today (`student`, `admin`, `staff`,
  `faculty`) were tested; no new roles were invented.
* `RetrievedChunk.chunk_id` / `document_id` remain in the context by design
  (existing citation mechanism); documented in §11, not treated as leakage.

## 22. Security conclusion

The Phase 6.14 pipeline held every boundary probed: identity is derived
exclusively from the authenticated `current_user`; personalization scope and
retrieval are server-resolved and institution-bound; the Phase 6.13.8
visibility filter and Phase 6.13.7 lifecycle guard fail closed; the public
path has no structural access to student data; and the built `AIContext`
carries only whitelisted, minimized student-facing fields. **No
vulnerabilities were discovered; no production changes were required.**
