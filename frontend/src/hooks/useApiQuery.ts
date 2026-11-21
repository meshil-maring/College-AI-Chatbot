import {
  useMutation,
  useQuery,
  type QueryKey,
  type UseMutationOptions,
  type UseQueryResult,
} from '@tanstack/react-query'
import { useId, useState } from 'react'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../lib/queryClient.ts'

let nextQueryScope = 0

/**
 * Small app-level adapter that keeps feature code on TanStack Query.
 *
 * Reads are cached by default (`NAVIGATION_QUERY_POLICY`): returning to a page
 * shows the saved data at once, and only data older than a minute is refreshed
 * in the background. The key must therefore name everything the response
 * depends on, including the signed-in identity or token; the auth provider
 * clears these cached reads whenever the session or token changes.
 *
 * Use `cache: 'none'` for reads that must never be reused, such as an
 * authorization check or a one-time invitation token.
 */
export function useApiQuery<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  enabled = true,
  options: { cache?: 'navigation' | 'none' } = {},
): UseQueryResult<T, unknown> {
  const instanceId = useId()
  const [scope] = useState(() => ++nextQueryScope)
  const retainOnNavigation = options.cache !== 'none'
  return useQuery(
    {
      queryKey: retainOnNavigation ? queryKey : [...queryKey, instanceId, scope],
      queryFn,
      enabled,
      retry: false,
      ...(retainOnNavigation ? NAVIGATION_QUERY_POLICY : { refetchOnMount: 'always' as const, gcTime: 0 }),
    },
    queryClient,
  )
}

export function useApiMutation<TData, TVariables>(
  options: Omit<UseMutationOptions<TData, unknown, TVariables>, 'retry'>,
) {
  return useMutation({ ...options, retry: false }, queryClient)
}
