# PHASE 5.7b — BACKEND CONVERSATIONAL CONTEXT INTEGRATION

## STATUS: LOCKED

Lock date: 2026-09-08
Locked at final read-only lock review completion. Remaining blockers: NONE.

---

## Purpose

Introduce backend-managed conversational history into the generation
context so multi-turn conversations (conversational intent, coreference,
"what did I ask before"-style questions) are supported, while preserving
RAG grounding and the existing chat API contract unchanged.

---

## Scope locked

- Conversation history retrieval for an authenticated user's conversation
- Authenticated ownership enforcement before any history reaches the LLM
- Bounded conversation history (deterministic windowing)
- Chronological turn preservation (message_sequence ASC)
- Current-query duplication prevention
- Context-layer propagation of conversation history alongside retrieved
  knowledge
- Provider-level history serialization
- Coexistence of conversation history and retrieved institutional
  knowledge without either substituting for or corrupting the other

## Configuration

- `conversation_history_max_messages = 20` (`backend/app/config.py`) —
  the bound applied by `_bounded_conversation_history` in
  `backend/app/services/chat.py`. When the persisted message count exceeds
  this bound, the most recent messages are kept (never the oldest), and if
  the resulting window would start on an orphaned assistant turn, that
  turn is dropped so the window starts on a user turn. If the bound is
  `<= 0` or no messages exist, an empty history list is returned.

## API contract

Conversation history is **not** exposed as a new `ChatRequest` or
`ChatResponse` field. Both contracts (`backend/app/schemas/chat.py`)
remain exactly as locked under Phase 4.4/5.5:

- `ChatRequest`: `user_query`, `session_id`, `conversation_id`,
  `institution_id`, `knowledge_source_id`, `document_id`,
  `document_version_id`, `processing_run_id`, `retrieved_chunks`,
  `model_name`.
- `ChatResponse`: `session_id`, `conversation_id`, `message_id`,
  `sources`, `usage`, plus the inherited `AIResponse` fields.

History is entirely server-side managed: it is retrieved from persisted
messages using the request's resolved `conversation_id` and the
authenticated `user_id`, never accepted from or returned to the client.

## Security

- History is retrieved only after conversation ownership is validated.
  `process_chat_request` (`backend/app/services/chat.py`) verifies
  ownership when resolving the conversation (403 if a persisted
  conversation belongs to a different user), and
  `get_conversation_messages` (`backend/app/services/conversation_history.py`)
  independently re-verifies ownership before returning any messages
  (404 `CONVERSATION_NOT_FOUND` for a nonexistent or foreign conversation
  — the response does not confirm or deny that a foreign conversation
  exists).
- This defense-in-depth ordering guarantees a foreign or nonexistent
  conversation's history can never reach the generation provider.
- Physically verified: a request for a nonexistent/foreign
  `conversation_id` returned `404 CONVERSATION_NOT_FOUND` without leaking
  existence information.

## RAG boundary

Conversation history is explicitly **not** institutional authority.
Retrieved college knowledge remains the sole authoritative source for
factual institutional/college claims. Conversation history is used only
for conversational intent, coreference resolution, and answering
questions about the conversation itself. A previous assistant statement
is never automatically treated as verified institutional knowledge.

## Prompt compatibility

This behavior is governed by the separately locked
[`PHASE_4_4_AMENDMENT_LOCK.md`](PHASE_4_4_AMENDMENT_LOCK.md), which
amended `SYSTEM_INSTRUCTIONS` and `GROUNDING_INSTRUCTIONS`
(`backend/app/services/context.py`) to explicitly distinguish:

- conversation history — used for conversational intent, coreference,
  and meta-questions about the conversation itself, and
- retrieved knowledge — the sole authoritative source for factual
  institutional/college claims, with insufficient-context behavior
  remaining mandatory whenever retrieved knowledge does not support a
  factual claim.

Phase 5.7b's conversation-history plumbing was validated against this
amended prompt contract; no further Phase 4.4 changes were required.

---

## Validation locked

### Automated

- Focused tests (`test_context.py`, `test_generation_provider.py`,
  `test_generation_api.py`, `test_conversation_history.py`,
  `test_structured_chat_response.py`): **68 passed, 0 failed**
- Full backend regression (`pytest backend/tests`):
  **377 passed, 5 failed (pre-existing/unrelated), 3 skipped**
- No Phase 5.7b-specific failures.

### Physical (real backend, real frontend, real LLM provider)

- **C1 — conversation memory**: PASS. "What was my previous question?"
  correctly identified the actual prior user question.
- **C2 — coreference**: PASS. "Is that the same fee we discussed?"
  correctly resolved "that fee" via conversation history while remaining
  conservative about unverifiable factual equivalence.
- **C3 — factual grounding preservation**: PASS. An unsupported factual
  college question correctly returned the existing conservative
  insufficient-context response; history was not substituted as
  institutional evidence.
- **C4 — mixed history + RAG**: PASS. Follow-ups requiring both
  coreference resolution and factual support correctly resolved the
  conversational reference via history while remaining grounded for the
  factual portion.
- **C5 — existing conversation continuation**: PASS. Persisted messages
  returned in correct chronological order; conversation continued
  correctly under stable `conversation_id`/`session_id` semantics across
  multiple turns.

## Known unrelated failures (OUT OF SCOPE, PRE-EXISTING, NOT CAUSED BY PHASE 5.7b)

1. `backend/tests/test_auth.py::test_invalid_token` — invalid JWT
   currently returns 500 instead of 401.
2. `backend/tests/test_ingestion.py::test_r2_put_object_is_called` — R2
   bucket-name fixture/config mismatch.
3. `backend/tests/test_ingestion.py::test_document_version_fields` — same
   R2 bucket-name mismatch.
4. `backend/tests/test_ingestion.py::test_db_failure_after_r2_upload_triggers_r2_cleanup` —
   same R2 bucket-name mismatch.
5. `backend/tests/test_vector_search_service.py::test_service_maps_repository_validation_error` —
   error-code mismatch (`VECTOR_SEARCH_FAILED` vs
   `INVALID_VECTOR_SEARCH_REQUEST`).

None of these touch `chat.py`, `context.py`, `generation_provider.py`,
`conversation_history.py`, or any conversation-ownership/history code, and
none were introduced or modified by Phase 5.7b work. They were explicitly
excluded from this phase's scope and were not fixed.

## Database

No schema or migration changes.

## Frontend

No frontend changes attributable to Phase 5.7b.

## Locked phases preserved

- **Phase 4.4** (original): preserved unmodified.
- **Phase 4.4 Amendment**: preserved; its conversational-context prompt
  compatibility is what makes Phase 5.7b's physical behavior correct.
- **Phase 5.5**: unaffected — `ChatRequest`/`ChatResponse` contract,
  session semantics, and frontend behavior unchanged.
- **Phase 5.6**: unaffected — conversation history API, ownership logic,
  message ordering, and persistence behavior unchanged; reused directly
  by Phase 5.7b via `get_conversation_messages`.

## Files attributable to Phase 5.7b

- `backend/app/config.py` — added `conversation_history_max_messages`
  setting.
- `backend/app/schemas/generation.py` — added `ConversationTurn`, and
  `conversation_history` fields on `AIRequest`/`AIContext`.
- `backend/app/services/chat.py` — conversation history retrieval,
  `_bounded_conversation_history` windowing, history injection into the
  generation request, and the `settings` import correction.
- `backend/app/services/generation_provider.py` — `_build_user_content`
  serialization of conversation history alongside retrieved knowledge.
- `backend/tests/test_citation.py`, `backend/tests/test_generation_api.py`,
  `backend/tests/test_phase_4_2_persistence.py`,
  `backend/tests/test_structured_chat_response.py` — test coverage
  updated/extended for conversation-history-aware request handling.

(`backend/app/services/context.py` and `backend/tests/test_context.py`
are attributed to the separately locked Phase 4.4 Amendment, not to this
Phase 5.7b lock.)

## Git

No commit was performed as part of this lock or its finalization.

---

## Official lock statement

> "Phase 5.7b is complete and locked. Backend-managed conversation history
> is retrieved only for the authenticated owner of a conversation, is
> bounded and chronologically ordered, never duplicates the current
> query, and is propagated through context assembly and the generation
> provider without being treated as institutional authority. Retrieved
> college knowledge remains the sole authoritative source for factual
> institutional claims, per the Phase 4.4 Amendment. No further Phase 5.7b
> implementation changes are authorized without reopening the phase
> through the project's change-control process."
