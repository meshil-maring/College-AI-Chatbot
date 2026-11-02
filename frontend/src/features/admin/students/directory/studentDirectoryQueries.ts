import { queryOptions } from '@tanstack/react-query'
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
  })
}
