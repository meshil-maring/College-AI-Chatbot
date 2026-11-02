import { useState } from 'react'
import type { AcademicSection, AdmissionCohort } from '../../../../types/academicStructure.ts'
import type { StudentDirectoryRow, StudentDirectoryUpdateInput } from '../../../../types/admin/students.ts'
import StudentActionConfirmationDialog, { type StudentRecordAction } from './StudentActionConfirmationDialog.tsx'
import StudentEditDialog from './StudentEditDialog.tsx'

export default function StudentRecordActions({
  student,
  canEdit,
  canManagePlacement,
  canDelete,
  canResend,
  sections,
  cohorts,
  busy,
  structureLoading,
  structureError,
  onEdit,
  onSetActive,
  onDelete,
  onCancelInvitation,
  onResend,
}: {
  student: StudentDirectoryRow
  canEdit: boolean
  canManagePlacement: boolean
  canDelete: boolean
  canResend: boolean
  sections: AcademicSection[]
  cohorts: AdmissionCohort[]
  busy: boolean
  structureLoading: boolean
  structureError: string
  onEdit: (input: StudentDirectoryUpdateInput) => Promise<boolean>
  onSetActive: (active: boolean) => Promise<boolean>
  onDelete: () => Promise<boolean>
  onCancelInvitation: () => Promise<boolean>
  onResend: () => void
}) {
  const [open, setOpen] = useState(false)
  const [dialog, setDialog] = useState<StudentRecordAction | 'edit' | null>(null)
  const isInvitation = student.record_type === 'invitation'
  const canDeactivate = canEdit && student.student_status === 'active' && student.is_active !== false
  const canReactivate = canEdit && student.student_status === 'inactive' && student.approval_status === 'approved'
  const canEditRecord = canEdit
  const canDeleteRecord = canDelete && !isInvitation
  const canCancelInvitation = canDelete && isInvitation

  if (
    (!isInvitation || !canResend) &&
    !canEditRecord &&
    !canDeactivate &&
    !canReactivate &&
    !canDeleteRecord &&
    !canCancelInvitation
  ) {
    return null
  }

  async function confirmAction(): Promise<boolean> {
    if (dialog === 'deactivate') return onSetActive(false)
    if (dialog === 'reactivate') return onSetActive(true)
    if (dialog === 'delete') return onDelete()
    if (dialog === 'cancel-invitation') return onCancelInvitation()
    return false
  }

  return (
    <>
      <div className="student-directory-actions">
        <button
          type="button"
          aria-label={`Actions for ${student.student_name}`}
          aria-expanded={open}
          aria-controls={`student-actions-${student.record_id}`}
          disabled={busy}
          onClick={() => setOpen((value) => !value)}
        >
          Actions
        </button>
        {open && (
          <div id={`student-actions-${student.record_id}`}>
            {canResend && isInvitation && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setOpen(false)
                  onResend()
                }}
              >
                Resend setup link
              </button>
            )}
            {canEditRecord && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setOpen(false)
                  setDialog('edit')
                }}
              >
                {isInvitation ? 'Edit invitation' : 'Edit details'}
              </button>
            )}
            {canDeactivate && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setOpen(false)
                  setDialog('deactivate')
                }}
              >
                Deactivate
              </button>
            )}
            {canReactivate && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setOpen(false)
                  setDialog('reactivate')
                }}
              >
                Reactivate
              </button>
            )}
            {canDeleteRecord && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setOpen(false)
                  setDialog('delete')
                }}
              >
                Delete profile
              </button>
            )}
            {canCancelInvitation && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setOpen(false)
                  setDialog('cancel-invitation')
                }}
              >
                Cancel invitation
              </button>
            )}
          </div>
        )}
      </div>
      {dialog === 'edit' && (
        <StudentEditDialog
          student={student}
          isInvitation={isInvitation}
          sections={sections}
          cohorts={cohorts}
          canManagePlacement={canManagePlacement}
          placementLoading={structureLoading}
          placementError={structureError}
          onClose={() => setDialog(null)}
          onSave={onEdit}
        />
      )}
      {dialog && dialog !== 'edit' && (
        <StudentActionConfirmationDialog
          student={student}
          action={dialog}
          onClose={() => setDialog(null)}
          onConfirm={confirmAction}
        />
      )}
    </>
  )
}
