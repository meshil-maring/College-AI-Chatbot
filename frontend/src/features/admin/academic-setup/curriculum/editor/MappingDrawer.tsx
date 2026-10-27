import { Save, TriangleAlert } from 'lucide-react'
import type { CurriculumState } from '../useCurriculum.ts'
import type { MappingEditor } from './useMappingEditor.ts'
import CurriculumDrawerFrame from './CurriculumDrawerFrame.tsx'
import MappingForm from './MappingForm.tsx'

export default function MappingDrawer({ state, editor }: { state: CurriculumState; editor: MappingEditor }) {
  const confirming = Boolean(editor.confirmation)
  const title = confirming
    ? editor.confirmation === 'discard'
      ? 'Discard your changes?'
      : 'Confirm mapping status change'
    : editor.panel === 'edit'
      ? 'Edit Subject Mapping'
      : 'Add Subject'
  const description = confirming
    ? editor.confirmation === 'discard'
      ? 'Your changes have not been saved. Discarding will lose your unsaved entries.'
      : `Mark this mapping as ${editor.draft.is_active ? 'Active' : 'Inactive'}? Existing records will be retained. Active dependencies may prevent this change.`
    : 'Map a subject to this program using the existing academic catalogue.'
  return (
    <CurriculumDrawerFrame
      title={title}
      description={description}
      busy={editor.saving}
      alert={confirming}
      onClose={confirming ? editor.cancelConfirmation : editor.close}
      footer={
        confirming ? (
          <>
            <button type="button" className="academic-secondary-button" onClick={editor.cancelConfirmation}>
              Keep Editing
            </button>
            <button
              type="button"
              className="academic-primary-button"
              disabled={editor.confirmation === 'status' && !editor.canManage}
              onClick={() => (editor.confirmation === 'discard' ? editor.discard() : editor.submit(true))}
            >
              {editor.confirmation === 'discard' ? 'Discard Changes' : 'Confirm Changes'}
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              Cancel
            </button>
            <button
              type="submit"
              form="curriculum-mapping-form"
              className="academic-primary-button"
              disabled={editor.saving || !editor.canManage}
            >
              <Save aria-hidden="true" />
              {editor.saving ? 'Saving…' : editor.panel === 'edit' ? 'Save Changes' : 'Add Subject'}
            </button>
          </>
        )
      }
    >
      {confirming ? (
        <TriangleAlert className="curriculum-confirm-icon" aria-hidden="true" />
      ) : (
        <>
          {editor.error && (
            <p className="curriculum-form-error" role="alert">
              {editor.error} Your entries have been kept.
            </p>
          )}
          {!editor.canManage && (
            <p className="curriculum-form-error" role="status">
              Mapping changes are unavailable. Refresh the list to continue.
            </p>
          )}
          <MappingForm state={state} editor={editor} />
        </>
      )}
    </CurriculumDrawerFrame>
  )
}
