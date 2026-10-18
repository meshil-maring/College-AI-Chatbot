/** Phase 6.16 — shared TanStack Query primitive for student server state. */

import { useQuery } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useId, useRef, useState } from 'react'
import { queryClient } from '../../lib/queryClient.ts'
import { useAuth } from '../auth/AuthProvider.tsx'
import { StudentApiError } from '../../services/studentApi.ts'

export type SectionStatus = 'idle' | 'loading' | 'loaded' | 'error'

export interface SectionState<T> {
  readonly status: SectionStatus
  readonly data: T | null
  readonly error: string | null
}

export interface StudentResourceState<T> extends SectionState<T> {
  readonly reload: () => void
  readonly errorCode?: string | null
}

let nextStudentQueryScope = 0

/** Let the mounted shell replace its views when a data endpoint denies access. */
export type StudentAccessDenial = 'STUDENT_NOT_APPROVED' | 'STUDENT_INACTIVE' | 'ACCOUNT_INACTIVE'
export const StudentAccessContext = createContext<((code: StudentAccessDenial) => void) | null>(null)

/** Load one authenticated student resource through TanStack Query. */
export function useStudentResource<T>(
  loader: (accessToken: string) => Promise<T>,
  errorMessage: string,
  watchKey = '',
  resourceKey = 'resource',
): StudentResourceState<T> {
  const { accessToken } = useAuth()
  const reportAccessDenial = useContext(StudentAccessContext)
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

  const errorCode = query.error instanceof StudentApiError ? query.error.code : null
  useEffect(() => {
    if (query.isError && query.error instanceof StudentApiError && query.error.status === 403 && (
      errorCode === 'STUDENT_NOT_APPROVED' || errorCode === 'STUDENT_INACTIVE' || errorCode === 'ACCOUNT_INACTIVE'
    )) reportAccessDenial?.(errorCode)
  }, [query.isError, query.error, errorCode, reportAccessDenial])

  if (accessToken === null) {
    return { status: 'idle', data: null, error: null, reload: () => undefined }
  }

  const loading = query.isPending || query.isFetching
  const accessMessage = errorCode === 'STUDENT_INACTIVE' || errorCode === 'ACCOUNT_INACTIVE'
    ? 'Your account is inactive. Contact your institution administrator for help with access.'
    : errorCode === 'STUDENT_NOT_APPROVED'
      ? 'Your account is not approved for student access. Contact your institution administrator for help with your approval status.'
      : errorMessage
  return {
    status: loading ? 'loading' : query.isError ? 'error' : 'loaded',
    data: loading ? null : query.data ?? null,
    error: query.isError ? accessMessage : null,
    errorCode: query.isError ? errorCode : null,
    reload: () => { void query.refetch() },
  }
}
