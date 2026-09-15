# PHASE 4.4 — AMENDED LOCK (CONVERSATIONAL-CONTEXT COMPATIBILITY)

## STATUS: LOCKED (AMENDED)

Amendment date: 2026-09-08
This record documents a controlled, narrowly scoped reopening of the
Phase 4.4 lock. It supplements — and does not replace or erase —
[PHASE_4_4_LOCK.md](PHASE_4_4_LOCK.md), which remains the historical record
of the original RAG-only prompt contract validated and locked at that time.

---

## Reopen authorization

Phase 4.4 was explicitly reopened by the project owner for a single,
narrowly scoped purpose: resolve a Phase 5.7b physical-validation failure
caused by the original Phase 4.4 prompt contract not recognizing
conversation history as a distinct context class. This was not a general
Phase 4.4 redesign; no unrelated implementation, architecture, or scope
changes were authorized or made.

## Why the reopen was required

The original Phase 4.4 lock validated a prompt contract designed solely
around retrieval-augmented generation (RAG): `SYSTEM_INSTRUCTIONS` and
`GROUNDING_INSTRUCTIONS` in `backend/app/services/context.py` treated
retrieved knowledge as the only recognized context source and instructed
the model to declare insufficiency whenever retrieved knowledge was absent.

Phase 5.7b introduced a second context class — persisted conversation
history — supplied alongside retrieved knowledge on every generation
request. The original prompt contract gave the model no license to use
that second context class, so conversational/meta questions (e.g. "what
was my previous question?") were incorrectly forced through the
RAG-insufficiency path even though conversation history was present and
correctly delivered to the provider.

## Amendment scope

Only the prompt/instruction contract was amended. No retrieval, provider
transport, persistence, or ownership logic was touched.

### Amended prompt behavior

- Retrieved college knowledge remains the sole authoritative source for
  factual institutional/college claims — unchanged from the original lock.
- Conversation history, when supplied, may be used for conversational
  intent, coreference resolution (e.g. "that", "the previous one", "the
  fee we discussed"), and for answering questions about the conversation
  itself (e.g. identifying a previous user question or assistant
  response).
- Conversation history is explicitly not institutional knowledge and must
  never substitute for retrieved knowledge when answering a factual
  college claim. A previous assistant statement is never automatically
  treated as verified institutional knowledge.
- Mixed questions may use conversation history to resolve conversational
  meaning while relying on retrieved knowledge for the factual answer.
- Insufficient-context behavior remains mandatory and conservative for any
  factual college question unsupported by retrieved knowledge, regardless
  of what conversation history contains.
- Citation/source-reference requirements are unchanged: any source
  reference must still correspond to retrieved knowledge.

### Files amended

- `backend/app/services/context.py` — `SYSTEM_INSTRUCTIONS`,
  `GROUNDING_INSTRUCTIONS`, and `EMPTY_RETRIEVAL_NOTICE` amended to add the
  conversational-history carve-out described above. No other logic in this
  file was changed beyond the pre-existing (unlocked, Phase 5.7b)
  `conversation_history` plumbing already present in `assemble_context`.
- `backend/tests/test_context.py` — added
  `test_system_instructions_permit_conversational_history_use`,
  `test_grounding_instructions_exempt_conversational_meta_questions`, and
  one additional assertion in `test_empty_retrieval_produces_insufficient_context`.
  No existing assertion was weakened or removed.

### Explicitly NOT changed by this amendment

- `ChatRequest`
- `ChatResponse`
- `StructuredSource`
- `ChatUsage`
- Retrieval implementation
- Vector search implementation
- Persistence implementation
- Conversation ownership implementation
- `backend/app/services/generation_provider.py`
- `backend/app/services/chat.py`
- Frontend
- Database/schema

---

## Validation locked (amendment)

- Focused amendment tests
  (`test_context.py`, `test_generation_provider.py`, `test_generation_api.py`,
  `test_conversation_history.py`, `test_structured_chat_response.py`):
  **68 passed, 0 failed**
- Full backend regression (`pytest backend/tests`):
  **377 passed, 5 failed (pre-existing/unrelated), 3 skipped**
- No new failures introduced by the amendment.

### Remaining unrelated failures (OUT OF SCOPE, PRE-EXISTING, NOT FIXED)

These failures existed before this amendment, are unrelated to the prompt
contract or conversational-context change, and were explicitly excluded
from this amendment's scope per project instruction:

1. `backend/tests/test_auth.py::test_invalid_token` — invalid JWT currently
   returns 500 instead of 401.
2. `backend/tests/test_ingestion.py::test_r2_put_object_is_called` — R2
   bucket-name fixture/config mismatch (`documents` vs `college-ai-knowledge`).
3. `backend/tests/test_ingestion.py::test_document_version_fields` — same
   R2 bucket-name mismatch.
4. `backend/tests/test_ingestion.py::test_db_failure_after_r2_upload_triggers_r2_cleanup` —
   same R2 bucket-name mismatch.
5. `backend/tests/test_vector_search_service.py::test_service_maps_repository_validation_error` —
   error-code mismatch (`VECTOR_SEARCH_FAILED` vs `INVALID_VECTOR_SEARCH_REQUEST`).

## Physical validation (real backend, real frontend, real LLM provider)

- **C1 — conversation memory**: PASS. "What was my previous question?"
  correctly identified the actual prior user question; did not produce the
  previously observed insufficiency refusal.
- **C2 — coreference**: PASS. "Is that the same fee we discussed?"
  correctly resolved "that fee" via conversation history while remaining
  conservative about confirming unverified factual equivalence.
- **C3 — factual grounding preservation**: PASS. An unrelated factual
  question with no supporting retrieved knowledge correctly returned the
  existing conservative insufficient-context response; conversation
  history was not substituted as institutional evidence.
- **C4 — mixed history + RAG**: PASS. Follow-up questions requiring both
  coreference resolution (history) and factual support (retrieval)
  correctly resolved the conversational reference via history while
  remaining grounded/conservative for the factual portion.
- **C5 — existing conversation continuation**: PASS. Persisted messages
  returned in correct chronological `message_sequence` order; conversation
  continued correctly under the same `conversation_id`/`session_id`
  semantics across multiple turns.

## RAG preservation: PASS

All grounded answers observed during validation cited real, retrieved
chunk identifiers; no fabricated citations or facts were observed.

## Insufficient-context preservation: PASS

Conservative insufficiency behavior remains fully intact for factual
college claims unsupported by retrieved knowledge; conversation history
was never used as a substitute for institutional evidence in any
validation case.

## Security / ownership: PASS

Requesting a nonexistent/foreign `conversation_id` returned
`404 CONVERSATION_NOT_FOUND` without confirming existence of another
user's conversation. Ownership enforcement (Phase 5.6) was not modified
and remains intact.

## Locked-phase impact

- **Phase 5.5**: NONE. Chat request/response contract and session
  semantics unaffected.
- **Phase 5.6**: NONE. Conversation history retrieval and ownership
  enforcement unaffected; `test_conversation_history.py` passes unchanged.

## Historical distinction

The original [PHASE_4_4_LOCK.md](PHASE_4_4_LOCK.md) remains valid as the
historical record of the RAG-only prompt contract validated at that time.
This amendment record documents why and how that contract was extended,
under explicit authorization, to remain compatible with the
conversational-history context class introduced in Phase 5.7b. The
original lock record is preserved unmodified.

---

## Official amended lock statement

> "Phase 4.4 has been reopened under explicit, narrowly scoped
> authorization solely to extend the locked prompt contract for
> compatibility with Phase 5.7b conversation history. The amendment
> preserves the original RAG grounding and insufficient-context guarantees
> in full, changes no other Phase 4.4 contract element, and is now
> re-locked as amended. No further Phase 4.4 implementation or prompt
> changes are authorized without a separate, explicit reopening of the
> project's change-control process."

No commit was performed as part of this amendment or its lock finalization.
