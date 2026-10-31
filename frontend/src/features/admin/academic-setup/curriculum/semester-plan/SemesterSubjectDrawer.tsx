import type { StructureEditor } from '../../structure/useStructureEditor.ts'
import StructureFields from '../../structure/StructureFields.tsx'
import CurriculumDrawerFrame from '../editor/CurriculumDrawerFrame.tsx'

export default function SemesterSubjectDrawer({
  editor,
  semesterName,
  curriculumName,
}: {
  editor: StructureEditor
  semesterName: string
  curriculumName: string
}) {
  const confirming = Boolean(editor.confirmation)
  const editing = Boolean(editor.panel?.row)
  const title = confirming
    ? editor.confirmation === 'discard'
      ? 'Discard your changes?'
      : 'Change subject inclusion?'
    : `${editing ? 'Edit' : 'Add'} subject in ${semesterName}`
  return (
    <CurriculumDrawerFrame
      title={title}
      description={
        confirming
          ? editor.confirmation === 'discard'
            ? 'Your unsaved subject choices will be discarded.'
            : 'This changes whether the subject is included in this draft study plan.'
          : `${semesterName} · ${curriculumName}`
      }
      busy={editor.saving}
      alert={confirming}
      initialFocusSelector="select:not(:disabled)"
      onClose={confirming ? editor.keepEditing : editor.close}
      footer={
        confirming ? (
          <>
            <button
              type="button"
              className="academic-secondary-button"
              disabled={editor.saving}
              onClick={editor.keepEditing}
            >
              Keep editing
            </button>
            <button
              type="button"
              className="academic-primary-button"
              disabled={editor.saving || (editor.confirmation !== 'discard' && !editor.canManage)}
              onClick={editor.confirm}
            >
              {editor.confirmation === 'discard' ? 'Discard changes' : 'Confirm change'}
            </button>
          </>
        ) : (
          <>
            <button type="button" className="academic-secondary-button" disabled={editor.saving} onClick={editor.close}>
              Cancel
            </button>
            <button
              type="submit"
              form="semester-subject-form"
              className="academic-primary-button"
              disabled={editor.saving || !editor.canManage}
            >
              {editor.saving ? 'Saving…' : editing ? 'Save subject' : 'Add subject'}
            </button>
          </>
        )
      }
    >
      {!confirming && (
        <>
          {editor.error && (
            <p className="curriculum-form-error" role="alert">
              {editor.error} Your entries have been kept.
            </p>
          )}
          {!editor.canManage && (
            <p role="status">Changes are unavailable. Check the curriculum status and your access.</p>
          )}
          <form
            id="semester-subject-form"
            className="study-plan-subject-form"
            aria-label="Semester subject"
            onSubmit={(event) => {
              event.preventDefault()
              void editor.submit()
            }}
          >
            <fieldset disabled={editor.saving || !editor.canManage}>
              <StructureFields
                fields={editor.fields}
                draft={editor.draft}
                editing={editing}
                saving={editor.saving}
                change={editor.change}
              />
            </fieldset>
          </form>
        </>
      )}
    </CurriculumDrawerFrame>
  )
}
