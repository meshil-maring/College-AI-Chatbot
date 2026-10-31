import { useEffect, useRef } from 'react'
import { TriangleAlert, X } from 'lucide-react'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import type { AcademicDeletion } from './useAcademicDeletion.ts'
import './styles/dialog.css'

export default function AcademicDeleteDialog({ deletion }: { deletion: AcademicDeletion }) {
  const ref = useWorkspaceDialog(deletion.focusTarget)
  const cancel = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    cancel.current?.focus()
  }, [])

  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className="academic-delete-dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="academic-delete-title"
      aria-describedby="academic-delete-description"
      aria-busy={deletion.saving}
      onCancel={(event) => {
        event.preventDefault()
        deletion.close()
      }}
    >
      <header>
        <h2 id="academic-delete-title">Delete {deletion.noun}?</h2>
        <button
          type="button"
          aria-label="Close deletion confirmation"
          disabled={deletion.saving}
          onClick={deletion.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="academic-delete-body">
        <TriangleAlert className="academic-delete-warning" aria-hidden="true" />
        <h3>
          {deletion.record?.name} ({deletion.record?.code})
        </h3>
        <p id="academic-delete-description">
          This permanently deletes the {deletion.noun} and cannot be undone. Deletion is allowed only when there are no
          linked records, including inactive records. Student and teacher accounts will not be deleted.
        </p>
        {(deletion.blocked || deletion.error) && (
          <p className="academic-delete-error" role="alert">
            {deletion.blocked || deletion.error}
          </p>
        )}
        {!deletion.canDelete && !deletion.blocked && (
          <p role="status">{deletion.label} deletion is currently unavailable. Refresh the list to continue.</p>
        )}
      </div>
      <footer>
        <button
          ref={cancel}
          type="button"
          className="academic-secondary-button"
          disabled={deletion.saving}
          onClick={deletion.close}
        >
          Cancel
        </button>
        <button
          type="button"
          className="academic-delete-button"
          disabled={deletion.saving || !deletion.canDelete}
          onClick={deletion.confirm}
        >
          {deletion.saving ? 'Deleting…' : `Delete ${deletion.label}`}
        </button>
      </footer>
    </dialog>
  )
}
