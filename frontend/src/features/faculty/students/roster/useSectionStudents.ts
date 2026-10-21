import { useState } from 'react'
import { useApiQuery } from '../../../../hooks/useApiQuery.ts'
import { type FacultyAttendanceAssignment } from '../../../../services/faculty/facultyAttendanceApi.ts'
import type { ClassStudentRegistration } from '../../../../services/students/studentRegistrationApi.ts'
import type { StudentRegistrationMethod } from '../../../students/studentsNavigation.ts'
import { useStudentWorkspaceApi } from '../../../students/StudentWorkspaceContext.tsx'
import { PAGE_SIZE, useRosterStatusCount } from './rosterUi.tsx'
export function useSectionStudents({
  token,
  assignment,
  assignments,
  batchId,
  onClearBatch,
  onSectionChange,
  registrationOpen,
  waitingApproval,
  onRegister,
  onBack,
  registrationMethod,
  onRegistrationMethod,
  initialSearch,
}: {
  token: string
  assignment: FacultyAttendanceAssignment
  assignments: FacultyAttendanceAssignment[]
  batchId: string
  onClearBatch: () => void
  onSectionChange: (sectionId: string) => void
  registrationOpen: boolean
  waitingApproval: boolean
  onRegister: () => void
  onBack: () => void
  registrationMethod?: StudentRegistrationMethod
  onRegistrationMethod?: (method: StudentRegistrationMethod) => void
  initialSearch?: string
}) {
  const api = useStudentWorkspaceApi()
  const [filters, setFilters] = useState({
    search: initialSearch ?? '',
    registration: '',
    sort: 'register_number',
    batchId,
    page: 0,
  })
  const [draftSearch, setDraftSearch] = useState(initialSearch ?? '')
  const [studentId, setStudentId] = useState<string | null>(null)
  const [registrationMessage, setRegistrationMessage] = useState('')
  // Reset pagination before committing the new cohort, while retaining search and status.
  if (filters.batchId !== batchId) {
    setFilters({ ...filters, batchId, page: 0 })
    setStudentId(null)
  }
  // Status counts are declared before the roster query so their fetches always
  // start first — tests rely on the roster query being the latest call.
  const countsEnabled = !registrationOpen && !waitingApproval
  const activeCount = useRosterStatusCount(token, assignment.section_id, 'ACTIVE', countsEnabled, batchId)
  const pendingApprovalCount = useRosterStatusCount(
    token,
    assignment.section_id,
    'PENDING_APPROVAL',
    countsEnabled,
    batchId,
  )
  const unregisteredCount = useRosterStatusCount(token, assignment.section_id, 'UNREGISTERED', countsEnabled, batchId)
  const inactiveCount = useRosterStatusCount(token, assignment.section_id, 'INACTIVE', countsEnabled, batchId)
  const statusCounts = {
    ACTIVE: activeCount,
    PENDING_APPROVAL: pendingApprovalCount,
    UNREGISTERED: unregisteredCount,
    INACTIVE: inactiveCount,
  }
  const query = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String(filters.page * PAGE_SIZE),
    search: filters.search,
    sort: filters.sort,
  })
  if (batchId) query.set('batch_id', batchId)
  if (waitingApproval) query.set('registration', 'PENDING_APPROVAL')
  else if (filters.registration) query.set('registration', filters.registration)
  const studentsQuery = useApiQuery(
    [api.namespace, 'students', token, assignment.section_id, waitingApproval, batchId, filters],
    () => api.getStudents(token, assignment.section_id, query),
    !registrationOpen,
  )
  const result = studentsQuery.isError ? undefined : studentsQuery.data
  const totalPages = Math.max(1, Math.ceil((result?.total ?? 0) / PAGE_SIZE))
  const selectedStudent = result?.items.find((row) => row.roster_id === studentId)

  function updateFilters(next: Partial<typeof filters>) {
    setStudentId(null)
    setFilters((current) => ({ ...current, ...next, page: 0 }))
  }

  function registered(student: ClassStudentRegistration) {
    onBack()
    setRegistrationMessage(
      `${student.student_name} was registered in Section ${student.section_code}, batch ${student.batch_start_year}–${student.batch_end_year}. Subjects can be assigned later.`,
    )
    setDraftSearch('')
    updateFilters({ search: '', registration: '', sort: 'register_number' })
  }

  return {
    token,
    assignment,
    assignments,
    batchId,
    onClearBatch,
    onSectionChange,
    registrationOpen,
    waitingApproval,
    onRegister,
    onBack,
    registrationMethod,
    onRegistrationMethod,
    filters,
    setFilters,
    draftSearch,
    setDraftSearch,
    setStudentId,
    registrationMessage,
    setRegistrationMessage,
    statusCounts,
    studentsQuery,
    result,
    totalPages,
    selectedStudent,
    updateFilters,
    registered,
  }
}

export type SectionStudentsModel = ReturnType<typeof useSectionStudents>
