import { useEffect, useRef } from 'react'
import { Save, TriangleAlert, X } from 'lucide-react'
import type { Department } from '../../../../types/academicSetup.ts'
import type { SubjectEditor } from './useSubjectEditor.ts'
import { useAcademicDialog } from '../dialogs/useAcademicDialog.ts'
import SubjectForm from './forms/SubjectForm.tsx'
import SubjectDetails from './SubjectDetails.tsx'
import type { SubjectsState } from './useSubjects.ts'

export default function SubjectDrawer({
  editor,
  departments,
  assignments,
}: {
  editor: SubjectEditor
  departments?: Department[]
  assignments: SubjectsState['assignments']
}) {
  const ref = useAcademicDialog('.subjects-page h1')
  const safeAction = useRef<HTMLButtonElement>(null)
  const confirming = editor.confirmation !== null
  const view = editor.panel === 'view'
  const title = confirming
    ? editor.confirmation === 'discard'
      ? 'Discard your changes?'
      : 'Confirm status change'
    : view
      ? 'Subject details'
      : editor.panel === 'edit'
        ? 'Edit Subject'
        : 'Add Subject'
  useEffect(() => {
    if (confirming) safeAction.current?.focus()
  }, [confirming])
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className={`subject-drawer${confirming ? ' is-confirming' : ''}`}
      role={confirming ? 'alertdialog' : undefined}
      aria-modal="true"
      aria-labelledby="subject-drawer-title"
      aria-describedby={confirming ? 'subject-confirm-description' : 'subject-drawer-description'}
      aria-busy={editor.saving}
      onCancel={(event) => {
        event.preventDefault()
        if (confirming) editor.cancelConfirmation()
        else editor.close()
      }}
    >
      <header>
        <div>
          <h2 id="subject-drawer-title">{title}</h2>
          {!confirming && (
            <p id="subject-drawer-description">
              {view
                ? 'Review academic subject information.'
                : editor.panel === 'edit'
                  ? 'Update this academic subject.'
                  : 'Create a new subject and assign it to a department.'}
            </p>
          )}
        </div>
        <button
          type="button"
          aria-label="Close subject drawer"
          disabled={editor.saving}
          onClick={confirming ? editor.cancelConfirmation : editor.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="subject-drawer-body">
        {confirming ? (
          <>
            <TriangleAlert className="subject-confirm-icon" aria-hidden="true" />
            <h3>
              {editor.record?.name ?? (editor.draft.name.trim() || 'New subject')}
              {editor.record && ` (${editor.record.code})`}
            </h3>
            <p id="subject-confirm-description">
              {editor.confirmation === 'discard'
                ? 'Your changes have not been saved. Discarding will lose your unsaved entries.'
                : `Mark this subject as ${editor.draft.is_active ? 'Active' : 'Inactive'}?${editor.draft.is_active ? '' : ' Existing records will be retained. Active dependencies may prevent this change.'}`}
            </p>
          </>
        ) : (
          <>
            {editor.error && (
              <p className="subject-form-error" role="alert">
                {editor.error} Your entries have been kept. Try again.
              </p>
            )}
            {!view && !editor.canManage && (
              <p className="subject-form-error" role="status">
                Subject changes are currently unavailable. Refresh the list to continue.
              </p>
            )}
            {view && editor.record ? (
              <SubjectDetails record={editor.record} departments={departments} assignments={assignments} />
            ) : (
              <SubjectForm editor={editor} departments={departments} />
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
              Edit Subject
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              Cancel
            </button>
            <button
              type="submit"
              form="subject-form"
              className="academic-primary-button"
              disabled={editor.saving || !editor.canManage}
            >
              <Save aria-hidden="true" />
              {editor.saving ? 'Saving…' : editor.panel === 'edit' ? 'Save Changes' : 'Create Subject'}
            </button>
          </>
        )}
      </footer>
    </dialog>
  )
}
