/** Phase 6.16 — shared TanStack Query primitive for student server state. */

import { useQuery } from '@tanstack/react-query'
import { useId, useRef, useState } from 'react'
import { queryClient } from '../../lib/queryClient.ts'
import { useAuth } from '../auth/AuthProvider.tsx'

export type SectionStatus = 'idle' | 'loading' | 'loaded' | 'error'

export interface SectionState<T> {
  readonly status: SectionStatus
  readonly data: T | null
  readonly error: string | null
}

export interface StudentResourceState<T> extends SectionState<T> {
  readonly reload: () => void
}

let nextStudentQueryScope = 0

/** Load one authenticated student resource through TanStack Query. */
export function useStudentResource<T>(
  loader: (accessToken: string) => Promise<T>,
  errorMessage: string,
  watchKey = '',
  resourceKey = 'resource',
): StudentResourceState<T> {
  const { accessToken } = useAuth()
  const instanceId = useId()
  const [scope] = useState(() => ++nextStudentQueryScope)
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  const query = useQuery<T, Error>(
    {
      queryKey: ['student', resourceKey, accessToken, watchKey, instanceId, scope],
      queryFn: () => loaderRef.current(accessToken as string),
      enabled: accessToken !== null,
      retry: false,
      gcTime: 0,
      refetchOnMount: 'always',
    },
    queryClient,
  )

  if (accessToken === null) {
    return { status: 'idle', data: null, error: null, reload: () => undefined }
  }

  const loading = query.isPending || query.isFetching
  return {
    status: loading ? 'loading' : query.isError ? 'error' : 'loaded',
    data: loading ? null : query.data ?? null,
    error: query.isError ? errorMessage : null,
    reload: () => { void query.refetch() },
  }
}
