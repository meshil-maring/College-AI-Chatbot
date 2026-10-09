import { useMutation, useQuery, type QueryKey, type UseMutationOptions, type UseQueryResult } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../lib/queryClient.ts'

let nextQueryScope = 0

/** Small app-level adapters that keep feature code on TanStack Query. */
export function useApiQuery<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  enabled = true,
  options: { cache?: 'navigation' } = {},
): UseQueryResult<T, unknown> {
  const instanceId = useId()
  const [scope] = useState(() => ++nextQueryScope)
  const retainOnNavigation = options.cache === 'navigation'
  return useQuery({
    queryKey: retainOnNavigation ? queryKey : [...queryKey, instanceId, scope],
    queryFn, enabled, retry: false, refetchOnMount: 'always', gcTime: 0,
    ...(retainOnNavigation ? NAVIGATION_QUERY_POLICY : {}),
  }, queryClient)
}

export function useApiMutation<TData, TVariables>(
  options: Omit<UseMutationOptions<TData, unknown, TVariables>, 'retry'>,
) {
  return useMutation({ ...options, retry: false }, queryClient)
}
