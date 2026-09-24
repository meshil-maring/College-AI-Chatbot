# Phase 6.14.7 — Personalized Chat Scope Report

## 1. Objective
Connect the completed Phase 6.14 personalized pipeline to the authenticated
student chat flow without redesigning generation: `current_user` →
`get_personalized_context()` (6.14.5) → `build_personalized_ai_context()`
(6.14.6) → existing `AIGenerationService`/`GenerationProvider` → existing
`ChatResponse`. Identity is JWT-only; public chat stays free of
student-private data.


## 2. Existing architecture inspected
- `backend/app/api/chat.py` (authenticated route → `process_chat_request`)
- `backend/app/api/public_chat.py` (public route → separate service)
- `backend/app/services/chat.py` (history, rewrite, retrieval,
  `assemble_context`, `AIGenerationService`, persistence)
- `backend/app/services/public_chat.py` (PUBLIC_USER_ID ownership,
  `_validate_public_institution`, `_filter_to_public_chunks`,
  `_reject_personal_query_if_needed`, `assemble_context` + generation)
- `backend/app/services/personalized_retrieval.py`
  (`get_personalized_context`, authorized-source filtering)
- `backend/app/services/ai_context_builder.py`
  (`build_personalized_ai_context`, academic block rendering)
- `backend/app/services/student_academic_context.py`,
  `student_attendance.py`, `student_results.py`
- `backend/app/services/generation.py` (`AIGenerationService.generate`,
  empty-context `insufficient_context` exit, ungrounded-ref guard)
- `backend/app/services/personalization.py`
  (`classify_personalization_question`, legacy 6.10 path)
- `AIContext`, provider contract, `PHASE_6_14_6_SCOPE_REPORT.md`, existing
  auth/public/retrieval/generation/tenant tests. All reused, none rewritten.

## 3. Files changed
- `backend/app/services/chat.py`: `_is_student()` + `_uses_personalized_pipeline()`
  gates; Step 1.6 runs 6.14.5→6.14.6, skips the redundant Phase-3 retrieval on
  that path (chunks re-exported), attaches bounded stored history, renders the
  student block into the USER message via the existing 6.10 placement; every
  other caller keeps the legacy path verbatim.
- `backend/tests/test_personalized_chat_6147.py`: NEW (38 hermetic tests).
- `backend/tests/test_personalized_chat_phase_6_10.py`: aligned expectations
  with the 6.14.7 student-personal branch (general/non-student unchanged).
- `PHASE_6_14_7_SCOPE_REPORT.md`: NEW (this file).
No API/schema/provider/model changes.

## 4. Personalized chat flow
Student + personal intent → resolve conversation/history (unchanged) → rewrite
query for retrieval only → `get_personalized_context(current_user, query)`
(tenant/academic authorization inside 6.14.5/6.14.4 from JWT) →
`build_personalized_ai_context(personalized_context, current_user)` →
attach bounded `conversation_history` → unchanged `AIGenerationService` +
provider → unchanged source extraction, persistence, `ChatResponse`.
General student questions and non-student callers use legacy `assemble_context`.

## 5. Student identity/security model
Identity is JWT-only: `current_user` is the sole source; `ChatRequest` has no
identity fields and query text is content-only (hostile claims select
nothing). Tenant isolation: server-resolved institution; knowledge filtered
to published own-institution sources; academic reads re-resolve the student
from `user_id`. Only the authenticated student's records render. Errors reuse
`AppError`; auth failures stay failures; no internals leak.

## 6. Public vs personalized isolation
`POST /api/v1/chat/public` untouched: `public_chat.process_chat_request`
(PUBLIC_USER_ID, validated-institution scope, public-only filter,
personal-query rejection, `assemble_context`). Never calls
`get_personalized_context`/`build_personalized_ai_context`; never receives
academic context/attendance/results/identity (source + behavior tests).

## 7. Non-student behavior
Any principal without the JWT `student` role never enters the personalized
branch (explicit `_is_student` gate) and keeps the exact legacy path, so no
student-private block can reach admin/staff/faculty. Verified by tests.

## 8. Conversation-history handling
Unchanged: stored history via `get_conversation_messages` (ownership-checked),
bounded by `settings.conversation_history_max_messages` via
`_bounded_conversation_history` (most-recent preserved), into
`AIContext.conversation_history`. No request-body history exists or is
trusted; history never becomes knowledge.

## 9. Tests executed
- `pytest tests/test_personalized_chat_6147.py -q`
- `pytest tests/test_personalized_chat_6147.py
  tests/test_personalized_chat_phase_6_10.py
  tests/test_personalized_retrieval_6145.py
  tests/test_ai_context_builder_6146.py
  tests/test_student_academic_context_6144.py tests/test_attendance_6142.py
  tests/test_results_6143.py -q`
- Full suite: `pytest tests -q` (all hermetic; no Supabase/network/LLM).

## 10. Exact test counts
- Phase file: **38 passed, 0 failed, 0 skipped** (all 20 required items:
  retrieval/builder wiring, own attendance/results, other-student exclusion,
  cross-tenant filtering, inactive/pending/rejected tenants, public and
  non-student isolation, bounded history, schema/provider compat,
  identity-override rejection, regression).
- 6.14.1–6.14.6 + 6.10 regression slice: **190 passed, 0 failed**.
- Full backend suite: **1544 passed, 15 skipped, 0 failed** (`PYTEST_EXIT=0`).

## 11. Full regression result
Green: `1544 passed, 15 skipped in ~22s`. The 15 skips are pre-existing
environment-gated skips, none from this phase. Authenticated chat, public
chat, retrieval, generation, provider, tenant isolation, and authorization
suites all pass.

## 12. Known limitations
- Personalization triggers only when the locked deterministic 6.10 intent
  classifier fires; ambiguous personal questions stay general by design.
- Bounded academic rendering caps may omit older records (explicit markers).
- No summarization/digests (out of scope by design).

## 13. No migrations/schema changes
Confirmed: no migrations, no schema/DB changes, no new roles, no auth/tenant/
retrieval/generation rewrites, no model/provider change, no second pipeline,
no context-schema duplication, no academic data in public chat. `git status`
shows only `backend/app/services/chat.py` and
`backend/tests/test_personalized_chat_phase_6_10.py` modified plus the new
phase test/report files (alongside the pre-existing 6.14.1–6.14.6 untracked
phase files); no `migrations/` or schema edits.