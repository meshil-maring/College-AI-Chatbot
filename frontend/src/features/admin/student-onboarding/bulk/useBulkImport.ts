import { useState } from 'react'
import type { StudentOnboardingBulkResult } from '../../../../types/admin/students.ts'
import { createStudentInvitationsBulk } from '../../../../services/admin/students.ts'
import { refreshStudentInvitations } from '../invitations/studentInvitationQueries.ts'
import { parseStudentFile, validateStudentRows, type StudentImportRow } from './studentImport.ts'

type EditableField = 'student_name' | 'register_number' | 'university_roll_number' | 'email'

/** Placement → upload → validate → results state for a spreadsheet of students. */
export function useBulkImport(accessToken: string, identity: string) {
  const [sectionId, setSectionId] = useState('')
  const [step, setStep] = useState(0)
  const [rows, setRows] = useState<StudentImportRow[]>([])
  const [fileName, setFileName] = useState('')
  const [fileError, setFileError] = useState('')
  const [results, setResults] = useState<StudentOnboardingBulkResult[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const readyRows = rows.filter((row) => row.errors.length === 0)

  async function upload(file?: File) {
    if (!file) return
    setFileError('')
    setResults([])
    try {
      setRows(await parseStudentFile(file))
      setFileName(file.name)
      setStep(1)
    } catch (reason) {
      setRows([])
      setFileName('')
      setFileError(reason instanceof Error ? reason.message : 'The selected file could not be read.')
    }
  }
  function editRow(sourceRow: number, field: EditableField, value: string) {
    setRows((current) =>
      validateStudentRows(current.map((row) => (row.sourceRow === sourceRow ? { ...row, [field]: value } : row))),
    )
  }
  function removeRow(sourceRow: number) {
    setRows((current) => validateStudentRows(current.filter((row) => row.sourceRow !== sourceRow)))
  }

  async function submit() {
    if (!sectionId || !readyRows.length) return
    setBusy(true)
    setError('')
    try {
      const result = await createStudentInvitationsBulk(
        accessToken,
        sectionId,
        readyRows.map(({ sourceRow, errors: _errors, ...identityRow }) => ({ ...identityRow, source_row: sourceRow })),
      )
      setResults((current) => {
        const latest = new Map(current.map((item) => [item.row, item]))
        result.rows.forEach(({ row, status, delivery_status, message }) => {
          latest.set(row, { row, status, delivery_status, message })
        })
        return [...latest.values()].sort((left, right) => left.row - right.row)
      })
      const failedRows = new Set(result.rows.filter((item) => item.status !== 'created').map((item) => item.row))
      setRows((current) => current.filter((row) => row.errors.length > 0 || failedRows.has(row.sourceRow)))
      setStep(3)
      refreshStudentInvitations(identity)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Bulk invitations could not be created.')
    } finally {
      setBusy(false)
    }
  }

  function reset() {
    setRows([])
    setResults([])
    setFileName('')
    setFileError('')
    setError('')
    setStep(1)
  }

  return {
    sectionId,
    setSectionId,
    step,
    setStep,
    rows,
    readyRows,
    issueRows: rows.length - readyRows.length,
    fileName,
    fileError,
    results,
    error,
    busy,
    upload,
    editRow,
    removeRow,
    submit,
    reset,
  }
}

export type BulkImport = ReturnType<typeof useBulkImport>
