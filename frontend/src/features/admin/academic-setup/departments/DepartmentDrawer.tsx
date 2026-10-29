import { useEffect, useRef } from 'react'
import { Save, TriangleAlert, X } from 'lucide-react'
import type { AcademicCatalogue } from '../../../../types/academicSetup.ts'
import type { DepartmentEditor } from './useDepartmentEditor.ts'
import DepartmentForm from './DepartmentForm.tsx'
import DepartmentDetails from './DepartmentDetails.tsx'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'

export default function DepartmentDrawer({
  editor,
  catalogue,
}: {
  editor: DepartmentEditor
  catalogue?: AcademicCatalogue
}) {
  const ref = useWorkspaceDialog('.departments-page h1')
  const safeAction = useRef<HTMLButtonElement>(null)
  const confirming = editor.confirmation !== null
  const view = editor.panel === 'view'
  const title = confirming
    ? editor.confirmation === 'discard'
      ? 'Discard your changes?'
      : 'Confirm status change'
    : view
      ? 'Department details'
      : editor.panel === 'edit'
        ? 'Edit Department'
        : 'Add Department'
  useEffect(() => {
    if (confirming) safeAction.current?.focus()
  }, [confirming])
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className={`department-drawer${confirming ? ' is-confirming' : ''}`}
      role={confirming ? 'alertdialog' : undefined}
      aria-modal="true"
      aria-labelledby="department-drawer-title"
      aria-describedby={confirming ? 'department-confirm-description' : 'department-drawer-description'}
      aria-busy={editor.saving}
      onCancel={(event) => {
        event.preventDefault()
        if (confirming) editor.cancelConfirmation()
        else editor.close()
      }}
    >
      <header>
        <div>
          <h2 id="department-drawer-title">{title}</h2>
          {!confirming && (
            <p id="department-drawer-description">
              {view
                ? 'Review department information.'
                : editor.panel === 'edit'
                  ? 'Update this academic department.'
                  : 'Create a new academic department.'}
            </p>
          )}
        </div>
        <button
          type="button"
          aria-label="Close department drawer"
          disabled={editor.saving}
          onClick={confirming ? editor.cancelConfirmation : editor.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="department-drawer-body">
        {confirming ? (
          <>
            <TriangleAlert className="department-confirm-icon" aria-hidden="true" />
            <h3>
              {editor.record?.name ?? (editor.draft.name.trim() || 'New department')}
              {editor.record && ` (${editor.record.code})`}
            </h3>
            <p id="department-confirm-description">
              {editor.confirmation === 'discard'
                ? 'Your changes have not been saved. Discarding will lose your unsaved entries. The saved department record will remain unchanged.'
                : `Mark this department as ${editor.draft.is_active ? 'Active' : 'Inactive'}?${editor.draft.is_active ? '' : ' Existing records will be retained. Active dependencies may prevent this change.'}`}
            </p>
          </>
        ) : (
          <>
            {editor.error && (
              <p className="department-form-error" role="alert">
                {editor.error} Your entries have been kept. Try again.
              </p>
            )}
            {!view && !editor.canManage && (
              <p className="department-form-error" role="status">
                Department changes are currently unavailable. Refresh the list to continue.
              </p>
            )}
            {view && editor.record ? (
              <DepartmentDetails record={editor.record} catalogue={catalogue} />
            ) : (
              <DepartmentForm editor={editor} />
            )}
          </>
        )}
      </div>
      <footer>
        {confirming ? (
          <>
            <button
              ref={safeAction}
              type="button"
              className="academic-secondary-button"
              onClick={editor.cancelConfirmation}
            >
              Keep Editing
            </button>
            <button
              type="button"
              className="academic-primary-button"
              onClick={() => (editor.confirmation === 'discard' ? editor.discard() : editor.submit(true))}
              disabled={editor.confirmation === 'status' && !editor.canManage}
            >
              {editor.confirmation === 'discard' ? 'Discard Changes' : 'Confirm Changes'}
            </button>
          </>
        ) : view ? (
          <>
            <button type="button" className="academic-secondary-button" onClick={editor.close}>
              Close
            </button>
            <button
              type="button"
              className="academic-primary-button"
              disabled={!editor.canManage}
              onClick={() => editor.open('edit', editor.record)}
            >
              Edit Department
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              Cancel
            </button>
            <button
              type="submit"
              form="department-form"
              className="academic-primary-button"
              disabled={editor.saving || !editor.canManage}
            >
              <Save aria-hidden="true" />
              {editor.saving ? 'Saving…' : editor.panel === 'edit' ? 'Save Changes' : 'Create Department'}
            </button>
          </>
        )}
      </footer>
    </dialog>
  )
}
