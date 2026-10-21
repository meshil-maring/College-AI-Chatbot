import { useEffect, useMemo, useRef, useState } from 'react'
import {
  type FacultyAttendanceImportReview,
  type FacultyAttendanceRosterRow,
} from '../../../../services/faculty/facultyAttendanceApi.ts'
import { useFacultyAttendanceData } from './useFacultyAttendanceData.ts'
import { importedStats, PAGE_SIZE } from '../shared/AttendanceWorkspaceUi.tsx'
import {
  type AttendanceTab,
  type AttendanceValue,
  type FacultyAttendanceProps,
  type UploadStep,
} from './workspaceTypes.ts'
export function useAttendanceState({
  accessToken,
  actionRequest,
  onNavigateAssignments,
  scopeVersion = '',
}: FacultyAttendanceProps) {
  const [assignmentId, setAssignmentId] = useState('')
  const [sort, setSort] = useState('register_number')
  const [statuses, setStatuses] = useState<Record<string, AttendanceValue>>({})
  const [sessionDate, setSessionDate] = useState(() => {
    const date = new Date()
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  })
  const [review, setReview] = useState<FacultyAttendanceImportReview | null>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [attendanceFilter, setAttendanceFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [tab, setTab] = useState<AttendanceTab>('students')
  const [profile, setProfile] = useState<FacultyAttendanceRosterRow | null>(null)
  const [markOpen, setMarkOpen] = useState(false)
  const [markPage, setMarkPage] = useState(0)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [uploadStep, setUploadStep] = useState<UploadStep>(1)
  const [uploadSuccess, setUploadSuccess] = useState(false)
  const [aiConfirmationFile, setAiConfirmationFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  const {
    assignments,
    selected,
    roster,
    overview,
    assignmentsQuery,
    overviewQuery,
    studentsQuery,
    sectionUnavailable,
    rosterIncomplete,
    refreshSection,
    retry,
  } = useFacultyAttendanceData(accessToken, scopeVersion, assignmentId)
  const rosterLoading = !!selected && studentsQuery.isPending
  const loadError = overviewQuery.error ?? studentsQuery.error
  const refreshing =
    (assignmentsQuery.isFetching && !assignmentsQuery.isPending) ||
    (overviewQuery.isFetching && !overviewQuery.isPending) ||
    (studentsQuery.isFetching && !studentsQuery.isPending && !studentsQuery.isFetchingNextPage)
  const canManage = selected?.can_manage === true
  const scopeRef = useRef(selected?.section_id)
  scopeRef.current = selected?.section_id

  useEffect(() => {
    setStatuses({})
    setMarkPage(0)
    setProfile(null)
    setMarkOpen(false)
    setUploadOpen(false)
    setReview(null)
    setPendingFile(null)
    setAiConfirmationFile(null)
  }, [selected?.section_id, scopeVersion, accessToken])
  useEffect(() => {
    if (sectionUnavailable) {
      setProfile(null)
      setMarkOpen(false)
      setStatuses({})
    }
  }, [sectionUnavailable])

  useEffect(() => {
    if (assignmentsQuery.isPending || !actionRequest || actionRequest.id === 0) return
    if (actionRequest.action === 'upload') {
      setUploadOpen(true)
      setUploadStep(1)
      setUploadSuccess(false)
      setError(null)
    } else if (actionRequest.action === 'mark') {
      setMarkOpen(true)
    } else if (actionRequest.action === 'history') {
      setTab('history')
    } else {
      setTab('students')
    }
  }, [actionRequest, assignmentsQuery.isPending])

  const filteredRoster = useMemo(() => {
    const query = search.trim().toLowerCase()
    return roster
      .filter((row) => {
        const stats = importedStats(row)
        const matchesQuery =
          !query ||
          [row.register_number, row.university_roll_number ?? '', row.student_name, row.email ?? ''].some((value) =>
            value.toLowerCase().includes(query),
          )
        const matchesStatus = statusFilter === 'all' || row.roster_status === statusFilter
        const matchesAttendance =
          attendanceFilter === 'all' ||
          (attendanceFilter === 'low'
            ? stats.percentage !== null && stats.percentage < 75
            : attendanceFilter === 'good'
              ? stats.percentage !== null && stats.percentage >= 75
              : stats.percentage === null)
        return matchesQuery && matchesStatus && matchesAttendance
      })
      .sort((a, b) =>
        sort === 'attendance'
          ? (a.attendance_percentage ?? -1) - (b.attendance_percentage ?? -1)
          : String(a[sort as 'register_number' | 'student_name']).localeCompare(
              String(b[sort as 'register_number' | 'student_name']),
            ),
      )
  }, [roster, search, statusFilter, attendanceFilter, sort])

  const totalPages = Math.max(1, Math.ceil(filteredRoster.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleRoster = filteredRoster.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  useEffect(() => {
    setPage(1)
  }, [selected?.section_id, search, statusFilter, attendanceFilter])

  const metrics = useMemo(() => {
    return {
      students: overview?.total_students ?? null,
      average: overview?.average_attendance ?? null,
      low: overview?.low_attendance_count ?? null,
      classes: overview?.session_count ?? null,
    }
  }, [overview])

  function resetFilters() {
    setSearch('')
    setStatusFilter('all')
    setAttendanceFilter('all')
    setPage(1)
  }

  return {
    accessToken,
    onNavigateAssignments,
    setAssignmentId,
    sort,
    setSort,
    statuses,
    setStatuses,
    sessionDate,
    setSessionDate,
    review,
    setReview,
    pendingFile,
    setPendingFile,
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    attendanceFilter,
    setAttendanceFilter,
    setPage,
    tab,
    setTab,
    profile,
    setProfile,
    markOpen,
    setMarkOpen,
    markPage,
    setMarkPage,
    uploadOpen,
    setUploadOpen,
    uploadStep,
    setUploadStep,
    uploadSuccess,
    setUploadSuccess,
    aiConfirmationFile,
    setAiConfirmationFile,
    dragging,
    setDragging,
    saving,
    setSaving,
    message,
    error,
    setError,
    reloadKey,
    assignments,
    selected,
    roster,
    overview,
    assignmentsQuery,
    overviewQuery,
    studentsQuery,
    sectionUnavailable,
    rosterIncomplete,
    retry,
    rosterLoading,
    loadError,
    refreshing,
    canManage,
    filteredRoster,
    totalPages,
    currentPage,
    visibleRoster,
    metrics,
    resetFilters,
    setMessage,
    setReloadKey,
    refreshSection,
    scopeRef,
  }
}

export type AttendanceState = ReturnType<typeof useAttendanceState>
