# Phase 7.7 — Public Conversation Experience & Local History Hardening

Status: **COMPLETE**  
Phase type: frontend conversation lifecycle, local persistence hardening, tests, and documentation  
Date: 2026-09-28

## 1. Objective

Make the existing public chat reliable across multiple turns, refreshes, browser
restarts, institution route changes, request failures, and accidental duplicate
submissions while preserving the locked architecture:

```text
stateful in the browser + stateless on the server
```

No anonymous server account, token, conversation table, message persistence, shared
public user, or backend contract change was introduced.

## 2. Existing Phase 7.6 architecture

The implementation investigation covered the route selection in `App.tsx`, the
public page and message/source rendering, `usePublicChat`, the version-1 storage
envelope, the anonymous API client, request/response presentation types, and the
focused routing, API, storage, interaction, and security tests. All Phase 7.1–7.6
status documents were reviewed before modification.

The public route remains `/public-chat/{institution_code}` and is still selected
before `AuthProvider`. The dedicated client still sends only `institution_code` and
`message` to `POST /api/v1/chat/public`, without authorization or conversation data.

## 3. Conversation model

The browser model is now explicit:

```text
PublicConversation
  id                 local display/lifecycle ID only
  institutionCode    normalized public code
  messages[]         bounded chronological user/assistant messages
  createdAt
  updatedAt
```

Conversation and message IDs are local, non-sensitive, and never included in the
HTTP request. One current conversation is retained per institution. Starting a new
conversation replaces only that institution's current local conversation; previous
conversations are not archived because multi-conversation history is outside the
current product model.

## 4. Local persistence

Persistence uses local storage so history survives refresh, unmount/remount,
back/forward navigation, and browser restart when the browser retains site data.
The current namespace and envelope are:

```text
college-ai-chatbot.public-chat.v2:{NORMALIZED_INSTITUTION_CODE}
{ version: 2, conversation: PublicConversation }
```

Valid Phase 7.6 version-1 records are migrated once to version 2. Invalid JSON,
wrong versions, missing fields, unexpected fields, invalid ordering, wrong-tenant
records, excessive field sizes, excessive message counts, and oversized serialized
records are removed and replaced with a clean in-memory conversation. Raw parse
errors are never shown.

Empty conversations are not persisted. Storage denial and quota errors remain
best-effort failures and do not break the in-memory chat.

## 5. Institution isolation

Codes are trimmed and uppercased before key construction, matching the existing
case-insensitive public route behavior. Each institution has a distinct key and the
stored `institutionCode` must exactly match the requested normalized code. The hook
now detects an institution prop change, aborts the old request, clears transient
error/loading state, and hydrates the new institution before persistence is allowed.
This closes the Phase 7.6 race that could write Institution A state to Institution B.

Tests cover simultaneous A/B histories and route changes in both directions.

## 6. New conversation

`New conversation` is always reachable from the header when no request is pending.
It creates a fresh local conversation ID, removes only the active institution's
stored conversation, resets draft/error/retry state, and returns focus to the input.
No backend request is made.

## 7. Clear conversation

`Clear conversation` is shown when messages exist. It opens an `aria-modal` dialog
with an explicit description that other colleges are unaffected. Cancel receives
initial focus, focus is trapped between dialog actions, Escape cancels and restores
focus to the trigger, and confirmation removes only the current institution's local
record before focusing the input.

## 8. Refresh recovery

Every completed state update writes the validated conversation envelope. Hydration
preserves chronological message order, response status, and only the safe public
source projection (`title`, `section`, `quote`). Remount/refresh coverage verifies
that both user and assistant messages return without authentication.

## 9. Browser lifecycle

The application now listens for `popstate`, allowing the minimal route selector to
respond to browser back/forward navigation without adding a router dependency.
Direct loads continue to work. Local storage provides browser-restart persistence
subject to normal browser/site-data clearing behavior.

On unmount or institution change, the hook aborts its active request and ignores any
late result. It never updates an unmounted or wrong-institution conversation.

## 10. Multi-tab behavior

No complex storage-event synchronization was introduced. Separate-institution tabs
operate on separate keys. Same-institution tabs use validated atomic local-storage
writes with documented last-writer-wins behavior; a tab write cannot create a shape
that another tab accepts as a malformed or cross-institution conversation. New
messages are not live-merged between tabs.

## 11. Retry behavior

A failed request retains its one user message and records that message's local ID.
Retry reuses the same message without appending another user bubble. New submissions
are blocked until the failed turn is retried or the conversation is reset, preserving
strict user/assistant ordering. If refresh or browser shutdown interrupts a pending
turn, hydration recognizes the unmatched final user message and restores it as the
single retry target. No automatic or background retry exists.

## 12. Interrupted requests

The API client now accepts an optional caller signal while retaining its independent
35-second timeout. Caller cancellation is distinguished from timeout and is not
rendered as an error during navigation/unmount. The hook owns one `AbortController`,
aborts on route changes and unmount, and guards all late state updates by institution.

## 13. Storage limits

The limits are:

- 40 messages, retained as the newest complete chronological turns;
- 4,000 characters per user message;
- 12,000 characters per assistant message and safe source field;
- 10 sources per assistant message;
- 128 characters per local ID;
- 256,000 characters for the complete serialized envelope.

The Phase 7.6 per-field limits were retained for backend compatibility. The total
envelope cap is new. If the cap is exceeded, the oldest complete turns are removed
first, so the newest turns are retained and ordering is never split.

## 14. Security and privacy

Only local IDs, roles, text, timestamps, public response status, and `title`,
`section`, and `quote` sources are serialized. Tokens, provider/model metadata,
diagnostics, internal UUID fields, processing IDs, storage paths, and internal URLs
are absent. The UI now discloses that history is stored in the browser for the named
institution.

Stored and live content remains React text. Tests cover literal `<script>`, `<img
onerror>`, and `javascript:` payloads; no HTML, script, image, or unsafe link is
created. The backend remains the public-knowledge and tenant authorization boundary.

## 15. Accessibility

Existing labelled input, semantic buttons, live log, status, alert, keyboard send,
Shift+Enter, IME protection, and focus rings remain. Lifecycle actions are native
buttons. The clear dialog has a name, description, modal semantics, initial focus,
Tab/Shift+Tab trapping, Escape handling, and focus restoration. The input regains
focus after response completion, new conversation, or confirmed clear.

## 16. Responsive behavior

The existing dynamic viewport, scrollable transcript, sticky safe-area composer,
adaptive message widths, and break-safe sources remain. Header actions now wrap and
stack on narrow screens so New, Clear, and Sign in stay reachable without hiding the
input or overflowing the viewport. No fake streaming behavior was added.

## 17. Tests

Focused coverage includes conversation creation, multiple turns, strict ordering,
duplicate prevention, retry without duplication, new and clear actions, dialog
keyboard/focus behavior, refresh/remount, Phase 7.6 migration, malformed and old
storage, unexpected fields, total/message bounds, same- and multi-institution tab-like
writes, route changes, popstate restoration, cancellation, safe sources, API request
projection, and inert XSS payloads.

There is no browser/E2E framework in the frontend package, so no large framework was
introduced solely for this phase. The realistic route/request/remount/institution
switch flow is covered with the existing Vitest + Testing Library architecture.

Verification results:

```text
Focused Phase 7.7 frontend:
  npm.cmd run test -- --pool=threads --maxWorkers=1 --isolate=false \
    src/services/publicChat.test.ts \
    src/features/publicChat/publicChatStorage.test.ts \
    src/features/publicChat/PublicChatPage.test.tsx
  3 files passed, 25 tests passed

Complete frontend (normal isolation, single Windows worker):
  npm.cmd run test -- --pool=threads --maxWorkers=1
  50 files passed, 427 tests passed

TypeScript:
  npx.cmd tsc --noEmit -p tsconfig.json
  PASS

Production build:
  npm.cmd run build
  PASS — 97 modules transformed, built in 5.51s

Focused backend public-chat regression:
  DEBUG=false uv run pytest -q \
    tests/test_narrow_public_chat_api_phase_7_3.py \
    tests/test_public_rag_integration_phase_7_4.py \
    tests/test_public_ai_generation_phase_7_5.py
  65 passed, 1 deprecation warning
```

An initial complete frontend attempt with `--isolate=false` was stopped after it
caused broad cross-file test-state leakage in unrelated auth/student suites. That
optimization is valid for the three self-contained focused files but not for the
complete repository. The authoritative complete result above uses normal isolation.

## 18. Files changed

Modified:

- `frontend/src/App.tsx`
- `frontend/src/types/publicChat.ts`
- `frontend/src/services/publicChat.ts`
- `frontend/src/services/publicChat.test.ts`
- `frontend/src/features/publicChat/usePublicChat.ts`
- `frontend/src/features/publicChat/publicChatStorage.ts`
- `frontend/src/features/publicChat/publicChatStorage.test.ts`
- `frontend/src/features/publicChat/PublicChatPage.tsx`
- `frontend/src/features/publicChat/PublicChatPage.test.tsx`

Created:

- `docs/status/PHASE_7_7_PUBLIC_CONVERSATION_EXPERIENCE.md`

No backend source, schema, migration, or test file was modified.

## 19. Deferred work

- rate limiting and IP throttling;
- concurrency controls;
- AI cost controls and quotas;
- CAPTCHA and external abuse prevention;
- server-side anonymous history or accounts;
- multi-conversation archives and cross-tab live merge;
- production deployment and host rewrite validation.

## 20. Acceptance criteria

- [x] Multi-turn browser conversation works with deterministic ordering.
- [x] Refresh and browser-restart persistence use bounded local storage.
- [x] Corrupted, old, oversized, and wrong-institution storage fails safely.
- [x] Institution A/B history cannot mix, including route changes.
- [x] New conversation and confirmed clear affect only the active institution.
- [x] Duplicate submission and failed-turn duplication are prevented.
- [x] Retry reuses the existing user turn.
- [x] Interrupted requests are aborted and late state updates are ignored.
- [x] XSS payloads remain inert text.
- [x] Persisted sources contain only the safe public projection.
- [x] Direct load and back/forward popstate behavior work.
- [x] Lifecycle actions and focus behavior are keyboard/screen-reader accessible.
- [x] Responsive controls, transcript, sources, and sticky input are retained.
- [x] No server-side anonymous history or authentication dependency was introduced.
- [x] The existing public API contract remains unchanged.
- [x] Focused, complete frontend, type, build, and backend regressions pass.
- [x] No rate, concurrency, cost, CAPTCHA, analytics, or deployment system was added.

**PHASE 7.7 STATUS: COMPLETE**
