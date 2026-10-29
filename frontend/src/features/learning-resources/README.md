# Shared Learning Resources workspace

Admin, faculty and staff mount `LearningResourcesPage.tsx`. The page owns its
heading, library, own submissions, audience form, files and revision detail.
Admin review uses the same detail drawer with explicit review/publication actions.
Admin navigation retains its internal `documents` view key with the shared
**Learning Resources** label. Faculty keeps `/faculty/resources`; staff adds the
same local workspace view. The student metadata-only page remains separate.

| Folder/module                                          | Responsibility                                                                          |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `ResourceWorkspace.tsx`, list/toolbar/state components | Navigation, loaded-page filters, server pagination and independent loading/error states |
| `data/`                                                | Canonical identity/grant scope, query keys/options and guarded mutation reconciliation  |
| `editor/`                                              | Metadata/audience draft, validation, file attachment/replacement and failed-index retry |
| `details/`                                             | Shared modal, revision information, file states and confirmed admin decisions           |
| `styles/`                                              | Scoped design-token styles and responsive records/drawers                               |
| `__tests__/`                                           | Role composition, library states, editing, review and identity regression coverage      |

Transport lives in `services/knowledge/resources.ts`; contracts live in
`types/learningResources.ts`. Read cancellation reaches fetch through the shared
authenticated transport. No token enters a query/mutation key. Cache scope
includes generation, user, institution, role and sorted effective grants.
Identity/grant changes discard drafts and retire reads; same-session token renewal
preserves edits. Late mutation callbacks cannot refill a retired scope.

The backend remains authoritative. UI actions use resolved operation grants,
ownership where returned and revision state. No role grants are inferred.
Draft creation and file attachment are separate saved steps, so an indexing
failure cannot cause another source to be created on retry. All writes wait for
server confirmation and use the displayed revision/policy concurrency tokens.
409/unknown outcomes block further writes until explicit reload. Dirty reload
requires confirmation; background reads never overwrite typed metadata.
403 hides cached private content; a denied/missing source detail hides its cache.

Search/audience/status filters apply only to the current server page and are
labeled accordingly. Full-library search and file delivery/removal remain absent.
Published resource details use the shared chat eligibility button and chat view;
Ask AI is authorized by the server and persists scope across follow-ups/history.
Canonical FAQ/notice content uses its existing editors. The prepared migration
and backend must be deployed together before these screens can use a live stack.

Run frontend structure/build/tests and the loopback-only
[browser harness](../../../../scripts/validation/learning_resource_ui/README.md).
The harness supports intercepted HTTP fixtures and the real API/SQL workflow in
disposable PostgreSQL. Deployed authentication/storage/providers require staging
verification.
