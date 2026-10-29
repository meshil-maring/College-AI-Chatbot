import { useEffect } from 'react'
import { Pencil, Save, TriangleAlert, X } from 'lucide-react'
import { useWorkspaceDialog } from '../../../../workspace/useWorkspaceDialog.ts'
import type { SectionEditor } from './useSectionEditor.ts'
import SectionForm from './SectionForm.tsx'
import SectionDetails from './SectionDetails.tsx'

export default function SectionDrawer({ editor }: { editor: SectionEditor }) {
  const ref = useWorkspaceDialog('.sections-page h1')
  const { panel, confirmation } = editor
  const viewing = panel?.mode === 'view'
  const title =
    confirmation === 'discard'
      ? 'Discard your changes?'
      : confirmation === 'status'
        ? 'Change section status?'
        : viewing
          ? 'Section Details'
          : panel?.mode === 'edit'
            ? 'Edit Section'
            : 'Add Section'
  useEffect(() => {
    const target = confirmation ? 'footer button' : viewing ? 'header button' : '#section-name'
    ref.current?.querySelector<HTMLElement>(target)?.focus()
  }, [confirmation, viewing, panel?.mode, ref])
  useEffect(() => {
    if (editor.error) ref.current?.querySelector<HTMLElement>('[role="alert"]')?.focus()
  }, [editor.error, ref])
  return (
    <dialog
      ref={ref}
      className="section-drawer"
      tabIndex={-1}
      aria-modal="true"
      role={confirmation ? 'alertdialog' : undefined}
      aria-labelledby="section-drawer-title"
      aria-describedby="section-drawer-description"
      onCancel={(event) => {
        event.preventDefault()
        if (confirmation) editor.keepEditing()
        else editor.close()
      }}
    >
      <header>
        <div>
          <h2 id="section-drawer-title">{title}</h2>
          <p id="section-drawer-description">
            {confirmation
              ? 'Confirm the change to this section.'
              : viewing
                ? 'Review this section and its batch.'
                : panel?.mode === 'edit'
                  ? 'Update this section and its status.'
                  : 'Create a new section for a student batch.'}
          </p>
        </div>
        <button
          type="button"
          disabled={editor.saving}
          aria-label="Close section drawer"
          onClick={confirmation ? editor.keepEditing : editor.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="section-drawer-body">
        {confirmation ? (
          <div className="section-confirmation">
            <TriangleAlert aria-hidden="true" />
            <p>
              {confirmation === 'discard'
                ? 'Your unsaved section entries will be discarded.'
                : `Change ${panel?.record?.name} to ${editor.draft.status}?`}
            </p>
          </div>
        ) : (
          <>
            {editor.saving && <p role="status">Saving section…</p>}
            {editor.error && (
              <p className="section-form-error" role="alert" tabIndex={-1}>
                {editor.error}
              </p>
            )}
            {viewing && panel?.record ? (
              <SectionDetails record={panel.record} state={editor.state} />
            ) : (
              <SectionForm editor={editor} />
            )}
          </>
        )}
      </div>
      <footer>
        {confirmation ? (
          <>
            <button type="button" className="academic-secondary-button" onClick={editor.keepEditing}>
              Keep Editing
            </button>
            <button type="button" className="academic-primary-button" disabled={editor.saving} onClick={editor.confirm}>
              {confirmation === 'discard' ? 'Discard Changes' : 'Confirm Change'}
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              {viewing ? 'Close' : 'Cancel'}
            </button>
            {viewing && panel?.record ? (
              <button
                type="button"
                className="academic-primary-button"
                disabled={!editor.state.canManage}
                onClick={() => editor.open('edit', panel.record)}
              >
                <Pencil aria-hidden="true" />
                Edit Section
              </button>
            ) : (
              <button
                type="submit"
                form="section-form"
                className="academic-primary-button"
                disabled={editor.saving || !editor.state.canManage}
              >
                <Save aria-hidden="true" />
                {panel?.mode === 'edit' ? 'Save Changes' : 'Create Section'}
              </button>
            )}
          </>
        )}
      </footer>
    </dialog>
  )
}
