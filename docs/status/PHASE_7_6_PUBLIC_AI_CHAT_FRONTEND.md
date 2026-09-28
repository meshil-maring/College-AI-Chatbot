# Phase 7.6 — Public AI Chat Frontend

Status: **COMPLETE**  
Phase type: frontend routing, public API client, chat UI, browser state, tests, and documentation  
Date: 2026-09-28

## 1. Objective

Provide an unauthenticated, institution-scoped public chat experience that calls only
the secured Phase 7.3–7.5 public API. Visitors can ask questions against published
college knowledge, receive plain-text answers and safe sources, and retain a bounded
display history in their own browser without entering an authenticated role shell.

## 2. Public route

The route is `/public-chat/{institution_code}`, for example `/public-chat/GIT`.
`App` performs the repository's minimal route selection from `window.location.pathname`;
no router dependency was introduced. The public branch is selected before
`AuthProvider` is rendered, so both direct navigation and a browser refresh resolve the
same public component when the web host serves the Vite SPA entry point. `/public-chat`
and invalid code paths remain public but render a safe incomplete-link page.

The existing `/` authenticated entry and all role shells are unchanged.

## 3. Authentication separation

The public tree is returned before `AuthProvider`, `AuthGate`, session restoration,
`/auth/me`, role detection, and development auth status are mounted. It has no access
token prop, no `useAuth` call, and no student/admin/faculty/staff navigation. Its only
authenticated-navigation element is a normal link back to the existing `/` sign-in
flow.

Tests spy on `AuthProvider` and make `useAuth` throw if called; direct public navigation
still renders successfully and the provider is never invoked.

## 4. API client

`services/publicChat.ts` owns the anonymous HTTP boundary:

```text
POST {VITE_API_BASE_URL || /api}/v1/chat/public
Content-Type: application/json

{ "institution_code": "GIT", "message": "..." }
```

No `Authorization` header, token, conversation identifier, retrieval control, model,
provider, debug field, or internal identifier can be supplied. The client supports a
35-second browser timeout, non-JSON errors, network failures, status classification,
malformed success responses, and allow-list projection of successful responses.

## 5. Request and response types

`types/publicChat.ts` mirrors the actual backend schemas:

- `PublicChatRequest`: `institution_code`, `message`;
- `PublicChatResponse`: `answer`, `status`, `sources`;
- `PublicChatSource`: nullable `title`, nullable `section`, required `quote`.

It does not model provider data, usage, diagnostics, database IDs, similarity scores,
or authenticated structured-source fields. `PublicChatMessage` is explicitly a
browser-only presentation model.

## 6. Institution resolution

The deployment/institution link supplies a public code in the route. The client
decodes, trims, uppercases, and validates a conventional 1–32 character public code;
it never accepts or exposes an institution database UUID. There is no institution
switcher. The backend remains authoritative and re-resolves the submitted code for
every independent request.

## 7. Chat UI

`PublicChatPage` provides a separated public header, empty state, supported example
questions, chronological user/assistant bubbles, a sticky mobile-safe composer,
clear-history control, sign-in link, source cards, loading state, safe error alert,
and explicit retry. The wording limits knowledge claims to published FAQs, notices,
and handbooks and distinguishes student-specific information.

The composer trims and whitespace-normalizes messages, rejects blank or over-4,000
character input, sends on Enter, preserves Shift+Enter, respects IME composition, and
prevents concurrent sends with both UI disabling and an immediate ref guard.

## 8. Local conversation state

`usePublicChat` owns the chronological local message list. Each request contains only
the current user message and institution code. Assistant results append after the
request completes. A failed request leaves its user turn in place and records that
turn's local ID; retry calls the same message without adding a second user bubble or
creating a background retry loop.

Local IDs are React/browser display keys only and are never sent to the backend.

## 9. Storage strategy

Display history uses a versioned, per-institution local-storage key:

```text
college-ai-chatbot.public-chat.v1:{INSTITUTION_CODE}
```

The version-1 envelope contains only the institution code and up to 40 public
messages with local IDs, roles, content, timestamps, response status, and safe source
fields. Reads validate every field, source count, content length, version, tenant, and
message count. Corrupt, old-version, cross-institution, or excessive data resets to an
empty history. Storage denial/quota failures leave the in-memory chat functional.
Tokens, internal IDs, request metadata, provider details, and diagnostics are absent.

## 10. Loading and error behavior

While one request is active, the composer and send button are disabled and an
accessible `Thinking…` status is shown; the UI does not claim streaming. Errors use
fixed frontend messages for validation, institution availability, private-information
authentication, timeout, network, server, malformed response, and unexpected failure.
Backend bodies and exception strings are never rendered. A retry action targets only
the failed user turn.

An `insufficient_context` response becomes a stable message explaining that reliable
public college information was not found. It does not fabricate an answer or show an
empty source section.

## 11. Source display

Source cards render only the backend-provided `title`, `section`, and `quote`. Missing
titles use a generic display label. No source section appears for an empty array, no
internal identifiers are reconstructed, and no model-generated source link is made
clickable.

## 12. Safe AI rendering

Answers, questions, titles, sections, and quotes are React text children. No Markdown
parser, raw HTML renderer, `dangerouslySetInnerHTML`, URL detection, or executable
model output is used. Tests render a literal `<script>alert(1)</script>` answer and
verify no script element is created. The API layer also projects only known public
response fields before they enter state.

## 13. Accessibility

The page uses a heading hierarchy, semantic list/messages, labelled textarea,
semantic buttons, visible focus rings, disabled states, an `aria-live="polite"` log
for new messages, `role="status"` for loading, and `role="alert"` for failures.
Keyboard users can send, add a newline, select suggestions, retry, clear, and reach
sign-in without pointer input.

## 14. Responsive behavior

The public page is full-height using dynamic viewport units, with a constrained
desktop width and full-width mobile layout. Message widths adapt by breakpoint,
content and quotes break safely, and the sticky composer includes bottom safe-area
padding. Controls retain touch-friendly height and remain beside the textarea.

## 15. Security

- the public component is outside authentication and role resolution;
- the dedicated client has no privileged endpoint or authorization-header path;
- request serialization explicitly selects only `institution_code` and `message`;
- successful response projection explicitly selects only public fields;
- React escapes all untrusted answer/source content;
- per-institution storage accepts only a bounded safe schema;
- no credentials, secret environment variables, internal IDs, URLs, analytics, or
  server-side anonymous persistence were added.

The backend remains the public-knowledge authorization authority.

## 16. Environment configuration

The client reuses the existing public `VITE_API_BASE_URL` with the same-origin `/api`
fallback. No localhost production URL or new Vite variable was introduced. The Vite
development proxy remains unchanged, and no server secret is exposed to the bundle.

## 17. Tests

New focused tests cover:

- public direct routing without `AuthProvider` or role navigation;
- incomplete public-link routing outside authentication;
- exact endpoint, method, body, and absence of authorization;
- runtime malformed/non-JSON handling and response allow-listing;
- user/assistant rendering, safe sources, and no empty source section;
- loading state and duplicate-submission prevention;
- retry without duplicate user turns;
- Enter-to-send and local-history restoration;
- literal malicious HTML rendering without execution;
- versioned per-institution persistence and corrupt/old/oversized reset;
- absence of internal/provider/token fields in UI and storage.

Verification executed on 2026-09-28:

```text
Focused frontend:
  npm.cmd run test -- --pool=threads --maxWorkers=1 \
    src/services/publicChat.test.ts \
    src/features/publicChat/publicChatStorage.test.ts \
    src/features/publicChat/PublicChatPage.test.tsx
  3 files passed, 10 tests passed

Complete frontend:
  npm.cmd run test -- --pool=threads --maxWorkers=1
  50 files passed, 412 tests passed

TypeScript:
  npx.cmd tsc --noEmit -p tsconfig.json
  PASS

Production build:
  npm.cmd run build
  PASS — 97 modules transformed, built in 4.95s

Focused backend public-chat regression:
  DEBUG=false uv run pytest -q \
    tests/test_narrow_public_chat_api_phase_7_3.py \
    tests/test_public_rag_integration_phase_7_4.py \
    tests/test_public_ai_generation_phase_7_5.py
  65 passed, 1 deprecation warning

git diff --check
  PASS (only existing line-ending notices for two modified backend test files)
```

The first default Vitest attempt encountered three Windows worker-start timeouts
before collecting tests. Rerunning with the same Vitest suite and a single thread
completed successfully. No backend source or test file was changed by Phase 7.6.

## 18. Files changed

Created:

- `frontend/src/types/publicChat.ts`
- `frontend/src/services/publicChat.ts`
- `frontend/src/services/publicChat.test.ts`
- `frontend/src/features/publicChat/PublicChatPage.tsx`
- `frontend/src/features/publicChat/PublicChatPage.test.tsx`
- `frontend/src/features/publicChat/usePublicChat.ts`
- `frontend/src/features/publicChat/publicChatStorage.ts`
- `frontend/src/features/publicChat/publicChatStorage.test.ts`
- `docs/status/PHASE_7_6_PUBLIC_AI_CHAT_FRONTEND.md`

Modified:

- `frontend/src/App.tsx`

Pre-existing Phase 7.5 backend worktree changes were preserved and not edited.

## 19. Deferred work

- rate limiting and IP throttling;
- concurrency controls;
- AI quotas and cost controls;
- CAPTCHA and external abuse prevention;
- persistent anonymous server conversations;
- bounded multi-turn server context/query rewriting;
- public-chat administration and conversation analytics;
- production deployment and host rewrite configuration.

## 20. Acceptance criteria

- [x] Public chat route exists and supports direct navigation.
- [x] The route works without authentication or an authenticated shell.
- [x] Dedicated public API client calls `POST /api/v1/chat/public`.
- [x] Request exactly matches `PublicChatRequest`; no internal controls are sent.
- [x] Institution code is resolved from an explicit public route and validated.
- [x] User/assistant UI, loading, errors, retry, and safe sources are implemented.
- [x] AI and source output is rendered safely as text.
- [x] Unexpected response/internal metadata is not retained or exposed.
- [x] Bounded, versioned, per-institution local display history works.
- [x] No server-side anonymous history was introduced.
- [x] Responsive desktop/mobile and keyboard/accessibility behavior is implemented.
- [x] Focused security tests and all existing frontend tests pass.
- [x] Typecheck and production build pass.
- [x] Focused backend regression remains passing; backend was untouched.
- [x] No rate/cost/abuse control or deployment system was implemented.

**PHASE 7.6 STATUS: COMPLETE**
