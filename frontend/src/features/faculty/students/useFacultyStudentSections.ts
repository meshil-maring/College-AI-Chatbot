import { useQuery } from '@tanstack/react-query'
import { useBrowserLocation } from '../../../lib/navigation.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import { getFacultyAttendanceAssignments } from '../../../services/faculty/facultyAttendanceApi.ts'
import { resolveFacultyRoute } from '../workspace/facultyRoutes.ts'

/** Share section selection between the Students sidebar and its current page. */
export function useFacultyStudentSections(accessToken: string, scopeVersion = '') {
  const { pathname, search } = useBrowserLocation()
  const sectionId = new URLSearchParams(search).get('section_id') ?? ''
  const page = resolveFacultyRoute(pathname)?.studentPage ?? 'roster'
  const assignmentsQuery = useQuery({
    queryKey: ['faculty', 'students', accessToken, scopeVersion, 'sections'],
    queryFn: () => getFacultyAttendanceAssignments(accessToken),
  }, queryClient)
  const assignments = assignmentsQuery.isError ? [] : assignmentsQuery.data ?? []
  const selected = sectionId ? assignments.find((item) => item.section_id === sectionId)
    : page === 'register' ? assignments.find((item) => item.can_manage) : assignments[0]

  return { page, sectionId, assignmentsQuery, assignments, selected }
}
