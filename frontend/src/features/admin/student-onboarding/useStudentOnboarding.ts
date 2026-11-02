import { useState } from 'react'
import { useApiQuery } from '../../../hooks/useApiQuery.ts'
import { queryClient } from '../../../lib/queryClient.ts'
import type { StructureCatalogue } from '../../../types/academicStructure.ts'
import type { StudentInvitationInput, StudentOnboardingBulkResult } from '../../../types/admin/students.ts'
import {
  createStudentInvitation,
  createStudentInvitationsBulk,
  listStudentInvitations,
  reassignStudentInvitation,
  resendStudentInvitation,
} from '../../../services/admin/students.ts'
import { getAcademicStructure } from '../../../services/admin/academicStructure.ts'
import { parseStudentFile, validateStudentRows, type StudentImportRow } from './studentImport.ts'
import { useStudentIdentityConflictReview } from './registration/useStudentIdentityConflictReview.ts'

const invitationKey = (identity: string) => ['admin', identity, 'student-onboarding-invitations'] as const
const structureKey = (identity: string) => ['admin', identity, 'student-onboarding-structure'] as const

function emptyStudent(): StudentInvitationInput {
  return { student_name: '', register_number: '', university_roll_number: null, email: '' }
}

export function useStudentOnboarding(
  accessToken: string,
  identity: string,
  canManage: boolean,
  initialMode: 'single' | 'bulk' = 'single',
) {
  const invitations = useApiQuery(invitationKey(identity), () => listStudentInvitations(accessToken), canManage, {
    cache: 'navigation',
  })
  const conflictReview = useStudentIdentityConflictReview(accessToken)
  const structure = useApiQuery<StructureCatalogue>(
    structureKey(identity),
    () => getAcademicStructure(accessToken),
    canManage,
    { cache: 'navigation' },
  )
  const [mode, setMode] = useState<'single' | 'bulk'>(initialMode)
  const [sectionId, setSectionId] = useState('')
  const [singleStep, setSingleStep] = useState(0)
  const [bulkStep, setBulkStep] = useState(0)
  const [student, setStudent] = useState<StudentInvitationInput>(emptyStudent)
  const [singleDelivery, setSingleDelivery] = useState<'sent' | 'failed'>('sent')
  const [rows, setRows] = useState<StudentImportRow[]>([])
  const [fileName, setFileName] = useState('')
  const [fileError, setFileError] = useState('')
  const [bulkResults, setBulkResults] = useState<StudentOnboardingBulkResult[]>([])
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const records = structure.data?.records
  const cohorts = records?.admission_cohorts ?? []
  const sections = (records?.academic_sections ?? []).filter((section) => {
    const cohort = cohorts.find((item) => item.admission_cohort_id === section.admission_cohort_id)
    return section.is_active && cohort?.status === 'active'
  })
  const selectedSection = sections.find((section) => section.academic_section_id === sectionId)
  const selectedCohort = cohorts.find((cohort) => cohort.admission_cohort_id === selectedSection?.admission_cohort_id)
  const selectedLabel =
    selectedSection && selectedCohort
      ? `${selectedCohort.code} · ${selectedCohort.name} · ${selectedSection.code} ${selectedSection.name}`
      : ''
  const readyRows = rows.filter((row) => row.errors.length === 0)
  const issueRows = rows.length - readyRows.length

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: invitationKey(identity) })
  }
  function changeMode(next: 'single' | 'bulk') {
    setMode(next)
    setError('')
    setNotice('')
  }
  function setField(field: keyof StudentInvitationInput, value: string) {
    setStudent((current) => ({ ...current, [field]: value }))
    conflictReview.clear()
  }
  async function upload(file?: File) {
    if (!file) return
    setFileError('')
    setBulkResults([])
    try {
      setRows(await parseStudentFile(file))
      setFileName(file.name)
      setBulkStep(1)
    } catch (reason) {
      setRows([])
      setFileName('')
      setFileError(reason instanceof Error ? reason.message : 'The selected file could not be read.')
    }
  }
  function editRow(
    sourceRow: number,
    field: 'student_name' | 'register_number' | 'university_roll_number' | 'email',
    value: string,
  ) {
    setRows((current) =>
      validateStudentRows(current.map((row) => (row.sourceRow === sourceRow ? { ...row, [field]: value } : row))),
    )
  }
  function removeRow(sourceRow: number) {
    setRows((current) => validateStudentRows(current.filter((row) => row.sourceRow !== sourceRow)))
  }

  async function submitSingle() {
    if (!sectionId) return
    setBusy(true)
    setError('')
    conflictReview.clear()
    try {
      const result = await createStudentInvitation(accessToken, sectionId, {
        ...student,
        email: student.email.trim().toLowerCase(),
        student_name: student.student_name.trim(),
        register_number: student.register_number.trim(),
        university_roll_number: student.university_roll_number?.trim() || null,
      })
      setSingleDelivery(result.delivery_status)
      setSingleStep(3)
      refresh()
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Student invitation could not be created.'
      setError(message)
      if (message.toLowerCase().includes('already in use')) await conflictReview.lookup(student)
    } finally {
      setBusy(false)
    }
  }

  async function submitBulk() {
    if (!sectionId) return
    const ready = rows.filter((row) => !row.errors.length)
    if (!ready.length) return
    setBusy(true)
    setError('')
    try {
      const result = await createStudentInvitationsBulk(
        accessToken,
        sectionId,
        ready.map(({ sourceRow, errors: _errors, ...identityRow }) => ({ ...identityRow, source_row: sourceRow })),
      )
      setBulkResults((current) => {
        const latest = new Map(current.map((item) => [item.row, item]))
        result.rows.forEach(({ row, status, delivery_status, message }) => {
          latest.set(row, { row, status, delivery_status, message })
        })
        return [...latest.values()].sort((left, right) => left.row - right.row)
      })
      const failedRows = new Set(result.rows.filter((item) => item.status !== 'created').map((item) => item.row))
      setRows((current) => current.filter((row) => row.errors.length > 0 || failedRows.has(row.sourceRow)))
      setBulkStep(3)
      refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Bulk invitations could not be created.')
    } finally {
      setBusy(false)
    }
  }

  async function resend(invitationId: string) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await resendStudentInvitation(accessToken, invitationId)
      setNotice(result.delivery_message)
      refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'A new setup link could not be sent.')
    } finally {
      setBusy(false)
    }
  }
  async function reassign(invitationId: string) {
    if (!sectionId) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await reassignStudentInvitation(accessToken, invitationId, sectionId)
      setNotice('Invitation assigned to the selected active section.')
      refresh()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Section assignment could not be updated.')
    } finally {
      setBusy(false)
    }
  }
  function resetSingle() {
    setStudent(emptyStudent())
    setSingleStep(0)
    setSectionId('')
    conflictReview.clear()
  }
  function resetBulk() {
    setRows([])
    setBulkResults([])
    setFileName('')
    setFileError('')
    setBulkStep(1)
  }

  return {
    invitations,
    structure,
    mode,
    sectionId,
    setSectionId,
    singleStep,
    setSingleStep,
    bulkStep,
    setBulkStep,
    student,
    singleDelivery,
    rows,
    fileName,
    fileError,
    bulkResults,
    notice,
    error,
    identityReview: conflictReview.identityReview,
    identityReviewError: conflictReview.identityReviewError,
    identityReviewing: conflictReview.identityReviewing,
    busy,
    cohorts,
    sections,
    selectedSection,
    selectedCohort,
    selectedLabel,
    readyRows,
    issueRows,
    changeMode,
    setField,
    upload,
    editRow,
    removeRow,
    submitSingle,
    submitBulk,
    resend,
    reassign,
    resetSingle,
    resetBulk,
  }
}
