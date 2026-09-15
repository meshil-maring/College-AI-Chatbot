# College AI Chatbot — Final Demo Status

## Project purpose

The project is a college-focused AI chatbot that answers questions using retrieved institutional knowledge. It is designed to keep factual college claims grounded in retrieved sources, return an insufficient-context result when the knowledge base does not support a claim, and preserve authenticated conversation history for multi-turn use.

## Current architecture

```text
React + TypeScript + Vite frontend
  -> typed browser API client through the Vite /api proxy
  -> FastAPI backend
  -> Supabase authentication and persisted conversation data
  -> embedding and pgvector retrieval over seeded college knowledge
  -> OpenRouter generation (openai/gpt-4o-mini)
  -> structured chat response rendered by the frontend
```

The frontend is API-only. Retrieval, generation, prompt handling, persistence, authorization decisions, and source construction remain backend responsibilities.

## Completed and locked phases

- **Phase 3:** AI/RAG retrieval foundation, including ingestion, extraction, chunking, embeddings, vector storage, access filtering, retrieval evaluation, and the demo knowledge dataset.
- **Phase 4.4:** structured `ChatResponse`, structured sources, usage metadata, citation safety, provenance enrichment, and conversation/message integration.
- **Phase 4.4 amendment:** controlled conversational-context prompt compatibility, preserving retrieved knowledge as the sole authority for factual institutional claims.
- **Phase 5.2:** React, TypeScript, Vite, Tailwind, frontend structure, environment foundation, and development proxy.
- **Phase 5.3:** typed frontend chat contract and native-fetch API client.
- **Phase 5.4:** login, authenticated-user validation, token restoration, local logout, and authentication UI/state.
- **Phase 5.5:** authenticated chat UI, chat API integration, loading/error states, source/usage display, and backend-owned session/conversation propagation.
- **Phase 5.6:** authenticated conversation listing and chronological message retrieval with ownership isolation.
- **Phase 5.7b:** bounded, authenticated, chronological conversation history in generation context.
- **Phase 5.8:** end-to-end physical demo validation and integration hardening.

The locked phase records are the authoritative historical scope and validation record. No locked behavior is reopened by this document.

## Phase 5.8 physical validation

Phase 5.8 validated the real frontend, real authenticated FastAPI backend, real Supabase data, live pgvector retrieval, and live OpenRouter generation as one system.

Results:

- Backend automated suite: **382 passed, 3 intentionally skipped, 0 failed**
- Frontend automated suite: **23 passed, 0 failed**
- Frontend production build: **passed**
- Live checks C1-C10: **all passed**
- Full 17-step demo journey: **17/17 passed**
- Integration defects found: **none**

The live journey verified application load, login, grounded answers, source and usage rendering, conversation list/open/continuation, unambiguous coreference, insufficient-context behavior, cross-user ownership denial, and reload persistence.

## Authentication

The backend exposes `POST /api/v1/auth/login` and `GET /api/v1/auth/me`. The frontend treats the Supabase-issued JWT access token as opaque, sends it only through the authorization header, and restores a stored token by revalidating it with `/auth/me`.

Passwords are not persisted. Tokens are not logged, displayed, placed in URLs, query parameters, or request bodies. The backend remains authoritative for JWT verification and user resolution. Logout is local token/state clearing because no backend revocation endpoint exists.

## RAG and retrieval

The backend retrieves seeded college knowledge using embeddings and pgvector similarity search. Retrieved knowledge is the only authority for factual institutional claims. Retrieval and generation were both exercised live in Phase 5.8.

## LLM generation

Generation uses the configured OpenRouter provider and `openai/gpt-4o-mini` model. Phase 5.8 validated real provider calls rather than mocked generation.

## Structured responses

The chat contract returns a structured response including answer/status data, source references, structured sources, model metadata, usage information, session/conversation identifiers, and message identity where available. The frontend contract mirrors the backend JSON boundary and preserves snake_case fields.

## Conversation history

Authenticated users can list their own conversations and retrieve their own messages in chronological order. Conversation listing is newest first. The frontend displays this history and can continue a selected conversation using its backend-issued conversation identifier.

## Conversational context and coreference

For an existing authenticated conversation, the backend supplies a bounded history window to the generation context. It preserves chronological turns, avoids duplicating the current query, and validates ownership before history can reach the provider.

Conversation history supports conversational intent, questions about the conversation, and unambiguous coreference. It is not institutional knowledge and cannot substitute for retrieved evidence for factual college claims.

## Insufficient-context behavior

When retrieved knowledge does not support a factual college claim, the system returns the locked conservative insufficient-context result rather than fabricating an answer. This was physically validated with an unsupported college question in Phase 5.8.

## Source references and usage information

The backend constructs source references and structured source cards from retrieved knowledge. The frontend renders backend-provided source title, section, quote, and relevance information without generating citations itself. It also displays backend-provided input/output token usage and model metadata when available.

## Conversation ownership and security

Conversation endpoints require authenticated users. Listings are filtered by user, and message retrieval verifies ownership. Unknown and foreign conversations both return `404 CONVERSATION_NOT_FOUND`, preventing existence disclosure. This isolation was verified live in Phase 5.8 using a real authenticated session.

## Frontend/backend separation

The frontend does not directly access Supabase, implement ownership checks, persist messages, perform RAG, generate embeddings, select providers, construct citations, or handle prompt logic. It uses the typed API client and renders backend responses. The backend owns the relevant security and intelligence boundaries.

## Current automated test and build status

The current locked validation baseline is Phase 5.8:

- Backend: **382 passed, 3 intentionally skipped, 0 failed**
- Frontend: **23 passed, 0 failed**
- Frontend build: **passed**

The five historical test-debt cases subsequently targeted during Phase 5.9 reconciliation also passed **5/5** at the authoritative HEAD: invalid JWT handling, three R2 ingestion cases, and vector-search validation-error mapping.

## Demo implementation status

**Complete.** Phase 5.8 established that the required end-to-end demo is functional and contains no identified integration defect. The next activity is demonstration, documentation, or deployment, not another implementation phase.

## Known documented limitations

- Deliberately ambiguous compound/list coreference such as “the second one” may remain unresolved by the model. Phase 5.8 verified that this is a model-interpretation limitation under ambiguous wording, not a missing history-integration defect; unambiguous coreference works.
- On this Windows environment, the default Vitest forks pool timed out while starting workers. The existing `npx vitest run --pool=threads` invocation passed all frontend tests. This is documented as an environment/tooling quirk, not a product defect.
- Root-level manual physical-validation scripts are not part of `pytest tests/`; collecting them with the test suite can produce unrelated fixture-resolution errors.

## Optional future enhancements

These are not required for the completed demo:

- Product-defined handling for ambiguous multi-entity coreference.
- Deployment automation and operational runbooks.
- Observability, analytics, feedback, administration, or document-management interfaces.
- Streaming, model selection, and other expanded chatbot features.
- Tooling changes for the Windows Vitest worker-pool behavior.

## Final record

- Current HEAD: `ca70cba2292b9676abfa8049e2147bc2c4412fbb`
- File created: `FINAL_DEMO_STATUS.md`
- Production files changed: NO
- Existing lock files changed: NO
- `.vscode/settings.json` preserved: YES
- Working-tree status: modified `.vscode/settings.json` (pre-existing) and untracked `PHASE_5_9_SCOPE_REPORT.md` (pre-existing) plus `FINAL_DEMO_STATUS.md`.
