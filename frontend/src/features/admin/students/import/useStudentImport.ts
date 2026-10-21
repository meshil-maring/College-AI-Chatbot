import { useEffect, useRef, useState } from 'react'
import type { Student } from '../../../../types/admin.ts'
import {
  downloadCsv,
  IMPORT_COLUMNS,
  readStudentFile,
  validateStudents,
  type ImportStudent,
  type ReviewStatus,
  type ReviewStudent,
} from '../studentImport.ts'
import type { StudentImportOutcome, StudentRegistrationImport } from './importTypes.ts'
import { PAGE_SIZE, statuses } from './importUi.ts'

export function useStudentImport({
  students,
  directoryReady,
  onBack,
  registration,
  embedded = false,
}: {
  students: Student[]
  directoryReady: boolean
  onBack: () => void
  registration?: StudentRegistrationImport
  embedded?: boolean
}) {
  const [upload, setUpload] = useState<{
    name: string
    time: Date
    rows: ImportStudent[]
  } | null>(null)
  const [stage, setStage] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<ReviewStatus | 'all'>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [onlySelected, setOnlySelected] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [reportMenu, setReportMenu] = useState(false)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const request = useRef(0)
  const active = useRef(false)
  const importing = useRef(false)
  const [outcomes, setOutcomes] = useState<StudentImportOutcome[]>([])
  const [importProgress, setImportProgress] = useState({ completed: 0, total: 0 })
  const onBusyChange = registration?.onBusyChange
  useEffect(() => {
    active.current = true
    return () => {
      active.current = false
      request.current++
    }
  }, [])
  useEffect(() => {
    onBusyChange?.(busy)
  }, [busy, onBusyChange])
  const reviewed = registration
    ? registration.reviewRows(upload?.rows ?? [])
    : validateStudents(upload?.rows ?? [], students)
  const columns = registration ? IMPORT_COLUMNS.slice(0, 4) : IMPORT_COLUMNS
  const counts = Object.fromEntries(
    Object.keys(statuses).map((status) => [status, reviewed.filter((row) => row.status === status).length]),
  ) as Record<ReviewStatus, number>
  const validSelected = reviewed.filter((row) => row.status === 'valid' && selected.has(row.row))
  const filtered = reviewed.filter(
    (row) =>
      (filter === 'all' || row.status === filter) &&
      (!onlySelected || selected.has(row.row)) &&
      `${row.name} ${row.registerNumber} ${row.rollNumber} ${row.email}`
        .toLowerCase()
        .includes(search.toLowerCase().trim()),
  )
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const selectable = visible.filter((row) => row.status === 'valid')
  const allSelected = selectable.length > 0 && selectable.every((row) => selected.has(row.row))

  async function choose(file: File) {
    const id = ++request.current
    setBusy(true)
    setError(null)
    try {
      const rows = await (registration ? registration.readFile(file) : readStudentFile(file))
      if (id !== request.current) return
      setUpload({ name: file.name, time: new Date(), rows })
      registration?.onReset?.()
      setStage(1)
      setOutcomes([])
      setPage(1)
      setFilter('all')
      setSearch('')
      setOnlySelected(false)
      setSelected(
        new Set(
          (registration ? registration.reviewRows(rows) : validateStudents(rows, students))
            .filter((row) => row.status === 'valid')
            .map((row) => row.row),
        ),
      )
    } catch (cause) {
      if (id === request.current)
        setError(cause instanceof Error ? cause.message : 'The file could not be read. Check its format and try again.')
    } finally {
      if (id === request.current) setBusy(false)
    }
  }

  async function importSelected(rows: ReviewStudent[]) {
    if (!registration || busy || importing.current || !directoryReady || !rows.length) return
    importing.current = true
    setBusy(true)
    setError(null)
    setImportProgress({ completed: 0, total: rows.length })
    try {
      const result = await registration.importRows(rows, (completed) => {
        if (active.current) setImportProgress({ completed, total: rows.length })
      })
      if (!active.current) return
      setOutcomes((previous) =>
        [...previous.filter((old) => !result.some((item) => item.row === old.row)), ...result].sort(
          (a, b) => a.row - b.row,
        ),
      )
      setStage(3)
    } catch (cause) {
      if (active.current)
        setError(cause instanceof Error ? cause.message : 'Registration could not be completed. Please try again.')
    } finally {
      importing.current = false
      if (active.current) setBusy(false)
    }
  }

  function toggle(row: number) {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(row)) next.delete(row)
      else next.add(row)
      return next
    })
  }
  function downloadReport(rows: ReviewStudent[]) {
    downloadCsv('student-validation-report.csv', [
      [
        ...columns,
        'file_row',
        'validation_status',
        'validation_message',
        ...(registration ? ['registration_result', 'registration_message'] : []),
      ],
      ...rows.map((row) => [
        row.name,
        row.registerNumber,
        row.rollNumber,
        row.email,
        ...(registration ? [] : [row.attendance]),
        row.row,
        row.status,
        row.message,
        ...(registration
          ? [
              outcomes.find((result) => result.row === row.row)?.status ?? '',
              outcomes.find((result) => result.row === row.row)?.message ?? '',
            ]
          : []),
      ]),
    ])
  }
  function report() {
    downloadReport(reviewed)
  }
  function problemsReport() {
    downloadReport(
      reviewed.filter(
        (row) =>
          row.status !== 'valid' || outcomes.some((result) => result.row === row.row && result.status === 'failed'),
      ),
    )
  }

  return {
    directoryReady,
    onBack,
    registration,
    embedded,
    upload,
    setUpload,
    stage,
    setStage,
    busy,
    error,
    filter,
    setFilter,
    search,
    setSearch,
    setPage,
    selected,
    setSelected,
    onlySelected,
    setOnlySelected,
    showFilters,
    setShowFilters,
    reportMenu,
    setReportMenu,
    dragging,
    setDragging,
    fileInput,
    importing,
    outcomes,
    importProgress,
    reviewed,
    columns,
    counts,
    validSelected,
    filtered,
    totalPages,
    currentPage,
    visible,
    selectable,
    allSelected,
    choose,
    importSelected,
    toggle,
    report,
    problemsReport,
  }
}

export type StudentImportModel = ReturnType<typeof useStudentImport>

export { PAGE_SIZE, statuses, steps } from './importUi.ts'

export type { StudentImportOutcome, StudentRegistrationImport } from './importTypes.ts'
