import { useEffect, useMemo } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { useApiQuery } from '../../hooks/useApiQuery.ts'
import { NAVIGATION_QUERY_POLICY, queryClient } from '../../lib/queryClient.ts'
import {
  getFacultyAttendanceAssignments,
  getFacultyAttendanceOverview,
  getFacultyAttendanceStudents,
  type FacultyAttendanceAssignment,
} from '../../services/facultyAttendanceApi.ts'

const EMPTY_ASSIGNMENTS: FacultyAttendanceAssignment[] = []
const CACHE = { cache: 'navigation' } as const

export const facultyAttendanceKeys = {
  all: (token: string) => ['faculty', 'attendance', token] as const,
  assignments: (token: string, scope: string) => [...facultyAttendanceKeys.all(token), scope, 'assignments'] as const,
  section: (token: string, scope: string, sectionId?: string) => [...facultyAttendanceKeys.all(token), scope, 'section', sectionId] as const,
}

export function useFacultyAttendanceData(token: string, scope: string, assignmentId: string) {
  const assignmentsQuery = useApiQuery(
    facultyAttendanceKeys.assignments(token, scope),
    () => getFacultyAttendanceAssignments(token),
    true,
    CACHE,
  )
  const assignments = assignmentsQuery.isError ? EMPTY_ASSIGNMENTS : assignmentsQuery.data ?? EMPTY_ASSIGNMENTS
  const selected = assignments.find((assignment) => assignment.assignment_id === assignmentId) ?? assignments[0]
  const sectionId = selected?.section_id
  const sectionKey = facultyAttendanceKeys.section(token, scope, sectionId)
  const overviewQuery = useApiQuery(
    [...sectionKey, 'overview'],
    () => getFacultyAttendanceOverview(token, sectionId!),
    !!selected,
    CACHE,
  )
  const studentsQuery = useInfiniteQuery({
    queryKey: [...sectionKey, 'students'],
    queryFn: ({ pageParam }) => getFacultyAttendanceStudents(token, sectionId!, new URLSearchParams({
      limit: '500', offset: String(pageParam),
    })),
    initialPageParam: 0,
    getNextPageParam: (lastPage, _pages, offset) => {
      const next = offset + lastPage.items.length
      return lastPage.items.length > 0 && next < lastPage.total ? next : undefined
    },
    enabled: !!selected,
    retry: false,
    ...NAVIGATION_QUERY_POLICY,
  }, queryClient)

  const sectionUnavailable = overviewQuery.isError || studentsQuery.isError
  const { hasNextPage, isFetching, fetchNextPage } = studentsQuery
  useEffect(() => {
    // Show the first page immediately, then fill the cache for filters and export.
    if (sectionId && hasNextPage && !isFetching && !sectionUnavailable) void fetchNextPage({ cancelRefetch: false })
  }, [sectionId, hasNextPage, isFetching, sectionUnavailable, fetchNextPage])

  useEffect(() => {
    const refresh = () => {
      void queryClient.refetchQueries({ queryKey: facultyAttendanceKeys.all(token), type: 'active', stale: true }, { cancelRefetch: false })
    }
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [token])

  // A rejected read must hide cached records, including a revoked assignment.
  const roster = useMemo(() => sectionUnavailable ? [] : studentsQuery.data?.pages.flatMap((page) => page.items) ?? [],
    [sectionUnavailable, studentsQuery.data])
  const overview = sectionUnavailable ? null : overviewQuery.data ?? null
  const rosterIncomplete = !!selected && (studentsQuery.isPending || studentsQuery.hasNextPage)

  function refreshSection(id: string) {
    return queryClient.invalidateQueries({ queryKey: facultyAttendanceKeys.section(token, scope, id) })
  }

  function retry() {
    return queryClient.invalidateQueries({ queryKey: facultyAttendanceKeys.all(token) })
  }

  return { assignments, selected, roster, overview, assignmentsQuery, overviewQuery, studentsQuery,
    sectionUnavailable, rosterIncomplete, refreshSection, retry }
}
