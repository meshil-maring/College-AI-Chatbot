import { useState, type FormEvent } from 'react'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import type { AcademicSection, AdmissionCohort } from '../../../../types/academicStructure.ts'
import type {
  StudentDirectoryRow,
  StudentDirectoryUpdateInput,
  StudentProfileUpdateInput,
} from '../../../../types/admin/students.ts'
import './studentRecordDialog.css'

export default function StudentEditDialog({
  student,
  isInvitation,
  sections,
  cohorts,
  canManagePlacement,
  placementLoading,
  placementError,
  onClose,
  onSave,
}: {
  student: StudentDirectoryRow
  isInvitation: boolean
  sections: AcademicSection[]
  cohorts: AdmissionCohort[]
  canManagePlacement: boolean
  placementLoading: boolean
  placementError: string
  onClose: () => void
  onSave: (input: StudentDirectoryUpdateInput) => Promise<boolean>
}) {
  const ref = useWorkspaceDialog('.student-directory-header h1')
  const [name, setName] = useState(student.student_name)
  const [registerNumber, setRegisterNumber] = useState(student.register_number ?? '')
  const [rollNumber, setRollNumber] = useState(student.university_roll_number ?? '')
  const [email, setEmail] = useState(student.email ?? '')
  const [sectionId, setSectionId] = useState(student.academic_section_id ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const placementIdsMissing =
    Boolean(student.section_name || student.section_code) &&
    (!student.admission_cohort_id || !student.academic_section_id)
  const availableSections = sections.filter((section) => {
    const cohort = cohorts.find((item) => item.admission_cohort_id === section.admission_cohort_id)
    return (
      section.is_active &&
      cohort?.status === 'active' &&
      (!student.admission_cohort_id || cohort.admission_cohort_id === student.admission_cohort_id)
    )
  })

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const details: StudentProfileUpdateInput = {
        student_name: name.trim(),
        register_number: registerNumber.trim(),
        university_roll_number: rollNumber.trim() || null,
        academic_section_id:
          canManagePlacement && sectionId && sectionId !== student.academic_section_id ? sectionId : null,
      }
      const saved = await onSave(isInvitation ? { ...details, email: email.trim() } : details)
      if (saved) onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Student details could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <dialog
      ref={ref}
      className="student-record-dialog"
      aria-modal="true"
      aria-labelledby="student-edit-title"
      onCancel={(event) => {
        event.preventDefault()
        if (!saving) onClose()
      }}
    >
      <header>
        <div>
          <h2 id="student-edit-title">{isInvitation ? 'Edit invitation' : 'Edit student'}</h2>
          <p>
            {isInvitation
              ? 'Update the pending student details and academic placement.'
              : 'Update this student’s identity and current academic placement.'}
          </p>
        </div>
        <button type="button" aria-label="Close edit student" disabled={saving} onClick={onClose}>
          ×
        </button>
      </header>
      <form onSubmit={(event) => void submit(event)}>
        {error && (
          <p className="student-record-error" role="alert">
            {error}
          </p>
        )}
        <label>
          Student name
          <input required maxLength={200} value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <label>
          Register number
          <input
            required
            maxLength={128}
            value={registerNumber}
            onChange={(event) => setRegisterNumber(event.target.value)}
          />
        </label>
        <label>
          University roll number
          <input maxLength={128} value={rollNumber} onChange={(event) => setRollNumber(event.target.value)} />
        </label>
        <label>
          Email
          <input
            type={isInvitation ? 'email' : 'text'}
            required={isInvitation}
            maxLength={320}
            value={isInvitation ? email : (student.email ?? 'No email on file')}
            readOnly={!isInvitation}
            disabled={saving}
            onChange={(event) => setEmail(event.target.value)}
          />
          <small>
            {isInvitation
              ? 'Changing this email invalidates the old setup link and sends a fresh link to the corrected address.'
              : 'Email changes require a separate verified-email process; they cannot be changed here.'}
          </small>
        </label>
        <label>
          Current academic section
          <select
            value={sectionId}
            disabled={!canManagePlacement || placementLoading || !!placementError || placementIdsMissing || saving}
            onChange={(event) => setSectionId(event.target.value)}
          >
            <option value="">{student.academic_section_id ? 'Keep current placement' : 'No section assigned'}</option>
            {availableSections.map((section) => {
              const cohort = cohorts.find((item) => item.admission_cohort_id === section.admission_cohort_id)
              return (
                <option key={section.academic_section_id} value={section.academic_section_id}>
                  {cohort?.code} · {cohort?.name} · {section.code} {section.name}
                </option>
              )
            })}
          </select>
          <small>
            {canManagePlacement
              ? 'Completed semester registrations and batch transfers are protected.'
              : 'Your account does not have permission to change academic placement.'}
          </small>
          {canManagePlacement && placementLoading && <small role="status">Loading active sections…</small>}
          {canManagePlacement && !placementLoading && !placementError && !availableSections.length && (
            <small>
              {student.admission_cohort_id
                ? 'No active sections are available in this student’s batch.'
                : 'No active academic sections are available.'}
            </small>
          )}
          {canManagePlacement && placementIdsMissing && (
            <small className="student-record-error" role="alert">
              Academic placement identifiers are missing from the directory response. Apply the latest student directory
              migration before editing placement.
            </small>
          )}
          {placementError && (
            <small className="student-record-error" role="alert">
              {placementError}
            </small>
          )}
        </label>
        <footer>
          <button type="button" disabled={saving} onClick={onClose}>
            Cancel
          </button>
          <button type="submit" disabled={saving}>
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </footer>
      </form>
    </dialog>
  )
}
