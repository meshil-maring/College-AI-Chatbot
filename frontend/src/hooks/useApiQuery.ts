import { useMutation, useQuery, type QueryKey, type UseMutationOptions, type UseQueryResult } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { queryClient } from '../lib/queryClient.ts'

let nextQueryScope = 0

/** Small app-level adapters that keep feature code on TanStack Query. */
export function useApiQuery<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  enabled = true,
): UseQueryResult<T, unknown> {
  const instanceId = useId()
  const [scope] = useState(() => ++nextQueryScope)
  return useQuery({ queryKey: [...queryKey, instanceId, scope], queryFn, enabled, retry: false, refetchOnMount: 'always', gcTime: 0 }, queryClient)
}

export function useApiMutation<TData, TVariables>(
  options: Omit<UseMutationOptions<TData, unknown, TVariables>, 'retry'>,
) {
  return useMutation({ ...options, retry: false }, queryClient)
}
