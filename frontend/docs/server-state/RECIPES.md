# Server-state TypeScript recipes

Follow [SERVER_STATE.md](../SERVER_STATE.md) for architecture and required UI states.
These examples describe proposed feature modules; they have not been added to `src/`.
They reuse existing services and response contracts without introducing endpoints.

## 1. Keys and scope: `academic-setup/queries/academicKeys.ts`

```ts
export interface AcademicScope {
  readonly sessionGeneration: number
  readonly userId: string
  readonly institutionId: string
  readonly role: string
  readonly grantsKey: string
}

export const academicKeys = {
  root: (scope: AcademicScope) => ['academics', scope] as const,
  catalogue: (scope: AcademicScope) => [...academicKeys.root(scope), 'catalogue'] as const,
  structure: (scope: AcademicScope) => [...academicKeys.root(scope), 'structure'] as const,
}
```

Build scope at the existing authenticated workspace boundary from canonical auth.
Use `JSON.stringify([...effectivePermissions].sort())` for `grantsKey`. Require a
defined generation in migrated private scopes; do not fall back to a raw token.
Mount the workspace keyed by this identity so replacement identity clears drafts.

## 2. Colocated query: `academic-setup/queries/academicQueries.ts`

```ts
import { queryOptions } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY } from '../../../../lib/queryClient.ts'
import { getAcademicSetup } from '../../../../services/admin/academics.ts'
import { academicKeys, type AcademicScope } from './academicKeys.ts'

export class AcademicScopeError extends Error {}

export interface AcademicQueryContext {
  scope: AcademicScope
  accessToken: string
  canReadCatalogues: boolean
  isCurrent: () => boolean
}

export function academicCatalogueOptions(context: AcademicQueryContext) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: academicKeys.catalogue(context.scope),
    enabled: context.canReadCatalogues,
    queryFn: async ({ signal }) => {
      signal.throwIfAborted()
      if (!context.isCurrent()) throw new AcademicScopeError('The academic session changed.')
      const catalogue = await getAcademicSetup(context.accessToken)
      signal.throwIfAborted()
      if (!context.isCurrent()) throw new AcademicScopeError('The academic session changed.')
      if (catalogue.institution_id !== context.scope.institutionId) {
        throw new AcademicScopeError('Academic data is unavailable for this institution.')
      }
      return catalogue
    },
  })
}
```

`isCurrent` must compare the captured generation/user/institution/role/grants against
live auth refs updated synchronously on identity changes. Reuse/extend existing
session guards; a closure comparing captured values to themselves is insufficient.
Rebuild context/options with the latest token each render. Permissions gate the
request; server `manageable` and valid current data separately gate writes.

The current service accepts only a token. The signal checks discard canceled reads
but do not abort the HTTP request. When migrating transport, add an optional signal
through `getAcademicSetup` and `requestJson` to `fetch`, preserve abort exceptions,
then call `getAcademicSetup(context.accessToken, signal)`. Keep expiry events intact.
See TanStack's [cancellation guidance](https://tanstack.com/query/v5/docs/framework/react/guides/query-cancellation).

In `departments/useDepartments.ts`, subscribe using the same factory as other
catalogue consumers. Keep pure search/sort projections beside the feature:

```ts
import { useQuery } from '@tanstack/react-query'
import { academicCatalogueOptions, type AcademicQueryContext } from '../queries/academicQueries.ts'

export function useDepartmentRecords(context: AcademicQueryContext) {
  return useQuery({
    ...academicCatalogueOptions(context),
    select: (catalogue) =>
      catalogue.records.departments?.filter((record) => record.institution_id === context.scope.institutionId),
  })
}
```

The cache retains the complete catalogue. A missing `departments` property remains
undefined, so the feature can distinguish unavailable data from an empty list.
The page must hide data on lost permission, authorization error or tenant mismatch
even if an observer still has previously successful data. Treat `AcademicScopeError`
as an access/integrity failure when deciding whether cached content can be shown.

## 3. Optimistic description edit: `departments/useUpdateDepartmentDescription.ts`

This recipe previews one row through mutation variables. It patches the canonical
cache only after success, so a rejected write needs no cache rollback. Keep draft
validation, editor notices and the UI overlay in the existing department feature.

```ts
import { useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateAcademicRecord } from '../../../../services/admin/academics.ts'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import { academicKeys } from '../queries/academicKeys.ts'
import type { AcademicQueryContext } from '../queries/academicQueries.ts'

interface DescriptionContext extends AcademicQueryContext {
  canManageDepartments: () => boolean
}

export function useUpdateDepartmentDescription(context: DescriptionContext, departmentId: string) {
  const client = useQueryClient()
  const locked = useRef(false)
  const key = academicKeys.catalogue(context.scope)
  const mutation = useMutation({
    mutationKey: [...academicKeys.root(context.scope), 'update-description', departmentId],
    retry: false,
    mutationFn: async (description: string | null) => {
      if (!context.isCurrent() || !context.canManageDepartments()) {
        throw new Error('Department changes are unavailable. Refresh and try again.')
      }
      const catalogue = client.getQueryData<AcademicCatalogue>(key)
      const exists =
        catalogue?.institution_id === context.scope.institutionId &&
        catalogue.records.departments?.some((record) => record.department_id === departmentId)
      if (!exists) throw new Error('This department is no longer available.')
      const saved = await updateAcademicRecord(context.accessToken, 'departments', departmentId, { description })
      if (saved.institution_id !== context.scope.institutionId || saved.department_id !== departmentId) {
        throw new Error('The saved department could not be verified.')
      }
      return saved
    },
    onSuccess: async (saved) => {
      if (!context.isCurrent()) return
      await client.cancelQueries({ queryKey: key, exact: true })
      if (!context.isCurrent()) return
      client.setQueryData<AcademicCatalogue>(key, (old) => {
        if (old?.institution_id !== context.scope.institutionId) return old
        return {
          ...old,
          records: {
            ...old.records,
            departments: old.records.departments?.map((record) =>
              record.department_id === saved.department_id ? saved : record,
            ),
          },
        }
      })
    },
    onSettled: async () => {
      try {
        if (context.isCurrent()) await client.invalidateQueries({ queryKey: key, exact: true })
      } finally {
        locked.current = false
      }
    },
  })

  function save(description: string | null) {
    if (locked.current || mutation.isPending) return
    locked.current = true
    mutation.mutate(description)
  }

  return { save, isPending: mutation.isPending, variables: mutation.variables, error: mutation.error }
}
```

`canManageDepartments` must consult current authorized, verified catalogue data,
`manageable`, and existing refresh/error restrictions. Keep this hook mounted for
one department within one identity-keyed editor; block changing targets during save.
The local lock prevents duplicate submissions through that editor. If several
editors can write the same department, add a shared per-scope/record lock before
allowing concurrent editing. Different rows can reconcile independently.

In that row, render `mutation.isPending ? mutation.variables : department.description`
and a “Saving...” label. On error the original description returns; keep the editable
draft and offer retry. Clear/reset mutation feedback when opening another draft.
The response patch preserves other rows; exact catalogue invalidation refreshes all
its projections. A description-only edit does not change structure relationships.

For an optimistic cache patch affecting several observers, implement cancel,
snapshot, patch, guarded rollback and settled invalidation as described in the
[main guide](../SERVER_STATE.md#7-optimistic-changes), with concurrency coverage.

## 4. Rendering and verification

Keep feature components focused on the [required state table](../SERVER_STATE.md#8-required-states-for-every-page-and-independent-section).
Do not early-return on every `isError`: an ordinary failed background refresh may
still have valid cached data. Access denial takes precedence over retained data.
Use `data !== undefined` rather than truthiness to detect cached values, and handle
successful absent entity collections separately from pending/error states.

Use the existing design system for skeletons, status text, stale banners and Retry.
Use `dataUpdatedAt` for last cache-update time; `setQueryData` also advances it.
Track full-read time separately if needed. Pending UI overlays leave cache timestamps
untouched. Allow pagination placeholders only inside the same identity/permission
scope. Never carry previous-tenant data forward.

Verify behavior with the actual provider and an isolated test QueryClient. For these
recipes, cover shared catalogue requests, exact invalidation, late callbacks after
identity change, missing entity collections and description failure/retry. Use a
deferred service promise to prove the optimistic preview appears before resolution
and disappears on rejection while the original cache and draft survive. Confirm
background-read failure after a successful write offers refresh without writing again.
