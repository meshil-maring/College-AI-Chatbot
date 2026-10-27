import { useEffect, useRef } from 'react'
import { Save, X } from 'lucide-react'
import { useAcademicDialog } from '../../dialogs/useAcademicDialog.ts'
import type { CalendarState } from '../useCalendar.ts'
import type { CalendarEditor } from '../useCalendarEditor.ts'
import CalendarForm from './CalendarForm.tsx'

export default function CalendarDrawer({ editor, state }: { editor: CalendarEditor; state: CalendarState }) {
  const ref = useAcademicDialog('.calendar-page h1')
  const safeAction = useRef<HTMLButtonElement>(null)
  const confirming = editor.confirmation !== null
  const view = editor.panel?.mode === 'view'
  const noun = editor.panel?.entity === 'semesters' ? 'Semester' : 'Academic Year'
  const title = confirming
    ? editor.confirmation === 'discard'
      ? 'Discard your changes?'
      : 'Confirm status change'
    : view
      ? `${noun} details`
      : `${editor.panel?.mode === 'edit' ? 'Edit' : 'Add'} ${noun}`
  useEffect(() => {
    if (confirming) safeAction.current?.focus()
  }, [confirming])
  return (
    <dialog
      ref={ref}
      tabIndex={-1}
      className="calendar-drawer"
      role={confirming ? 'alertdialog' : undefined}
      aria-modal="true"
      aria-labelledby="calendar-drawer-title"
      aria-describedby="calendar-drawer-description"
      aria-busy={editor.saving}
      onCancel={(event) => {
        event.preventDefault()
        if (confirming) editor.cancelConfirmation()
        else editor.close()
      }}
    >
      <header>
        <div>
          <h2 id="calendar-drawer-title">{title}</h2>
          <p id="calendar-drawer-description">
            {confirming
              ? editor.confirmation === 'discard'
                ? 'Your unsaved entries will be lost. Already saved records will be retained.'
                : 'Apply the new active and current settings? Existing dependencies may prevent this change.'
              : view
                ? 'Review academic calendar information.'
                : noun === 'Academic Year' && editor.panel?.mode === 'add'
                  ? 'Create a new academic year and configure its semesters.'
                  : `Update your ${noun.toLowerCase()} information.`}
          </p>
        </div>
        <button
          type="button"
          aria-label="Close calendar drawer"
          disabled={editor.saving}
          onClick={confirming ? editor.cancelConfirmation : editor.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="calendar-drawer-body">
        {confirming ? (
          <h3>{editor.draft.name}</h3>
        ) : (
          <>
            {editor.progress.year && (
              <p className="calendar-partial-notice" role="status">
                Academic year saved. {editor.progress.completed} of {editor.draft.semesters.length} semesters saved.
                Retry will save only the remaining semesters.
              </p>
            )}
            {editor.error && (
              <p className="calendar-form-error" role="alert">
                {editor.error} Your entries have been kept.
              </p>
            )}
            {!view && !editor.canManage && (
              <p className="calendar-form-error" role="status">
                Calendar changes are unavailable. Refresh the list to continue.
              </p>
            )}
            <CalendarForm editor={editor} state={state} />
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
              disabled={editor.confirmation === 'status' && !editor.canManage}
              onClick={() => (editor.confirmation === 'discard' ? editor.discard() : void editor.submit(true))}
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
              onClick={() => editor.panel && editor.open(editor.panel.entity, 'edit', editor.panel.record)}
            >
              Edit {noun}
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              Cancel
            </button>
            <button
              type="submit"
              form="calendar-form"
              className="academic-primary-button"
              disabled={editor.saving || !editor.canManage}
            >
              <Save aria-hidden="true" />
              {editor.saving
                ? 'Saving...'
                : editor.progress.year
                  ? 'Retry Remaining Semesters'
                  : editor.panel?.mode === 'edit'
                    ? 'Save Changes'
                    : `Create ${noun}`}
            </button>
          </>
        )}
      </footer>
    </dialog>
  )
}
