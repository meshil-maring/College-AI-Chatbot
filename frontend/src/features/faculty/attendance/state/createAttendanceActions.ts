import {
  commitFacultyAttendanceImport,
  markFacultyAttendance,
  uploadFacultyAttendance,
} from '../../../../services/faculty/facultyAttendanceApi.ts'
import type { AttendanceState } from './useAttendanceState.ts'

export function createAttendanceActions(state: AttendanceState) {
  const {
    accessToken,
    statuses,
    setStatuses,
    sessionDate,
    review,
    setReview,
    setPendingFile,
    setMarkOpen,
    setUploadStep,
    setUploadSuccess,
    setAiConfirmationFile,
    setSaving,
    setMessage,
    setError,
    setReloadKey,
    selected,
    sectionUnavailable,
    rosterIncomplete,
    refreshSection,
    canManage,
    scopeRef,
    filteredRoster,
  } = state

  function exportAttendance() {
    if (rosterIncomplete || sectionUnavailable) return
    const escape = (value: string | number | null) => {
      const text = String(value ?? '')
      return `"${(/^[\s]*[=+\-@]/.test(text) ? "'" : '') + text.replaceAll('"', '""')}"`
    }
    const csv = [
      ['register_number', 'student_name', 'attendance_percentage', 'records'],
      ...filteredRoster.map((row) => [
        row.register_number,
        row.student_name,
        row.attendance_percentage ?? null,
        row.record_count ?? 0,
      ]),
    ]
      .map((row) => row.map(escape).join(','))
      .join('\r\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'attendance.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  function onFileSelected(file: File | undefined) {
    if (!file) return
    if (file.size > 10 * 1024 * 1024) {
      setError('The file exceeds the 10 MB limit.')
      return
    }
    const extension = file.name.toLowerCase().split('.').pop()
    if (!['csv', 'xls', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'webp'].includes(extension ?? '')) {
      setError('Choose a CSV, Excel, PDF, JPG, JPEG, PNG, or WEBP file.')
      return
    }
    setPendingFile(file)
    setUploadStep(1)
    setUploadSuccess(false)
    setError(null)
  }

  async function processFile(file: File, aiConfirmed = false) {
    if (!selected || !canManage) return
    const expectedScope = selected.section_id
    setError(null)
    setMessage(null)
    setReview(null)
    setSaving(true)
    setUploadStep(2)
    try {
      const result = await uploadFacultyAttendance(
        accessToken,
        selected.section_id,
        selected.semester_id,
        file,
        aiConfirmed,
      )
      if (scopeRef.current !== expectedScope) return
      setReview({ import_id: result.import_id, status: 'VALIDATED', summary: result.summary, rows: result.rows })
      setPendingFile(null)
      setUploadStep(2)
    } catch (cause: unknown) {
      if (scopeRef.current !== expectedScope) return
      const code = cause && typeof cause === 'object' && 'code' in cause ? (cause as { code?: string }).code : undefined
      if (code === 'AI_CONFIRMATION_REQUIRED') {
        setAiConfirmationFile(file)
        setError('AI_CONFIRMATION_REQUIRED')
        setUploadStep(1)
      } else {
        setError(
          cause instanceof Error ? cause.message : 'The file could not be processed. Check the format and try again.',
        )
        setUploadStep(1)
      }
    } finally {
      setSaving(false)
    }
  }

  async function saveAttendance() {
    if (!selected || !canManage || rosterIncomplete || sectionUnavailable || Object.keys(statuses).length === 0) return
    if (Object.keys(statuses).length > 500) {
      setError('Submit at most 500 marked students at a time.')
      return
    }
    setSaving(true)
    setError(null)
    setMessage(null)
    try {
      const result = await markFacultyAttendance(accessToken, selected.section_id, sessionDate, statuses)
      setMessage(`${result.record_count} attendance records saved.`)
      setMarkOpen(false)
      setStatuses({})
      void refreshSection(selected.section_id)
      setReloadKey((key) => key + 1)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Attendance could not be saved. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  async function commit() {
    if (!review || !canManage || !selected) return
    setSaving(true)
    setError(null)
    try {
      await commitFacultyAttendanceImport(accessToken, review.import_id)
      setUploadStep(4)
      setUploadSuccess(true)
      setMessage('Attendance imported successfully.')
      void refreshSection(selected.section_id)
      setReloadKey((key) => key + 1)
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'Import could not be committed. Please review the file and try again.',
      )
    } finally {
      setSaving(false)
    }
  }

  function downloadValidationErrors() {
    if (!review) return
    const failedRows = review.rows.filter((row) => row.errors.length > 0)
    if (failedRows.length === 0) return
    const csv = [
      'row_number,register_number,student_name,errors',
      ...failedRows.map((row) =>
        [
          row.row_number,
          row.normalized_data.register_number ?? '',
          row.normalized_data.student_name ?? '',
          row.errors.join('; '),
        ]
          .map(
            (value) =>
              `"${(/^[\s]*[=+\-@]/.test(String(value)) ? "'" + String(value) : String(value)).replaceAll('"', '""')}"`,
          )
          .join(','),
      ),
    ].join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'attendance-validation-errors.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }
  return { exportAttendance, onFileSelected, processFile, saveAttendance, commit, downloadValidationErrors }
}
