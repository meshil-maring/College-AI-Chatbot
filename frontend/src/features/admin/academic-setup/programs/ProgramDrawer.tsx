import { useEffect, useRef } from 'react'
import { Save, TriangleAlert, X } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { ProgramEditor } from './useProgramEditor.ts'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import ProgramForm from './forms/ProgramForm.tsx'
import ProgramDetails from './ProgramDetails.tsx'

export default function ProgramDrawer({ editor, departments }: { editor: ProgramEditor; departments?: Department[] }) {
  const ref = useWorkspaceDialog('.programs-page h1')
  const safeAction = useRef<HTMLButtonElement>(null)
  const confirming = editor.confirmation !== null
  const view = editor.panel === 'view'
  const title = confirming
    ? editor.confirmation === 'discard'
      ? 'Discard your changes?'
      : 'Confirm status change'
    : view
      ? 'Program details'
      : editor.panel === 'edit'
        ? 'Edit Program'
        : 'Add Program'
  useEffect(() => {
    if (confirming) safeAction.current?.focus()
  }, [confirming])
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className={`program-drawer${confirming ? ' is-confirming' : ''}`}
      role={confirming ? 'alertdialog' : undefined}
      aria-modal="true"
      aria-labelledby="program-drawer-title"
      aria-describedby={confirming ? 'program-confirm-description' : 'program-drawer-description'}
      aria-busy={editor.saving}
      onCancel={(event) => {
        event.preventDefault()
        if (confirming) editor.cancelConfirmation()
        else editor.close()
      }}
    >
      <header>
        <div>
          <h2 id="program-drawer-title">{title}</h2>
          {!confirming && (
            <p id="program-drawer-description">
              {view
                ? 'Review academic program information.'
                : editor.panel === 'edit'
                  ? 'Update this academic program.'
                  : 'Create a new academic program.'}
            </p>
          )}
        </div>
        <button
          type="button"
          aria-label="Close program drawer"
          disabled={editor.saving}
          onClick={confirming ? editor.cancelConfirmation : editor.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="program-drawer-body">
        {confirming ? (
          <>
            <TriangleAlert className="program-confirm-icon" aria-hidden="true" />
            <h3>
              {editor.record?.name ?? (editor.draft.name.trim() || 'New program')}
              {editor.record && ` (${editor.record.code})`}
            </h3>
            <p id="program-confirm-description">
              {editor.confirmation === 'discard'
                ? 'Your changes have not been saved. Discarding will lose your unsaved entries.'
                : `Mark this program as ${editor.draft.is_active ? 'Active' : 'Inactive'}?${editor.draft.is_active ? '' : ' Existing records will be retained. Active dependencies may prevent this change.'}`}
            </p>
          </>
        ) : (
          <>
            {editor.error && (
              <p className="program-form-error" role="alert">
                {editor.error} Your entries have been kept. Try again.
              </p>
            )}
            {!view && !editor.canManage && (
              <p className="program-form-error" role="status">
                Program changes are currently unavailable. Refresh the list to continue.
              </p>
            )}
            {view && editor.record ? (
              <ProgramDetails record={editor.record} departments={departments} />
            ) : (
              <ProgramForm editor={editor} departments={departments} />
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
              Edit Program
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              Cancel
            </button>
            <button
              type="submit"
              form="program-form"
              className="academic-primary-button"
              disabled={editor.saving || !editor.canManage}
            >
              <Save aria-hidden="true" />
              {editor.saving ? 'Saving…' : editor.panel === 'edit' ? 'Save Changes' : 'Create Program'}
            </button>
          </>
        )}
      </footer>
    </dialog>
  )
}
