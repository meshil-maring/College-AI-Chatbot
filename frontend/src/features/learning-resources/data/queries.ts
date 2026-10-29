import { queryOptions } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY } from '../../../lib/queryClient.ts'
import { getResource, getRevision, listResources, ResourceApiError } from '../../../services/knowledge/resources.ts'
import type { ResourceRevision, ResourceView } from '../../../types/learningResources.ts'
import type { ResourceContext } from './resourceIdentity.ts'

export const resourceKeys = {
  scope: (identity: string) => ['learning-resources', identity] as const,
  lists: (identity: string) => [...resourceKeys.scope(identity), 'lists'] as const,
  list: (identity: string, view: ResourceView, offset: number) =>
    [...resourceKeys.lists(identity), view, offset] as const,
  revision: (identity: string, id: string) => [...resourceKeys.scope(identity), 'revision', id] as const,
  source: (identity: string, id: string) => [...resourceKeys.scope(identity), 'source', id] as const,
}
export function verifyRevision(context: ResourceContext, revision: ResourceRevision) {
  if (revision.institution_id !== context.institutionId) {
    throw new ResourceApiError(403, 'Resource scope changed.', undefined, 'SCOPE_MISMATCH')
  }
  return revision
}
export function resourceListOptions(context: ResourceContext, view: ResourceView, offset: number) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    queryKey: resourceKeys.list(context.identity, view, offset),
    queryFn: async ({ signal }) => {
      const result = await listResources(context.accessToken, view, offset, signal)
      for (const row of result.items) if ('revision_id' in row) verifyRevision(context, row)
      return result
    },
  })
}
export function resourceRevisionOptions(context: ResourceContext, id: string) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    // Review decisions always refresh on opening; never approve cached state blindly.
    staleTime: 0,
    refetchOnMount: 'always',
    queryKey: resourceKeys.revision(context.identity, id),
    queryFn: async ({ signal }) => verifyRevision(context, await getRevision(context.accessToken, id, signal)),
  })
}
export function resourceSourceOptions(context: ResourceContext, id: string) {
  return queryOptions({
    ...NAVIGATION_QUERY_POLICY,
    staleTime: 0,
    queryKey: resourceKeys.source(context.identity, id),
    queryFn: ({ signal }) => getResource(context.accessToken, id, signal),
  })
}
export function accessDenied(error: unknown) {
  return error instanceof ResourceApiError && [401, 403].includes(error.status)
}
