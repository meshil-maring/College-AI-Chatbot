# Frontend server-state architecture

Project standard for new and migrated pages, 28 October 2026. Stack: React 19,
TypeScript, Vite, TanStack Query v5, Tailwind/CSS tokens and Vitest/Testing Library.
Apply this guide across public, admin, staff, faculty, student and platform screens.
Use [STRUCTURE.md](STRUCTURE.md) for ownership, [ROUTES.md](ROUTES.md) for routing,
and [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) for presentation and accessibility.

This document defines the implementation target; existing screens have not all
adopted it. The [TypeScript recipes](server-state/RECIPES.md) illustrate the target
using existing academic contracts. This documentation change does not migrate runtime code.

## 1. Existing foundation and adoption boundaries

| Existing module                                   | Responsibility and current behavior                                                                                                     |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `src/lib/queryClient.ts`                          | One browser client; query/mutation retries disabled, `staleTime: 0`, `gcTime: 0`, window-focus refetch disabled.                        |
| `src/providers/QueryProvider.tsx`, `src/main.tsx` | Provide that client once around the application.                                                                                        |
| `NAVIGATION_QUERY_POLICY`                         | Opt-in freshness of 60 seconds, inactive retention of five minutes, refetch on stale remount and `meta.navigationCache`.                |
| `src/hooks/useApiQuery.ts`                        | Existing adapter appends instance identifiers unless navigation caching is requested; ordinary calls do not share stable cache entries. |
| `src/features/auth/session/`                      | Owns credentials, canonical identity, generation guards, token-scoped expiry and navigation-cache cleanup.                              |
| `src/services/`, `src/types/`                     | Domain transport/error handling and backend contracts.                                                                                  |

Reuse the provider and client. New or fully migrated resources use feature-owned
`queryOptions` factories with `useQuery` and `useQueryClient`. Keep existing adapter
callers working until their complete resource workflow is migrated. Do not change
global cache defaults or remove authentication guards as part of a page migration.

## 2. Placement and dependency direction

Example target additions within the existing Academic Setup feature:

```text
frontend/src/
  lib/queryClient.ts                         # shared cache policy/lifecycle
  providers/QueryProvider.tsx                # existing application provider
  services/admin/academics.ts                # HTTP and typed API errors
  types/academicSetup.ts                     # backend request/response contracts
  features/admin/academic-setup/
    queries/
      academicKeys.ts                        # domain keys and scope type
      academicQueries.ts                     # colocated queryFn/options
      academicQueries.test.ts                # cache and identity behavior
    departments/
      useDepartments.ts                     # query subscription and derivations
      useDepartmentEditor.ts                # drafts, validation, drawer workflow
      useUpdateDepartmentDescription.ts      # focused mutation and reconciliation
      DepartmentsPage.tsx                   # composition and rendering
      DepartmentListState.tsx                # feature loading/error/empty UI
      __tests__/                            # adjacent workflow tests/fixtures
```

These are proposed locations; inspect existing files before adding anything.
The shared academic query belongs above Departments because Programs, Calendar
and other academic pages consume the same catalogue. For a single-screen resource,
keep its key factory, query factory and mutation beside that screen; add a `queries/`
subfolder only when responsibilities justify it. Avoid a global query registry.

Dependency direction: page -> feature hook -> query factory/domain service ->
transport. Services depend on contracts and shared infrastructure, never features.
Colocate each query function with its key/options factory while keeping HTTP in
the existing domain service. Share components or query helpers after real reuse.
Follow the 15-direct-file and 250-physical-line limits before adding modules.

## 3. State ownership

| Data                                                        | Owner                                                                                |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Server records, lists, counts and saved details             | TanStack Query cache; derive views with `select` or pure helpers.                    |
| Loading, fetch errors, refetch status and mutation progress | Query/mutation results.                                                              |
| Search, sort, page and selected record ID                   | URL when navigation/shareable; otherwise local feature state.                        |
| Form drafts, validation, drawer visibility and confirmation | Local editor hook; a draft may start from server data.                               |
| Credentials, session lifecycle and canonical identity       | Existing auth provider; a controlled identity snapshot is required for access gates. |
| Shared client preferences, such as sidebar visibility       | Existing client state/context when needed.                                           |

Never mirror server collections into Redux, Zustand, application context or a
second client cache. Do not synchronize query results into `useState` with effects.
Retain editable drafts independently; background reads must not overwrite typing.
Store selected IDs and derive current records, except for deliberate form snapshots.
Keep streaming chat buffers local; reconcile saved conversation history through queries.

## 4. Domain-shaped keys and identity

Use serializable array keys, ordered from domain to scope to resource to variant:

```ts
;['academics', scope, 'catalogue'][('academics', scope, 'structure')][
  ('conversations', scope, 'list', { page, search })
][('conversations', scope, 'detail', conversationId, 'messages')][('institutions', 'public', 'lookup', { code })]
```

Factories own these keys; consumers never reconstruct them by hand. `scope` includes
session generation, canonical user ID, institution ID, role and a stable signature
of sorted effective permissions. Platform scope uses its explicit platform identity;
public reads use public scope and their actual response dependencies.

Include every server response dependency: ID, server filters, sort and page/cursor.
Normalize defaults before key construction. Keep local catalogue filters out of the
key when they do not affect the request. Never include credentials, component IDs,
functions, mutable objects or timestamps. Give infinite queries a separate key from
ordinary lists. These rules follow TanStack's [query-key guidance](https://tanstack.com/query/v5/docs/framework/react/guides/query-keys).

Use the current credential in the query function, outside the key. Rebuild options
from current auth on render. Mount private feature hooks only after authentication
and required scope exist; gate optional reads with `enabled` and render why they wait.
Check returned institution IDs and preserve server-derived `manageable` grants.

On logout or identity/permission replacement, hide private content immediately,
cancel/remove retired-scope queries and reset drafts/optimistic overlays. Late read
and mutation callbacks must check the captured scope against live identity before
writing caches, invalidating, showing notices or navigating. Query removal alone
does not cancel a server write or prevent its callback from repopulating a cache.

Keep `meta.navigationCache` on retained private queries so existing cleanup finds
them. Today token changes clear that marked cache, including renewal; generation
stays stable across renewal so drafts survive. Preserve that cleanup until a
separately tested lifecycle change covers logout, renewal and permission replacement.

## 5. Reads, freshness and cancellation

Define typed `queryOptions` factories once; reuse them for subscriptions and prefetch.
Use `select` for screen-specific projections while preserving the cached response
shape. See TanStack's [query-options guidance](https://tanstack.com/query/v5/docs/framework/react/guides/query-options).

- Use `NAVIGATION_QUERY_POLICY` for ordinary authenticated navigation reads.
  Document overrides beside the owning query, such as shorter freshness for queues.
- Freshness controls when data becomes stale; `gcTime` controls retention after the
  last observer leaves. Becoming stale does not start a timer-based network request.
- Keep retries disabled by default. An endpoint-specific bounded read retry must
  distinguish transient failures from authorization/validation failures. Writes
  require explicit idempotency guarantees before automatic retries are enabled.
- Throw typed transport errors; never turn failures into successful empty arrays.
- Carry the query `AbortSignal` through service and transport to `fetch` when that
  path supports it. Preserve abort errors instead of translating them to network errors.
  Current academic transport does not accept a signal; recipes identify this limit.
- Prefetch only permitted reads using the same factory and scope; avoid blanket
  polling. Refetch only the independent section that needs refreshing.

Academic Setup currently returns an aggregate `AcademicCatalogue`, not separate
department/program list endpoints. Cache that response once per scope and derive
each page's records. Preserve absent entity collections as unavailable/unauthorized;
only an explicit returned empty collection means zero records.

## 6. Writes and targeted reconciliation

Use feature mutation hooks. Validate drafts locally, then let the backend authorize
and validate the write. Preserve token-scoped expiry, institution checks, current
grants, synchronous duplicate-submit locks and identity guards from existing editors.
Keep cache reconciliation in hook-level callbacks; component callbacks may disappear
when a component unmounts. Expose pending/error state and preserve drafts on failure.

| Write                                         | Invalidate within the captured current scope                                                  |
| --------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Department/program/year/semester/course write | Exact academic catalogue; add exact structure only when its represented relationships change. |
| Curriculum/cohort/academic-section write      | Exact structure; add catalogue only for affected represented data.                            |
| Conversation/message write                    | That conversation's messages and affected conversation-list prefix.                           |
| Student approval                              | Pending-approval queue and affected account/detail/list queries.                              |
| Notice/resource write                         | Affected domain list prefix and existing affected detail query.                               |

Document the dependency set beside each mutation. Prefer exact aggregate/detail
keys and scoped list prefixes; never invalidate the entire application after a write.
Update an existing exact cache entry from a validated full mutation response when
useful, then invalidate related lists/counts. Do not invent missing response fields.
Remove deleted detail entries and invalidate lists only after server success.

Return/await invalidation promises when the action should remain pending through
reconciliation. Active matching queries refetch; inactive matches normally become
stale for their next mount. Disabled reads do not automatically refetch. A successful
write followed by a failed read remains a saved write: show a refresh warning and
Retry without resubmitting it. See [invalidation](https://tanstack.com/query/v5/docs/framework/react/guides/query-invalidation)
and [mutation invalidation](https://tanstack.com/query/v5/docs/framework/react/guides/invalidations-from-mutations).

## 7. Optimistic changes

Use optimism for reversible, predictable edits such as a description or display
preference. Approvals, role/permission changes, publication, destructive actions and
multi-step academic saves wait for confirmed server results.

Prefer a pending UI overlay from mutation variables when only one view needs the
preview. On failure the overlay disappears, the original cache remains and the draft
can be retried. For an optimistic cache update shared by several views: cancel exact
reads, snapshot affected data in `onMutate`, apply an immutable patch, roll back in
`onError`, and invalidate affected keys in `onSettled`.

Do not restore a whole list snapshot over a newer mutation. Lock the affected
resource before `onMutate`, or use tested per-record/version-aware reconciliation.
Keep other rows usable when independent writes are safe. All reconciliation must
respect identity changes. See the recipe and TanStack's [optimistic-update guidance](https://tanstack.com/query/v5/docs/framework/react/guides/optimistic-updates).

## 8. Required states for every page and independent section

Evaluate access/identity validity first, then data availability, then fetch status.
Use the same state meanings and design tokens across roles.

| Condition                                                | Required presentation                                                                        |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Authentication/dependency unresolved or `enabled: false` | Explain the prerequisite; no indefinite loading spinner.                                     |
| Permission revoked, 401/403 or tenant mismatch           | Hide protected data/actions immediately; use existing session/access handling.               |
| No data and `isLoading`                                  | Layout-shaped skeleton and accessible loading label.                                         |
| No data and `fetchStatus: 'paused'`                      | Offline/waiting message; resume or offer permitted retry.                                    |
| No data and `isError`                                    | Blocking section error with Retry.                                                           |
| Successful authorized empty collection                   | Explain no records and offer a permitted create action.                                      |
| Local filters produce no matches                         | Keep filters visible and offer Clear filters.                                                |
| Data exists and `isFetching`                             | Keep content visible; show a small “Updating...” status.                                     |
| Data exists and `isError` after refetch                  | Keep authorized data; label it stale, show last successful update and Retry.                 |
| Data exists and `isStale`, without fetch/error           | Show “Last updated”/refresh affordance; preserve usable content.                             |
| `isPlaceholderData` during same-scope pagination         | Label previous results and disable actions needing the new page.                             |
| Mutation pending/error/success                           | “Saving...”, duplicate-submit prevention, inline error/draft retention, polite saved notice. |

Stale and fetching are independent. `isPending` alone also covers disabled queries;
`isLoading` means pending and fetching. `dataUpdatedAt` tracks successful cache updates,
including `setQueryData`; record full-read timestamps separately when required.
Never flash an empty state during initial load, replace content with a full-page
spinner during refetch, or display an unavailable count as zero. Keep stale warnings
visible for empty cached results too. Preserve existing academic write restrictions
while data is refreshing or unverified. See the [query reference](https://tanstack.com/query/v5/docs/framework/react/reference/useQuery).

## 9. Adoption and review checklist

1. Identify the owning feature, actual API response and all consumers of that resource.
2. Add/reuse its scoped key/options factories. Migrate reads and writes together,
   including related screens; invalidate legacy and new keys explicitly if coexistence
   is unavoidable. Record remaining consumers in the change description.
3. Remove duplicated fetched-data state and manual request effects. Keep drafts and
   navigation state local. Preserve existing auth, permissions and tenant behavior.
4. Implement the state table, mutation dependency set and useful optimistic behavior.
5. Verify sharing/deduplication, fresh remount, stale refetch, initial/background errors,
   authorized empty results, absent collections, failed-write draft retention, rollback
   or overlay removal, targeted invalidation and unrelated-query preservation.
6. Test logout, replacement login, tenant/grant changes, token renewal, late responses
   and late mutation callbacks. Use an isolated QueryClient per test with retries off;
   existing singleton-bound adapter tests must clear that singleton between cases.
7. Inspect affected folders for at most 15 direct maintained files and source/test/
   style/script files for at most 250 lines. Format focused files with local Prettier.
8. From `frontend`, run `npm run check:structure`, `npm run build` and `npm test`.
   Store verification output under repository-level `logs/frontend/`.
