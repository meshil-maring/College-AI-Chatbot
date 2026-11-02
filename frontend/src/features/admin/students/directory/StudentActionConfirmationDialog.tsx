import { useState } from 'react'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import type { StudentDirectoryRow } from '../../../../types/admin/students.ts'
import './studentRecordDialog.css'

export type StudentRecordAction = 'deactivate' | 'reactivate' | 'delete' | 'cancel-invitation'

const copy: Record<StudentRecordAction, { title: string; confirm: string; description: string }> = {
  deactivate: {
    title: 'Deactivate student?',
    confirm: 'Deactivate student',
    description: 'Student access will be disabled. Academic and account history will be retained.',
  },
  reactivate: {
    title: 'Reactivate student?',
    confirm: 'Reactivate student',
    description: 'The approved student account will be allowed to sign in again.',
  },
  delete: {
    title: 'Delete student profile?',
    confirm: 'Delete profile',
    description:
      'Permanent deletion is allowed only when no records are linked. The login identity is retained and disabled if no other roles use it.',
  },
  'cancel-invitation': {
    title: 'Cancel setup invitation?',
    confirm: 'Cancel invitation',
    description:
      'The setup link will stop working. If the student has already started account setup, cancellation will be blocked.',
  },
}

export default function StudentActionConfirmationDialog({
  student,
  action,
  onClose,
  onConfirm,
}: {
  student: StudentDirectoryRow
  action: StudentRecordAction
  onClose: () => void
  onConfirm: () => Promise<boolean>
}) {
  const ref = useWorkspaceDialog('.student-directory-header h1')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const content = copy[action]

  async function confirm() {
    setBusy(true)
    setError('')
    try {
      if (await onConfirm()) onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The student action could not be completed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <dialog
      ref={ref}
      className="student-record-dialog is-confirmation"
      aria-modal="true"
      aria-labelledby="student-action-title"
      onCancel={(event) => {
        event.preventDefault()
        if (!busy) onClose()
      }}
    >
      <h2 id="student-action-title">{content.title}</h2>
      <p>{student.student_name}</p>
      <p>{content.description}</p>
      {error && (
        <p className="student-record-error" role="alert">
          {error}
        </p>
      )}
      <footer>
        <button type="button" disabled={busy} onClick={onClose}>
          Cancel
        </button>
        <button
          type="button"
          className={action === 'delete' || action === 'cancel-invitation' ? 'is-danger' : ''}
          disabled={busy}
          onClick={() => void confirm()}
        >
          {busy ? 'Working…' : content.confirm}
        </button>
      </footer>
    </dialog>
  )
}
