import { useEffect } from 'react'
import { Pencil, Save, TriangleAlert, X } from 'lucide-react'
import { useWorkspaceDialog } from '../../../../workspace/useWorkspaceDialog.ts'
import type { BatchEditor } from './useBatchEditor.ts'
import BatchForm from './BatchForm.tsx'
import BatchDetails from './BatchDetails.tsx'

export default function BatchDrawer({ editor }: { editor: BatchEditor }) {
  const ref = useWorkspaceDialog('.batches-page h1')
  const { panel, confirmation } = editor
  const viewing = panel?.mode === 'view'
  const title =
    confirmation === 'discard'
      ? 'Discard your changes?'
      : confirmation === 'status'
        ? 'Change batch status?'
        : viewing
          ? 'Batch Details'
          : panel?.mode === 'edit'
            ? 'Edit Batch'
            : 'Add Batch'
  useEffect(() => {
    const target = confirmation ? 'footer button' : viewing ? 'header button' : '#batch-name'
    ref.current?.querySelector<HTMLElement>(target)?.focus()
  }, [confirmation, viewing, panel?.mode, ref])
  useEffect(() => {
    if (editor.error) ref.current?.querySelector<HTMLElement>('[role="alert"]')?.focus()
  }, [editor.error, ref])
  return (
    <dialog
      ref={ref}
      className="batch-drawer"
      tabIndex={-1}
      aria-modal="true"
      role={confirmation ? 'alertdialog' : undefined}
      aria-labelledby="batch-drawer-title"
      aria-describedby="batch-drawer-description"
      onCancel={(event) => {
        event.preventDefault()
        if (confirmation) editor.keepEditing()
        else editor.close()
      }}
    >
      <header>
        <div>
          <h2 id="batch-drawer-title">{title}</h2>
          <p id="batch-drawer-description">
            {confirmation
              ? 'Confirm the change to this batch.'
              : viewing
                ? 'Review this batch and its program.'
                : panel?.mode === 'edit'
                  ? 'Update this batch and its status.'
                  : 'Create a new student batch for a program.'}
          </p>
        </div>
        <button
          type="button"
          disabled={editor.saving}
          aria-label="Close batch drawer"
          onClick={confirmation ? editor.keepEditing : editor.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="batch-drawer-body">
        {confirmation ? (
          <div className="batch-confirmation">
            <TriangleAlert aria-hidden="true" />
            <p>
              {confirmation === 'discard'
                ? 'Your unsaved batch entries will be discarded.'
                : `Change ${panel?.record?.name} to ${editor.draft.status}?`}
            </p>
          </div>
        ) : (
          <>
            {editor.saving && <p role="status">Saving batch…</p>}
            {editor.error && (
              <p className="batch-form-error" role="alert" tabIndex={-1}>
                {editor.error}
              </p>
            )}
            {viewing && panel?.record ? (
              <BatchDetails record={panel.record} state={editor.state} />
            ) : (
              <BatchForm editor={editor} />
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
                Edit Batch
              </button>
            ) : (
              <button
                type="submit"
                form="batch-form"
                className="academic-primary-button"
                disabled={editor.saving || !editor.state.canManage}
              >
                <Save aria-hidden="true" />
                {panel?.mode === 'edit' ? 'Save Changes' : 'Create Batch'}
              </button>
            )}
          </>
        )}
      </footer>
    </dialog>
  )
}
