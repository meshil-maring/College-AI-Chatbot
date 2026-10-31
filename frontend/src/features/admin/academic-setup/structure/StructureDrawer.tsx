import { useEffect } from 'react'
import { X } from 'lucide-react'
import { useWorkspaceDialog } from '../../../workspace/useWorkspaceDialog.ts'
import type { StructureEntity } from '../../../../types/academicStructure.ts'
import type { StructureEditor } from './useStructureEditor.ts'
import { structureSingular } from './structureFields.ts'
import StructureFields from './StructureFields.tsx'

export default function StructureDrawer({
  editor,
  entity,
  description,
  statusDescription,
}: {
  editor: StructureEditor
  entity: StructureEntity
  description?: string
  statusDescription?: string
}) {
  const ref = useWorkspaceDialog('.structure-records-page h1')
  const viewing = editor.panel?.mode === 'view'
  const title =
    editor.confirmation === 'discard'
      ? 'Discard your changes?'
      : editor.confirmation === 'status'
        ? 'Confirm status change'
        : `${viewing ? 'View' : editor.panel?.row ? 'Edit' : 'Add'} ${structureSingular[entity]}`
  useEffect(() => {
    const target = editor.confirmation
      ? 'footer button'
      : viewing
        ? 'header button'
        : 'input:not(:disabled), select:not(:disabled), textarea:not(:disabled)'
    ref.current?.querySelector<HTMLElement>(target)?.focus()
  }, [editor.confirmation, editor.panel?.mode, viewing, ref])
  useEffect(() => {
    if (editor.error) ref.current?.querySelector<HTMLElement>('[role="alert"]')?.focus()
  }, [editor.error, ref])
  return (
    <dialog
      ref={ref}
      className="structure-drawer"
      aria-modal="true"
      tabIndex={-1}
      role={editor.confirmation ? 'alertdialog' : undefined}
      aria-labelledby="structure-drawer-title"
      onCancel={(event) => {
        event.preventDefault()
        if (editor.confirmation) editor.keepEditing()
        else editor.close()
      }}
    >
      <header>
        <h2 id="structure-drawer-title">{title}</h2>
        <button
          type="button"
          aria-label="Close academic drawer"
          disabled={editor.saving}
          onClick={editor.confirmation ? editor.keepEditing : editor.close}
        >
          <X aria-hidden="true" />
        </button>
      </header>
      <div className="structure-drawer-body">
        {description && <p>{description}</p>}
        {editor.error && (
          <p role="alert" tabIndex={-1} className="academic-request-error">
            {editor.error}
          </p>
        )}
        {editor.saving && <p role="status">Saving academic record…</p>}
        {editor.confirmation ? (
          <p>
            {editor.confirmation === 'discard'
              ? 'Your unsaved entries will be discarded.'
              : (statusDescription ??
                'This changes the saved status. Publishing freezes this curriculum and its mappings; assigned batches retain it.')}
          </p>
        ) : viewing ? (
          <dl className="structure-details">
            {editor.fields.map((field) => (
              <div key={field.key}>
                <dt>{field.label}</dt>
                <dd>
                  {field.type === 'select'
                    ? (field.options?.find((item) => item.value === editor.draft[field.key])?.label ??
                      (field.immutable ? 'Current assignment retained' : String(editor.draft[field.key])))
                    : typeof editor.draft[field.key] === 'boolean'
                      ? editor.draft[field.key]
                        ? 'Yes'
                        : 'No'
                      : String(editor.draft[field.key] || 'Not specified')}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <form
            id="structure-form"
            aria-label={`${structureSingular[entity]} details`}
            onSubmit={(event) => {
              event.preventDefault()
              void editor.submit()
            }}
          >
            <StructureFields
              fields={editor.fields}
              draft={editor.draft}
              editing={Boolean(editor.panel?.row)}
              saving={editor.saving}
              change={editor.change}
            />
          </form>
        )}
      </div>
      <footer>
        {editor.confirmation ? (
          <>
            <button
              type="button"
              className="academic-secondary-button"
              disabled={editor.saving}
              onClick={editor.keepEditing}
            >
              Keep Editing
            </button>
            <button type="button" className="academic-primary-button" disabled={editor.saving} onClick={editor.confirm}>
              {editor.confirmation === 'discard' ? 'Discard Changes' : 'Confirm Change'}
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              {viewing ? 'Close' : 'Cancel'}
            </button>
            {viewing ? (
              <button
                type="button"
                className="academic-primary-button"
                disabled={!editor.canManage}
                onClick={() => editor.open('edit', editor.panel?.row)}
              >
                Edit {structureSingular[entity]}
              </button>
            ) : (
              <button
                type="submit"
                form="structure-form"
                className="academic-primary-button"
                disabled={editor.saving || !editor.canManage}
              >
                {editor.saving ? 'Saving…' : editor.panel?.row ? 'Save Changes' : `Create ${structureSingular[entity]}`}
              </button>
            )}
          </>
        )}
      </footer>
    </dialog>
  )
}
