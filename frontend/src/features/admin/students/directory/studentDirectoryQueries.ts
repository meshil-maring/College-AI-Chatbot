import { queryOptions } from '@tanstack/react-query'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../../../lib/queryClient.ts'
import { getStudentDirectory } from '../../../../services/admin/students.ts'
import type { StudentDirectoryFilter } from '../../../../types/admin/students.ts'

export const STUDENT_DIRECTORY_PAGE_SIZE = 25

export interface StudentDirectoryQuery {
  search: string
  status: StudentDirectoryFilter
  programId: string
  page: number
}

export const studentDirectoryKeys = {
  all: ['admin', 'student-directory'] as const,
  page: (identity: string, query: StudentDirectoryQuery) => [...studentDirectoryKeys.all, identity, query] as const,
}

/**
 * Mark cached All Students pages as outdated after anything that changes
 * students elsewhere: registration, approval or a transfer. The visible page
 * refreshes now; others refresh when next opened.
 */
export function invalidateStudentDirectory(): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: studentDirectoryKeys.all })
}

export function studentDirectoryQueryOptions(accessToken: string, identity: string, query: StudentDirectoryQuery) {
  return queryOptions({
    queryKey: studentDirectoryKeys.page(identity, query),
    queryFn: () =>
      getStudentDirectory(accessToken, {
        search: query.search || undefined,
        status: query.status === 'all' ? undefined : query.status,
        programId: query.programId || undefined,
        limit: STUDENT_DIRECTORY_PAGE_SIZE,
        offset: (query.page - 1) * STUDENT_DIRECTORY_PAGE_SIZE,
      }),
    // Keep each viewed page so returning to the directory shows it at once.
    ...NAVIGATION_QUERY_POLICY,
  })
}
