# Shared resources and chat: application architecture

Proposed architecture. [README](README.md) separates this plan from existing code.

## Reuse the current application

Keep React/TypeScript, feature hooks, TanStack Query, the existing service clients,
FastAPI layers and the document/retrieval pipeline. This design does not require
a new agent framework, a second resource store or separate role chat services.

```mermaid
flowchart TD
    R[Admin / Faculty / Staff workspace] --> L[Shared Learning Resources page]
    R --> C[Existing shared ChatShell]
    L --> K[Authorized knowledge API]
    C --> A[Authenticated chat API]
    K --> P[Server identity, permissions and institution scope]
    A --> P
    P --> S[Knowledge services and eligibility policy]
    S --> D[Existing sources, documents, versions and processing runs]
    S --> V[Eligible chunks and embeddings]
    A --> O[Existing chat orchestration and bounded history]
    O --> S
    O --> G[Generation adapter]
    O --> H[Owned conversations, messages and citations]
```

## Data ownership and eligibility

Reuse `knowledge_sources -> documents -> document_versions -> processing_runs`
and the existing chunk/embedding records. FAQs and notices retain their canonical
tables and existing synchronization into the retrieval pipeline. Presentation
adapters must not create a second editable copy of that text.

Treat these as independent dimensions:

- **Processing:** uploaded/queued, extracting/chunking/embedding, indexed or failed.
  UI labels are derived from actual processing and embedding fields; the current
  processing-run `ready` value alone does not establish complete AI readiness.
- **Publication:** existing source/version lifecycle and effective dates.
- **Audience:** `public`, `authenticated` and `restricted` visibility plus
  explicit selected-role targets in the proposed revision model.
- **Action capability:** server-authorized read, create, edit, version and
  publication actions within an active institution grant.

The target reader/RAG predicate is: correct institution, authorized audience,
published and effective source/version, valid processing provenance and completed
embeddings. Versions must belong to the approved published revision's manifest.
Management reads may expose authorized drafts without making them retrievable.
Metadata-only sources can be listed with AI unavailable.

Centralize the authenticated eligibility policy under `services/knowledge/` and
apply its criteria to repository retrieval before ranking/limiting results,
resource detail, citations and file delivery. Reuse date/provenance helpers
where appropriate; preserve the stricter anonymous public-knowledge policy.
Authenticated chat now uses the audience-aware SQL search and rechecks stored
provenance before delivery/history. Lower-level legacy vector helpers remain
internal; they do not grant HTTP reader access. See the [implemented API](API.md).

The [audience upload plan](AUDIENCE_UPLOAD.md) defines Public, signed-in members
and selected roles, including Students only, Staff only and Faculty only.
Selected roles match verified active institution grants with OR semantics.
No role targets means no restricted reader access. New uploads are private drafts;
uploaders propose an audience and admins approve/publish the exact revision.
Creation/indexing never publishes or replaces the live audience/version.

An admin's ability to manage a draft does not authorize the ordinary assistant
to answer from it. A future editor preview would need a separate explicit,
audited contract. Personal academic records remain outside the chat service.

## Permission contract

Runtime grants and role/scope dependencies must both pass. Reference defaults do
not prove an endpoint is usable: current admin CRUD handlers require admin scope,
even when faculty/staff have similarly named permissions.

| Operation                            | Proposed enforcement using existing permission names                                                                                |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| Read shared library metadata/details | Active admin/faculty/staff institution scope plus `documents.read`; filter every record by reader/management policy.                |
| Create a source or ingest content    | Exact scoped role plus `ai.knowledge.create`; preserve additional document-create requirements for the chosen upload operation.     |
| Upload a document/version            | `documents.create` / `documents.update` respectively, plus knowledge-create when executing indexing; check source/version ancestry. |
| Edit source metadata/publication     | `ai.knowledge.update` and existing scoped management policy; no new faculty/staff grant is inferred.                                |
| Delete documents                     | `documents.delete` plus the existing management policy.                                                                             |
| Chat or ask about a source           | `ai.chat` plus eligibility of every retrieved source; a resource selector never grants access.                                      |
| FAQ editorial operations             | Preserve existing knowledge permissions and admin scope until explicitly migrated.                                                  |

The shared `documents.read` projection exposes only reader-safe metadata.
Institution-wide draft review requires `ai.knowledge.read` and existing admin
management scope. Faculty/staff own-draft access uses an explicit creator/ownership
policy with exact create/edit grants; it is not a general management-read grant.
The new reader API must not inherit the broader payload of an admin endpoint.
Publication and live audience changes require active institution-admin scope and
`ai.knowledge.update`; faculty/staff only propose them in reviewable revisions.

Return operation-specific capabilities from the server, for example `canUpload`,
`canAddVersion`, `canEditMetadata`, `canPublish`, `canRetryIndexing`, `canDelete`
and `canAskAi`. They describe exact allowed operations on that record, including
state constraints. The frontend uses them for presentation; endpoints recheck.
Do not use a generic edit flag to imply publication or upload permission.

## Proposed API surface

The [implemented revision facade](API.md) now supplies library, drafts, uploads,
review and publication. The table below retains broader future resource-context
and file-delivery proposals; it is not an endpoint inventory. Keep `/api/v1/admin/*`,
`/api/v1/documents/*`, `/api/v1/students/me/resources` and current chat/history
contracts compatible while introducing focused endpoints under the knowledge
feature. Document every new method/path in the appropriate permission policy.
Audience/review enforcement deliberately constrains previous mutation behavior:
all legacy write paths must use the same approved-revision publication policy.

| Proposed route under `/api/v1`                     | Responsibility                                                                                                               |
| -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `GET /knowledge/resources`                         | Safe scoped list, supported search/type/status filters, bounded pagination and operation capabilities.                       |
| `GET /knowledge/resources/{source_id}`             | Authorized source metadata and permitted document/version summaries.                                                         |
| `POST /knowledge/resources`                        | Source creation with server-owned tenant/actor and constrained editable fields.                                              |
| `POST /knowledge/resources/{source_id}/documents`  | Shared upload facade reusing existing ingestion/orchestration.                                                               |
| `POST /knowledge/documents/{document_id}/versions` | Stage a scoped draft version; retain the live version until atomic admin publication.                                        |
| `PATCH /knowledge/resources/{source_id}`           | Authorized draft metadata/requested-audience changes with state validation; publication uses an explicit revision operation. |

PATCH edits drafts, not live publication/audience. Add explicit revision submit,
request-changes, publish and unpublish operations as detailed in the audience
plan; the publisher must approve the exact metadata, audience and file manifest.

Add status/retry/file-delivery endpoints only when their underlying service and
policy support them. Ordinary responses omit storage paths, extracted content,
raw processor errors and credentials. List responses declare pagination/total
semantics; a returned page length is never presented as a global total.
Readiness and capability fields must come from persisted state, not client timers.

`AuthenticatedChatRequest` now accepts optional `resource_id` while forbidding
unknown fields and internal retrieval filters. Resource context is authorized
server-side and persisted on the owned conversation. Context mismatches are
rejected before saving a turn. Never expose
internal chunks, prompt controls or provider/model selection as browser input.
Keep the existing required institution field compatible while using `/auth/me`
identity in the client; the server continues to check it against active scope.

## Layer placement

| Layer                                       | Ownership                                                                                               |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Shared frontend feature                     | `features/learning-resources/`; shell composition only in role features.                                |
| Frontend transport                          | Proposed `services/knowledge/` domain; update the services guide when introduced.                       |
| Frontend contracts                          | Reuse admin/student types where accurate; add focused knowledge contracts only for new responses.       |
| Knowledge API/services/repositories/schemas | `backend/app/{api,services,repositories,schemas}/knowledge/`; add focused modules to existing packages. |
| Chat orchestration                          | Existing `services/ai/chat.py` and `chat_support/`; retain generation/history adapters.                 |
| Database changes                            | `supabase/migrations/` and maintained migration sources, only for demonstrated contract gaps.           |

Move reusable orchestration out of admin ownership into knowledge services as
needed, updating all callers and tests together. Keep admin wrappers for their
existing URL/response contracts while enforcing review; do not make knowledge
services depend on admin routes. Replace early version supersession with draft
staging and an atomic approved-version switch for the new upload workflow.
Inspect destination file counts before implementing; split by workflow within
the 15-file/250-line limits. The [database model](DATABASE_MODEL.md) now implements
the schema foundation. Shared writers/readers, runtime policy and
[resource-scoped conversations](RESOURCE_CHAT.md) are implemented.

## Server state, identity and reliability

Use domain query keys scoped by auth generation, user, institution, grants and
normalized request filters according to the existing server-state guide. Keep
access tokens out of keys. Query options own reads; hooks own guarded mutations;
components own rendering and local interaction state.

Invalidate the affected scoped resource lists, exact detail and related document
status after writes. Invalidate only the affected conversation/message keys
after chat. Publication changes affect resource availability; always recheck it
on the server rather than relying on a cached client badge.

On logout, account/tenant/grant replacement, cancel/remove retired private queries
and reset local chat/resource context. Every late read/mutation callback checks
the captured identity before changing state or caches. Token renewal retains the
existing session-generation behavior.

Preserve drafts after errors, prevent duplicate submits and use version/conflict
checks for publication or replacement. Automatic retries of writes require an
explicit idempotency contract. Start by reusing the current synchronous pipeline;
if durable jobs are introduced, add persisted stage/retry state and a worker
before offering background completion or detailed live progress in the UI.

History restoration verifies ownership and current source eligibility. Unavailable
resource context redacts titles and the full message history; invalid answer
provenance redacts that answer and its dependent tail. Follow-ups cannot continue
after revocation. Keep telemetry content-free and separate from user-visible errors.
